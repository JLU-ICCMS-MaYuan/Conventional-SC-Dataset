package handlers

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"net/http"
	"sort"
	"strconv"
	"strings"

	"scwiki/server/cache"
	"scwiki/server/database"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

var paperPatchFields = map[string]bool{
	"title": true, "doi": true, "authors": true, "journal": true, "volume": true,
	"pages": true, "year": true, "abstract": true, "summary": true,
	"paper_type": true, "theoretical_subtype": true, "keywords_tags": true,
	"methodology": true, "key_finding": true, "research_motivation": true,
	"research_materials": true, "material_relations": true, "builds_on": true,
	"knowledge_graph_title": true,
}

func paperPatchFieldAllowed(field string) bool { return paperPatchFields[field] }

// paperPatchUpdatesFromBody 从请求体提取业务白名单字段，供 PatchPaper 使用。
func paperPatchUpdatesFromBody(body map[string]interface{}) map[string]interface{} {
	updates := map[string]interface{}{}
	for key, value := range body {
		if paperPatchFieldAllowed(key) {
			updates[key] = value
		}
	}
	return updates
}

// ═══════════════════════════════════════════════
// 论文公开 API（替代 Python /api/papers/*）
// ═══════════════════════════════════════════════

// GetPaper 论文详情 + key_properties
// GET /api/papers/:id
func GetPaper(c *gin.Context) {
	id, err := strconv.Atoi(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "无效的论文 ID"})
		return
	}

	var paper models.Paper
	if err := database.DB.
		Preload("KeyProperties.PropertyDefinition").
		Preload("MaterialStates.Superconductor").
		Preload("MaterialStates.MaterialFamily").
		Preload("MaterialStates.StructureFamilyLinks.StructureFamily").
		Preload("MaterialStates.TcResults").
		Preload("MaterialStates.CalculationContexts").
		Preload("MaterialStates.Structures").
		First(&paper, uint(id)).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "论文不存在"})
		return
	}
	user := optionalPaperUser(c)
	if !canViewPaper(&paper, user) {
		c.JSON(http.StatusForbidden, gin.H{"error": "无权查看该论文"})
		return
	}
	c.JSON(http.StatusOK, paperForViewer(paper, user))
}

func optionalPaperUser(c *gin.Context) *models.User {
	email, exists := c.Get("user_email")
	if !exists {
		return nil
	}
	var user models.User
	if err := database.DB.Where("email = ?", email).First(&user).Error; err != nil {
		return nil
	}
	return &user
}

func paperAdmin(user *models.User) bool {
	return user != nil && user.IsApproved && (user.Role == "admin" || user.Role == "superadmin")
}

func paperOwner(paper *models.Paper, user *models.User) bool {
	return user != nil && paper.UploadedBy != nil && *paper.UploadedBy == user.ID
}

func canViewPaper(paper *models.Paper, user *models.User) bool {
	if paperAdmin(user) || paper.ReviewStatus == reviewStatusApproved {
		return true
	}
	if user == nil {
		return false
	}
	if paper.ReviewStatus == reviewStatusPending {
		return true
	}
	return paper.ReviewStatus == reviewStatusRejected && paperOwner(paper, user)
}

func paperForViewer(paper models.Paper, user *models.User) gin.H {
	result := paperToDict(paper)
	if paperOwner(&paper, user) || paperAdmin(user) {
		result["review_comment"] = paper.ReviewComment
	}
	if paperAdmin(user) {
		result["admin_internal_note"] = paper.AdminInternalNote
		result["uploaded_by_user_id"] = paper.UploadedBy
		result["reviewed_by_user_id"] = paper.ReviewedBy
	}
	result["can_edit"] = paperOwner(&paper, user) || paperAdmin(user)
	return result
}

