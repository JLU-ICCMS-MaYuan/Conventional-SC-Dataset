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

// cascadeDeleteInDB 在数据库事务中按依赖顺序删除论文及其所有关联数据
func cascadeDeleteInDB(tx *gorm.DB, paperID uint) error {
	// 1. 删除证据和分块（叶子节点）
	if err := tx.Where("paper_id = ?", paperID).Delete(&models.PaperEvidence{}).Error; err != nil {
		return fmt.Errorf("删除 paper_evidences 失败: %w", err)
	}
	if err := tx.Where("paper_id = ?", paperID).Delete(&models.PaperChunk{}).Error; err != nil {
		return fmt.Errorf("删除 paper_chunks 失败: %w", err)
	}

	// 2. 删除审核历史
	if err := tx.Where("paper_id = ?", paperID).Delete(&models.PaperReviewEvent{}).Error; err != nil {
		return fmt.Errorf("删除 paper_review_events 失败: %w", err)
	}

	// 3. 删除 Tc 结果和上下文（依赖 material_states）
	if err := tx.Where("paper_id = ?", paperID).Delete(&models.TcResult{}).Error; err != nil {
		return fmt.Errorf("删除 tc_results 失败: %w", err)
	}
	if err := tx.Where("paper_id = ?", paperID).Delete(&models.CalculationContext{}).Error; err != nil {
		return fmt.Errorf("删除 calculation_contexts 失败: %w", err)
	}
	if err := tx.Where("paper_id = ?", paperID).Delete(&models.ExperimentalContext{}).Error; err != nil {
		return fmt.Errorf("删除 experimental_contexts 失败: %w", err)
	}

	// 4. 删除晶体结构
	if err := tx.Where("paper_id = ?", paperID).Delete(&models.StructureModel{}).Error; err != nil {
		return fmt.Errorf("删除 structures 失败: %w", err)
	}

	// 5. 删除材料状态
	if err := tx.Where("paper_id = ?", paperID).Delete(&models.MaterialState{}).Error; err != nil {
		return fmt.Errorf("删除 material_states 失败: %w", err)
	}

	// 6. 删除关键物性
	if err := tx.Where("paper_id = ?", paperID).Delete(&models.KeyProperty{}).Error; err != nil {
		return fmt.Errorf("删除 key_properties 失败: %w", err)
	}

	// 7. 最后删除论文记录
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
