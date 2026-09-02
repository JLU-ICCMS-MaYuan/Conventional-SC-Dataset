package handlers

import (
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"

	"scwiki/server/cache"
	"scwiki/server/database"
	"scwiki/server/models"

	"gorm.io/gorm"
)

// ErrPaperNotFound 供调用方区分 404 与 500，避免按错误文案做字符串匹配。
var ErrPaperNotFound = errors.New("论文不存在")

// cascadeDeleteInDB 在事务中按 MySQL 真实外键依赖的拓扑逆序删除论文及全部关联数据。
//
// 顺序不可随意调整：以下依赖由 information_schema 实测得出，写错会触发
// Error 1451 并回滚整个事务（历史事故：superconductor_properties 曾排在
// calculation_contexts 之后，导致删除功能完全不可用）。
//
//	superconductor_properties → calculation_contexts, structure_models, material_states
//	tc_results                → calculation_contexts, experimental_contexts, material_states
//	tc_result_evidences       → tc_results, paper_evidences
//	structure_model_evidences → structure_models, paper_evidences
//	superconductor_property_evidences → paper_evidences
//	calculation_contexts / experimental_contexts → structure_models, material_states
//	structure_models          → material_states, structure_models(自引用 parent)
//	material_state_structure_families → material_states（无 paper_id，按状态子查询）
//	material_states           → papers, superconductors
//	paper_evidences           → paper_chunks, papers
//	paper_chunks              → paper_files, papers
//	paper_files / paper_review_events → papers
//
// superconductors 与 material_families 是跨论文共享的目录数据，不在此删除。
func cascadeDeleteInDB(tx *gorm.DB, paperID uint) error {
	// 按 paper_id 直接删除的表，严格按依赖逆序排列。
	steps := []struct {
		table string
		model any
	}{
		// 1. 证据连接表：引用 tc_results / structure_models / paper_evidences
		{"tc_result_evidences", &models.TcResultEvidence{}},
		{"structure_model_evidences", &models.StructureModelEvidence{}},
		{"superconductor_property_evidences", &models.SuperconductorPropertyEvidence{}},

		// 2. 引用 contexts 与 material_states 的叶子业务表
		{"tc_results", &models.TcResult{}},
		{"superconductor_properties", &models.KeyProperty{}},

		// 3. contexts：引用 structure_models 与 material_states
		{"calculation_contexts", &models.CalculationContext{}},
		{"experimental_contexts", &models.ExperimentalContext{}},

	}
	for _, step := range steps {
		if err := tx.Where("paper_id = ?", paperID).Delete(step.model).Error; err != nil {
			return fmt.Errorf("删除 %s 失败: %w", step.table, err)
		}
	}

	// 4. structure_models 自引用 parent_structure_id：先置空再删，
	// 否则同论文内父子结构的删除先后顺序不定，可能触发 Error 1451。
	if err := tx.Model(&models.StructureModel{}).
		Where("paper_id = ? AND parent_structure_id IS NOT NULL", paperID).
		Update("parent_structure_id", nil).Error; err != nil {
		return fmt.Errorf("解开 structure_models 自引用失败: %w", err)
	}
	if err := tx.Where("paper_id = ?", paperID).Delete(&models.StructureModel{}).Error; err != nil {
		return fmt.Errorf("删除 structure_models 失败: %w", err)
	}

	// 5. 连接表无 paper_id，按本论文的 material_state 子查询删除
	if err := tx.Exec(
		"DELETE FROM material_state_structure_families WHERE material_state_id IN (SELECT id FROM material_states WHERE paper_id = ?)",
		paperID,
	).Error; err != nil {
		return fmt.Errorf("删除 material_state_structure_families 失败: %w", err)
	}

	// 6. 材料状态（此时所有子表已清空）
	if err := tx.Where("paper_id = ?", paperID).Delete(&models.MaterialState{}).Error; err != nil {
		return fmt.Errorf("删除 material_states 失败: %w", err)
	}
	if err := tx.Where("paper_id = ?", paperID).Delete(&models.PaperMaterialFamily{}).Error; err != nil {
		return fmt.Errorf("删除 paper_material_families 失败: %w", err)
	}

	// 7. 证据 → 分块 → 文件：paper_evidences 引用 paper_chunks，后者引用 paper_files
	rest := []struct {
		table string
		model any
	}{
		{"paper_evidences", &models.PaperEvidence{}},
		{"paper_chunks", &models.PaperChunk{}},
		{"paper_files", &models.PaperFile{}},
		{"paper_review_events", &models.PaperReviewEvent{}},
	}
	for _, step := range rest {
		if err := tx.Where("paper_id = ?", paperID).Delete(step.model).Error; err != nil {
			return fmt.Errorf("删除 %s 失败: %w", step.table, err)
		}
	}

	// 8. 最后删除论文本体
	if err := tx.Delete(&models.Paper{}, paperID).Error; err != nil {
		return fmt.Errorf("删除 papers 失败: %w", err)
	}

	return nil
}

// cleanExternalServices 调用 Python 内部端点清理 Qdrant 和 Neo4j。
// 外部清理属 best-effort：MySQL 记录已物理删除且不可恢复，此处失败只记日志，
// 不回滚也不阻断删除，避免把可补偿的不一致升级成删不掉的死局。
func cleanExternalServices(paperID uint, authToken string) {
	baseURL := pythonBackendURL()

	if err := callPythonDelete(fmt.Sprintf("%s/api/internal/papers/%d/vectors", baseURL, paperID), authToken); err != nil {
		log.Printf("警告: paper %d 的 Qdrant 清理失败: %v", paperID, err)
	}
	if err := callPythonDelete(fmt.Sprintf("%s/api/internal/papers/%d/graph", baseURL, paperID), authToken); err != nil {
		log.Printf("警告: paper %d 的 Neo4j 清理失败: %v", paperID, err)
	}
}

// callPythonDelete 调用 Python DELETE 端点
func callPythonDelete(url string, authToken string) error {
	req, err := http.NewRequest("DELETE", url, nil)
	if err != nil {
		return fmt.Errorf("创建请求失败: %w", err)
	}
	req.Header.Set("Authorization", authToken)

	resp, err := pythonBackendClient.Do(req)
	if err != nil {
		return fmt.Errorf("HTTP 请求失败: %w", err)
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)

	if resp.StatusCode == 404 {
		// 资源不存在，认为已删除
		return nil
	}
	if resp.StatusCode != 200 {
		return fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(body))
	}

	return nil
}

// CascadeDeletePaper 完整删除论文：MySQL 事务 + 外部清理 + 缓存清理
func CascadeDeletePaper(paperID uint, authToken string) error {
	// 检查论文是否存在
	var paper models.Paper
	if err := database.DB.First(&paper, paperID).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return ErrPaperNotFound
		}
		return fmt.Errorf("数据库查询失败: %w", err)
	}

	// 阶段1：MySQL 删除（事务保证原子性）
	err := database.DB.Transaction(func(tx *gorm.DB) error {
		return cascadeDeleteInDB(tx, paperID)
	})
	if err != nil {
		return fmt.Errorf("数据库删除失败: %w", err)
	}

	// 阶段2：外部清理（best-effort，失败只记日志）
	cleanExternalServices(paperID, authToken)

	// 阶段3：清理缓存
	cache.FlushPattern("chart:*")
	cache.FlushPattern("search:*")
	cache.FlushPattern("community:contributions:*")

	return nil
}