// ListPapers 返回当前身份可见的正式论文列表。
func ListPapers(c *gin.Context) {
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "50"))
	offset, _ := strconv.Atoi(c.DefaultQuery("offset", "0"))
	if limit < 1 {
		limit = 50
	}
	if limit > 200 {
		limit = 200
	}
	user := optionalPaperUser(c)
	query := database.DB.Model(&models.Paper{})
	if !paperAdmin(user) {
		if user == nil {
			query = query.Where("review_status = ?", reviewStatusApproved)
		} else {
			query = query.Where(
				"review_status IN ? OR (review_status = ? AND uploaded_by_user_id = ?)",
				[]string{reviewStatusApproved, reviewStatusPending}, reviewStatusRejected, user.ID,
			)
		}
	}
	var total int64
	query.Count(&total)
	var papers []models.Paper
	query.Preload("KeyProperties").Order("created_at DESC").Limit(limit).Offset(offset).Find(&papers)
	items := make([]gin.H, 0, len(papers))
	for _, paper := range papers {
		items = append(items, paperForViewer(paper, user))
	}
	c.JSON(http.StatusOK, gin.H{"items": items, "total": total})
}

// PatchPaper 只允许上传者或管理员修改业务白名单字段。
func PatchPaper(c *gin.Context) {
	var paper models.Paper
	if err := database.DB.First(&paper, c.Param("id")).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "论文不存在"})
		return
	}
	user := optionalPaperUser(c)
	if user == nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "未登录"})
		return
	}
	if !paperOwner(&paper, user) && !paperAdmin(user) {
		c.JSON(http.StatusForbidden, gin.H{"error": "无权修改该论文"})
		return
	}
	var body map[string]interface{}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "参数错误"})
		return
	}
	updates := paperPatchUpdatesFromBody(body)
	if len(updates) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "没有可修改字段"})
		return
	}
	if err := database.DB.Model(&paper).Updates(updates).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "保存失败"})
		return
	}
	database.DB.Preload("KeyProperties").First(&paper, paper.ID)
	c.JSON(http.StatusOK, paperForViewer(paper, user))
}

// SearchRecords 扁平记录搜索（替代 Python POST /api/papers/search/records）
// 基于 key_properties 的 critical_temperature 物性，支持元素/化学式搜索 + 多维度筛选
func SearchRecords(c *gin.Context) {
	var body struct {
		Elements           []string `json:"elements"`
		Mode               string   `json:"mode"`
		Formula            string   `json:"formula"`
		Keyword            string   `json:"keyword"`
		YearMin            *int     `json:"year_min"`
		YearMax            *int     `json:"year_max"`
		TcMin              *float64 `json:"tc_min"`
		TcMax              *float64 `json:"tc_max"`
		PressureMin        *float64 `json:"pressure_min"`
		PressureMax        *float64 `json:"pressure_max"`
		SuperconductorType string   `json:"superconductor_type"`
		ReviewStatus       string   `json:"review_status"`
		SpaceGroupMin      *int     `json:"space_group_min"`
		SpaceGroupMax      *int     `json:"space_group_max"`
		ChartOnly          bool     `json:"chart_only"`
		Limit              int      `json:"limit"`
		Offset             int      `json:"offset"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "参数错误"})
		return
	}

	if body.Limit <= 0 {
		body.Limit = 50
	}

	// 缓存包含完整筛选条件，并使用新前缀隔离历史上可能含待审数据的缓存。
	rawKey, _ := json.Marshal(body)
	cacheKey := fmt.Sprintf("search:approved:%x", sha256.Sum256(rawKey))

	var cached gin.H
	if cache.Get(cacheKey, &cached) {
		c.JSON(http.StatusOK, cached)
		return
	}

	// 元素匹配 → 查 superconductors 表
	scIDs := getSuperconductorIDs(body.Elements, body.Mode, body.Formula)
	if len(scIDs) == 0 && len(body.Elements) > 0 {
		// 有元素查询但无匹配 → 返回空
		c.JSON(http.StatusOK, gin.H{"items": []interface{}{}, "total": 0})
		return
	}

	// JOIN tc_results + material_states + superconductors + papers
	query := approvedRecordSearchQuery(database.DB)

	if len(scIDs) > 0 {
		query = query.Where("material_states.superconductor_id IN ?", scIDs)
	}

	if body.Keyword != "" {
		like := "%" + body.Keyword + "%"
		query = query.Where(
			"(papers.title LIKE ? OR papers.doi LIKE ? OR papers.journal LIKE ? OR superconductors.chemical_formula LIKE ?)",
			like, like, like, like,
		)
	}
	if body.YearMin != nil {
		query = query.Where("papers.year >= ?", *body.YearMin)
	}
	if body.YearMax != nil {
		query = query.Where("papers.year <= ?", *body.YearMax)
	}
	if body.TcMin != nil {
		query = query.Where("tc_results.tc_value_k >= ?", *body.TcMin)
	}
	if body.TcMax != nil {
		query = query.Where("tc_results.tc_value_k <= ?", *body.TcMax)
	}
	if body.PressureMin != nil {
		query = query.Where("material_states.pressure_value_gpa >= ?", *body.PressureMin)
	}
	if body.PressureMax != nil {
		query = query.Where("material_states.pressure_value_gpa <= ?", *body.PressureMax)
	}
	if body.SuperconductorType != "" {
		query = query.Where("material_states.state_kind = ?", body.SuperconductorType)
	}
	// body.ChartOnly 不再生效：主记录标记是旧 key_properties 的概念，
	// 条件化模型中物性没有主次语义，无真实列可依据。

	// 计算 total
	var total int64
	query.Count(&total)

	// 排序 + 分页
	var rows []recordSearchRow
	query.Order("papers.year DESC, tc_results.id ASC").
		Offset(body.Offset).Limit(body.Limit).
		Find(&rows)

	items := make([]gin.H, 0, len(rows))
	for _, r := range rows {
		items = append(items, flatRecordToDict(r))
	}

	result := gin.H{"items": items, "total": total}
	cache.Set(cacheKey, result, 0) // 永久缓存
	c.JSON(http.StatusOK, result)
}

func approvedPaperDetailQuery(db *gorm.DB) *gorm.DB {
	return db.Preload("KeyProperties").Where("review_status = ?", reviewStatusApproved)
}

// approvedRecordSearchQuery 记录搜索的主体是 Tc 结果：一行代表「一个材料在一组条件下的一个 Tc」。
// 旧实现查 key_properties 表，该表在条件化模型迁移后已不存在，导致搜索恒返回空；
// Tc 现只存在于 tc_results，条件字段上提到 material_states。
func approvedRecordSearchQuery(db *gorm.DB) *gorm.DB {
	return db.Table("tc_results").
		Select("tc_results.*, material_states.*, superconductors.chemical_formula, papers.*").
		Joins("JOIN material_states ON material_states.id = tc_results.material_state_id").
		Joins("JOIN superconductors ON superconductors.id = material_states.superconductor_id").
		Joins("JOIN papers ON papers.id = tc_results.paper_id").
		Where("tc_results.tc_value_k IS NOT NULL").
		Where("papers.review_status = ?", reviewStatusApproved)
}

// ── helpers ────────────────────────────────────

func getSuperconductorIDs(elements []string, mode, formula string) []uint {
	// 清洗元素列表
	var symbols []string
	for _, e := range elements {
		e = strings.TrimSpace(e)
		if e != "" {
			symbols = append(symbols, e)
		}
	}

	// 化学式搜索
	if mode == "formula_search" && formula != "" {
		key := buildFormulaSystemKey(formula)
		if key == "" {
			return nil
		}
		var cs models.ChemicalSystem
		if err := database.DB.Where("system_key = ?", key).First(&cs).Error; err != nil {
			return nil
		}
		return superconductorIDsByCS([]uint{cs.ID})
	}

	if len(symbols) == 0 {
		return nil
	}

	// 加载所有 chemical_systems（与 Python 一致，内存过滤）
	var allCS []models.ChemicalSystem
	database.DB.Find(&allCS)

	selected := stringSet(symbols)
	matched := make(map[uint]bool)

	for _, cs := range allCS {
		csElements := parseElementsList(cs.ElementsList)

		switch mode {
		case "elements_exact_search":
			if stringSetEqual(csElements, selected) {
				matched[cs.ID] = true
			}
		case "elements_contained_search":
			if isSubset(selected, csElements) {
				matched[cs.ID] = true
			}
		default: // elements_combination_search (default)
			if isSubset(csElements, selected) {
				matched[cs.ID] = true
			}
		}
	}

	var csIDs []uint
	for id := range matched {
		csIDs = append(csIDs, id)
	}
	if len(csIDs) == 0 {
		return nil
	}

	return superconductorIDsByCS(csIDs)
}

func superconductorIDsByCS(csIDs []uint) []uint {
	var scIDs []uint
	database.DB.Model(&models.Superconductor{}).
		Where("chemical_system_id IN ?", csIDs).
		Pluck("id", &scIDs)
	return scIDs
}

// ── 集合/化学式辅助函数 ────────────────────────

func stringSet(items []string) map[string]bool {
	s := make(map[string]bool)
	for _, item := range items {
		s[item] = true
	}
	return s
}

func stringSetEqual(a, b map[string]bool) bool {
	if len(a) != len(b) {
		return false
	}
	for k := range a {
		if !b[k] {
			return false
		}
	}
	return true
}

func isSubset(sub, super map[string]bool) bool {
	for k := range sub {
		if !super[k] {
			return false
		}
	}
	return true
}

// parseElementsList 解析数据库中存储的 JSON 数组 ["H","La"] → set
func parseElementsList(raw string) map[string]bool {
	// 简单的 JSON 数组解析：["H","La"] 或 ["H", "La"]
	s := raw
	s = strings.Trim(s, "[]")
	result := make(map[string]bool)
	for _, part := range strings.Split(s, ",") {
		elem := strings.Trim(part, ` "`)
		if elem != "" {
			result[elem] = true
		}
	}
	return result
}

// buildFormulaSystemKey 从化学式构建 system_key（如 LaH10 → H-La）
func buildFormulaSystemKey(formula string) string {
	// 解析化学式中的元素符号（大写字母+可选小写字母）
	var elems []string
	i := 0
	runes := []rune(formula)
	for i < len(runes) {
		if runes[i] >= 'A' && runes[i] <= 'Z' {
			j := i + 1
			for j < len(runes) && runes[j] >= 'a' && runes[j] <= 'z' {
				j++
			}
			elems = append(elems, string(runes[i:j]))
			i = j
		} else {
			i++
		}
	}

	if len(elems) == 0 {
		return ""
	}

	// 排序
	sort.Strings(elems)
	return strings.Join(elems, "-")
}

func paperToDict(p models.Paper) gin.H {
	// 聚合 Tc：Tc 只存在于 tc_results，不在普通物性表中。
	// 旧实现按 key_properties.name == "critical_temperature" 聚合，在条件化模型下恒为空。
	var tcMax *float64
	for _, state := range p.MaterialStates {
		for _, result := range state.TcResults {
			value := result.TcValueK
			if value == nil {
				value = result.TcMaxK
			}
			if value == nil {
				continue
			}
			if tcMax == nil || *value > *tcMax {
				tcMax = value
			}
		}
	}

	return gin.H{
		"id":                    p.ID,
		"doi":                   p.DOI,
		"title":                 p.Title,
		"authors":               p.Authors,
		"journal":               p.Journal,
		"volume":                p.Volume,
		"pages":                 p.Pages,
		"year":                  p.Year,
		"abstract":              p.Abstract,
		"summary":               p.Summary,
		"paper_type":            p.PaperType,
		"theoretical_subtype":   p.TheoreticalSubtype,
		"keywords_tags":         p.KeywordsTags,
		"methodology":           p.Methodology,
		"knowledge_graph_title": p.KnowledgeGraphTitle,
		"key_finding":           p.KeyFinding,
		"research_motivation":   p.ResearchMotivation,
		"review_status":         p.ReviewStatus,
		"created_at":            p.CreatedAt,
		"updated_at":            p.UpdatedAt,
		"tc_max":                tcMax,
		"key_properties":        keyPropertiesToDict(p.KeyProperties),
		"material_states":       materialStatesToDict(p.MaterialStates),
	}
}

func materialStatesToDict(states []models.MaterialState) []gin.H {
	result := make([]gin.H, 0, len(states))
	for _, state := range states {
		var family interface{}
		if state.MaterialFamily != nil {
			family = gin.H{"id": state.MaterialFamily.ID, "name": state.MaterialFamily.NameZH, "status": "confirmed"}
		}
		structures := make([]gin.H, 0, len(state.StructureFamilyLinks))
		for _, link := range state.StructureFamilyLinks {
			structures = append(structures, gin.H{
				"id": link.StructureFamilyID, "name": link.StructureFamily.NameZH,
				"status": "confirmed", "is_primary": link.IsPrimary,
			})
		}
		result = append(result, gin.H{
			"id": state.ID, "material": state.Superconductor.ChemicalFormula,
			"material_family": family, "structure_families": structures,
			"element_count": state.ElementCount, "material_dimensionality": state.MaterialDimensionality,
			"superconductor_kind": state.SuperconductorKind,
			"crystal_system":      state.CrystalSystem,
			"state_kind":          state.StateKind,
			// 压强单臂区间：缺失的一侧保持 null，不补造边界（Issue #54 入库语义）。
			"pressure_value_gpa":          state.PressureValueGPa,
			"pressure_min_gpa":            state.PressureMinGPa,
			"pressure_max_gpa":            state.PressureMaxGPa,
			"pressure_raw":                state.PressureRaw,
			"pressure_unit_raw":           state.PressureUnitRaw,
			"reported_space_group_symbol": state.ReportedSpaceGroupSymbol,
			"reported_space_group_number": state.ReportedSpaceGroupNumber,
			"temperature_value_k":         state.TemperatureValueK,
			"temperature_raw":             state.TemperatureRaw,
			"magnetic_field_t":            state.MagneticFieldT,
			"note":                        state.Note,
			// Tc 与计算上下文的外键都是 material_state_id，因此嵌套在所属材料状态之下，
			// 消费方无需按 material_state_id 自行重建分组关系。
			"tc_results":           tcResultsToDict(state.TcResults),
			"calculation_contexts": calculationContextsToDict(state.CalculationContexts),
			"structures":           structureModelsToDict(state.Structures),
		})
	}
	return result
}

// structureModelsToDict 结构模型是结构预览的唯一来源；物性表没有结构文本列。
func structureModelsToDict(structures []models.StructureModel) []gin.H {
	output := make([]gin.H, 0, len(structures))
	for _, item := range structures {
		output = append(output, gin.H{
			"id":                 item.ID,
			"space_group_symbol": item.SpaceGroupSymbol,
			"space_group_number": item.SpaceGroupNumber,
			"structure_format":   item.StructureFormat,
			"structure_text":     item.StructureText,
			"cell_parameters":    item.CellParameters,
			"volume_angstrom3":   item.VolumeAngstrom3,
			"atom_count":         item.AtomCount,
			"geometry_method":    item.GeometryMethod,
			"calculation_code":   item.CalculationCode,
			"source_locator":     item.SourceLocator,
		})
	}
	return output
}

func tcResultsToDict(results []models.TcResult) []gin.H {
	output := make([]gin.H, 0, len(results))
	for _, item := range results {
		output = append(output, gin.H{
			"id":               item.ID,
			"result_kind":      item.ResultKind,
			"tc_method":        item.TcMethod,
			"tc_method_custom": item.TcMethodCustom,
			"tc_value_k":       item.TcValueK,
			"tc_min_k":         item.TcMinK,
			"tc_max_k":         item.TcMaxK,
			"uncertainty_k":    item.UncertaintyK,
			"value_raw":        item.ValueRaw,
			"unit_raw":         item.UnitRaw,
			"source_locator":   item.SourceLocator,
		})
	}
	return output
}

// calculationContextsToDict 返回全部计算上下文，包含数值全为 NULL 的记录：
// 读取侧不筛选也不合并，避免擅自判定哪一条才算有效。
func calculationContextsToDict(contexts []models.CalculationContext) []gin.H {
	output := make([]gin.H, 0, len(contexts))
	for _, item := range contexts {
		output = append(output, gin.H{
			"id":                       item.ID,
			"lambda_ep":                item.LambdaEP,
			"mu_star":                  item.MuStar,
			"omega_log_k":              item.OmegaLogK,
			"electronic_method":        item.ElectronicMethod,
			"exchange_correlation":     item.ExchangeCorrelation,
			"pseudopotential_type":     item.PseudopotentialType,
			"pseudopotential_name":     item.PseudopotentialName,
			"spin_orbit_coupling":      item.SpinOrbitCoupling,
			"phonon_method":            item.PhononMethod,
			"phonon_nuclear_treatment": item.PhononNuclearTreatment,
			"epc_method":               item.EPCMethod,
			"k_grid":                   item.KGrid,
			"q_grid":                   item.QGrid,
			"energy_cutoff_value":      item.EnergyCutoffValue,
			"energy_cutoff_unit":       item.EnergyCutoffUnit,
			"calculation_code":         item.CalculationCode,
			"missing_structure_reason": item.MissingStructureReason,
		})
	}
	return output
}

// propertyDisplayName 取物性的展示名：规范定义优先，缺失时回退原文名。
// 不返回空字符串——空名称无法与「该论文确实没有名称」区分，对消费方是误导。
func propertyDisplayName(kp models.KeyProperty) string {
	if kp.PropertyDefinition != nil && kp.PropertyDefinition.DisplayName != "" {
		return kp.PropertyDefinition.DisplayName
	}
	return kp.NameRaw
}

// keyPropertiesToDict 只输出 superconductor_properties 的真实列。
// 条件类字段（压强、温度）属材料状态，结构文本属 structure_models，均不在此重复。
func keyPropertiesToDict(kps []models.KeyProperty) []gin.H {
	result := make([]gin.H, 0, len(kps))
	for _, kp := range kps {
		result = append(result, gin.H{
			"id":                kp.ID,
			"paper_id":          kp.PaperID,
			"material_state_id": kp.MaterialStateID,
			"material":          kp.Material,
			"name":              propertyDisplayName(kp),
			"name_raw":          kp.NameRaw,
			"value_min":         kp.ValueMin,
			"value_max":         kp.ValueMax,
			"value_raw":         kp.ValueRaw,
			"value_number":      kp.ValueNumber,
			"unit":              kp.Unit,
			"canonical_unit":    kp.CanonicalUnit,
			"condition_note":    kp.ConditionNote,
		})
	}
	return result
}

// SearchAll 跨源聚合搜索（替代 Python POST /api/papers/search/all）
func SearchAll(c *gin.Context) {
	var body struct {
		Elements []string `json:"elements"`
		Mode     string   `json:"mode"`
		Limit    int      `json:"limit"`
		Offset   int      `json:"offset"`
	}
	if err := c.ShouldBindJSON(&body); err != nil || len(body.Elements) == 0 {
		c.JSON(http.StatusOK, gin.H{"items": []any{}, "total": 0})
		return
	}
	if body.Limit <= 0 {
		body.Limit = 30
	}

	// 1. Local
	items := searchLocalAll(body.Elements, body.Mode)
	// 2. Alexandria
	items = append(items, searchAlexandriaAll(body.Elements, body.Mode)...)
	// 3. HTSC
	items = append(items, searchHTSCAll(body.Elements, body.Mode)...)

	// 4. 按 compound 分组
	type compoundGroup struct {
		key   string
		items []gin.H
	}
	groups := make(map[string]*compoundGroup)
	var order []string
	for _, item := range items {
		key := ""
		if src, _ := item["_source"].(string); src == "local" {
			if f, ok := item["compound_symbols"].(string); ok && f != "" {
				key = f
			}
		}
		if key == "" {
			src, _ := item["_source"].(string)
			if src == "" {
				src = "unknown"
			}
			f := ""
			switch v := item["formula"].(type) {
			case string:
				f = v
			case *string:
				if v != nil {
					f = *v
				}
			}
			key = f + "-" + src
		}
		if groups[key] == nil {
			groups[key] = &compoundGroup{key: key}
			order = append(order, key)
		}
		groups[key].items = append(groups[key].items, item)
	}

	// 5. 组内按 Tc 降序
	for _, g := range groups {
		sort.Slice(g.items, func(i, j int) bool {
			return tcFromItem(g.items[i]) > tcFromItem(g.items[j])
		})
	}

	// 6. 组间：本地优先，然后按 Tc 降序
	sort.SliceStable(order, func(i, j int) bool {
		a, b := groups[order[i]], groups[order[j]]
		aLocal := countLocal(a.items)
		bLocal := countLocal(b.items)
		if aLocal != bLocal {
			return aLocal > bLocal
		}
		return tcFromItem(a.items[0]) > tcFromItem(b.items[0])
	})

	// 7. 展平
	type itemWithType struct {
		Type string `json:"_type,omitempty"`
		gin.H
	}
	flat := make([]any, 0)
	for _, key := range order {
		g := groups[key]
		flat = append(flat, gin.H{"_type": "section", "key": key, "count": len(g.items)})
		for _, item := range g.items {
			flat = append(flat, item)
		}
	}

	start := body.Offset
	if start > len(flat) {
		start = len(flat)
	}
	end := start + body.Limit
	if end > len(flat) {
		end = len(flat)
	}

	total := 0
	for _, it := range flat {
		if m, ok := it.(gin.H); !ok || m["_type"] == nil {
			total++
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"items":       flat[start:end],
		"total":       total,
		"total_pages": (total + body.Limit - 1) / max(body.Limit, 1),
	})
}

func searchLocalAll(elements []string, mode string) []gin.H {
	scIDs := getSuperconductorIDs(elements, mode, "")
	if len(scIDs) == 0 {
		return nil
	}

	// 材料归属在 material_states.superconductor_id；key_properties 表已不存在。
	var papers []models.Paper
	database.DB.
		Preload("KeyProperties.PropertyDefinition").
		Preload("MaterialStates.Superconductor").
		Preload("MaterialStates.TcResults").
		Where("review_status = ?", reviewStatusApproved).
		Where("id IN (SELECT DISTINCT paper_id FROM material_states WHERE superconductor_id IN ?)", scIDs).
		Find(&papers)

	result := make([]gin.H, 0)
	for _, p := range papers {
		d := paperToDict(p)
		d["_source"] = "local"
		d["compound_symbols"] = ""
		// 化学式取自材料状态关联的超导体，物性的 material_raw 只作回退。
		for _, state := range p.MaterialStates {
			if state.Superconductor.ChemicalFormula != "" {
				d["compound_symbols"] = state.Superconductor.ChemicalFormula
				break
			}
		}
		if cs, _ := d["compound_symbols"].(string); cs == "" {
			for _, kp := range p.KeyProperties {
				if kp.Material != "" {
					d["compound_symbols"] = kp.Material
					break
				}
			}
		}
		result = append(result, d)
	}
	return result
}

func searchAlexandriaAll(elements []string, mode string) []gin.H {
	entryIDs := alexEntryIDs(elements, mode)
	if len(entryIDs) == 0 {
		return nil
	}

	var entries []models.AlexandriaEntry
	database.DB.Where("id IN ? AND imag = ?", entryIDs, false).
		Where("(tc_max IS NOT NULL OR tc_allen_dynes IS NOT NULL)").Find(&entries)

	result := make([]gin.H, 0)
	for _, e := range entries {
		tc := e.TcMax
		if tc == nil {
			tc = e.TcAllenDynes
		}
		elems := parseElementsList(*e.Elements)
		elemSlice := make([]string, 0, len(elems))
		for k := range elems {
			elemSlice = append(elemSlice, k)
		}
		sort.Strings(elemSlice)

		result = append(result, gin.H{
			"_source":        "alexandria",
			"mat_id":         e.MatID,
			"formula":        e.Formula,
			"elements":       elemSlice,
			"tc_max":         e.TcMax,
			"tc_allen_dynes": e.TcAllenDynes,
			"spg":            e.SPG,
		})
	}
	return result
}

func searchHTSCAll(elements []string, mode string) []gin.H {
	var mats []models.HTSCMaterial
	database.DB.Where("tc IS NOT NULL").Find(&mats)

	selected := stringSet(elements)
	result := make([]gin.H, 0)
	for _, m := range mats {
		matElems := parseElementsList(m.Elements)
		if len(matElems) == 0 || !matchesElements(matElems, selected, mode) {
			continue
		}

		elemSlice := make([]string, 0, len(matElems))
		for k := range matElems {
			elemSlice = append(elemSlice, k)
		}
		sort.Strings(elemSlice)

		result = append(result, gin.H{
			"_source":    "htsc2025",
			"formula":    m.Formula,
			"name":       m.Name,
			"tc":         m.Tc,
			"elements":   elemSlice,
			"class_name": m.ClassName,
		})
	}
	return result
}

func tcFromItem(item gin.H) float64 {
	if src, _ := item["_source"].(string); src == "htsc2025" {
		if v, ok := item["tc"].(float64); ok {
			return v
		}
	}
	if v, ok := item["tc_allen_dynes"].(*float64); ok && v != nil {
		return *v
	}
	if v, ok := item["tc_max"].(*float64); ok && v != nil {
		return *v
	}
	if v, ok := item["tc_max"].(float64); ok {
		return v
	}
	return 0
}

func countLocal(items []gin.H) int {
	n := 0
	for _, it := range items {
		if src, _ := it["_source"].(string); src == "local" {
			n++
		}
	}
	return n
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

// recordSearchRow 承接 approvedRecordSearchQuery 的一行：Tc 结果 + 所属材料状态 + 化学式 + 论文。
type recordSearchRow struct {
	models.TcResult
	models.MaterialState
	ChemicalFormula string
	models.Paper
}

func flatRecordToDict(row recordSearchRow) gin.H {
	pressure := "-"
	if row.MaterialState.PressureValueGPa != nil {
		pressure = strconv.FormatFloat(*row.MaterialState.PressureValueGPa, 'g', -1, 64) + " GPa"
	}

	tc := "-"
	if row.TcResult.TcValueK != nil {
		tc = strconv.FormatFloat(*row.TcResult.TcValueK, 'f', 1, 64) + " K"
	} else if row.TcResult.TcMinK != nil && row.TcResult.TcMaxK != nil {
		tc = strconv.FormatFloat(*row.TcResult.TcMinK, 'f', 1, 64) + "–" +
			strconv.FormatFloat(*row.TcResult.TcMaxK, 'f', 1, 64) + " K"
	}

	spaceGroup := "-"
	if row.MaterialState.ReportedSpaceGroupSymbol != nil && *row.MaterialState.ReportedSpaceGroupSymbol != "" {
		spaceGroup = *row.MaterialState.ReportedSpaceGroupSymbol
	}

	statusMap := map[string]string{
		"pending": "Pending", "approved": "Approved", "reviewed": "Approved", "rejected": "Rejected",
	}
	status := statusMap[row.Paper.ReviewStatus]
	if status == "" {
		status = "Pending"
	}

	year := 0
	if row.Paper.Year != nil {
		year = *row.Paper.Year
	}

	return gin.H{
		"record_id":   row.TcResult.ID,
		"paper_id":    row.Paper.ID,
		"year":        year,
		"formula":     row.ChemicalFormula,
		"type":        row.MaterialState.StateKind,
		"pressure":    pressure,
		"tc":          tc,
		"space_group": spaceGroup,
		"source":      "Local",
		"status":      status,
		"doi":         row.Paper.DOI,
	}
}
