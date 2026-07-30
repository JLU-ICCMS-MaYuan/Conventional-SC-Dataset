package handlers

import (
	"net/http"
	"sort"
	"strconv"
	"strings"

	"scwiki/server/database"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
)

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
	if err := database.DB.Preload("KeyProperties").First(&paper, uint(id)).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "论文不存在"})
		return
	}

	c.JSON(http.StatusOK, paperToDict(paper))
}

// SearchRecords 扁平记录搜索（替代 Python POST /api/papers/search/records）
// 基于 key_properties 的 critical_temperature 物性，支持元素/化学式搜索 + 多维度筛选
func SearchRecords(c *gin.Context) {
	var body struct {
		Elements            []string `json:"elements"`
		Mode                string   `json:"mode"`
		Formula             string   `json:"formula"`
		Keyword             string   `json:"keyword"`
		YearMin             *int     `json:"year_min"`
		YearMax             *int     `json:"year_max"`
		TcMin               *float64 `json:"tc_min"`
		TcMax               *float64 `json:"tc_max"`
		PressureMin         *float64 `json:"pressure_min"`
		PressureMax         *float64 `json:"pressure_max"`
		SuperconductorType  string   `json:"superconductor_type"`
		ReviewStatus        string   `json:"review_status"`
		SpaceGroupMin       *int     `json:"space_group_min"`
		SpaceGroupMax       *int     `json:"space_group_max"`
		ChartOnly           bool     `json:"chart_only"`
		Limit               int      `json:"limit"`
		Offset              int      `json:"offset"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "参数错误"})
		return
	}

	if body.Limit <= 0 {
		body.Limit = 50
	}

	// 元素匹配 → 查 superconductors 表
	scIDs := getSuperconductorIDs(body.Elements, body.Mode, body.Formula)
	if len(scIDs) == 0 && len(body.Elements) > 0 {
		// 有元素查询但无匹配 → 返回空
		c.JSON(http.StatusOK, gin.H{"items": []interface{}{}, "total": 0})
		return
	}

	// JOIN key_properties + papers
	query := database.DB.Table("key_properties").
		Select("key_properties.*, papers.*").
		Joins("JOIN papers ON key_properties.paper_id = papers.id").
		Where("key_properties.name = ?", "critical_temperature").
		Where("key_properties.value_max IS NOT NULL")

	if len(scIDs) > 0 {
		query = query.Where("key_properties.superconductor_id IN ?", scIDs)
	}

	if body.Keyword != "" {
		like := "%" + body.Keyword + "%"
		query = query.Where(
			"(papers.title LIKE ? OR papers.doi LIKE ? OR papers.journal LIKE ? OR key_properties.material LIKE ?)",
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
		query = query.Where("key_properties.value_max >= ?", *body.TcMin)
	}
	if body.TcMax != nil {
		query = query.Where("key_properties.value_min <= ?", *body.TcMax)
	}
	if body.PressureMin != nil {
		query = query.Where("key_properties.pressure_gpa >= ?", *body.PressureMin)
	}
	if body.PressureMax != nil {
		query = query.Where("key_properties.pressure_gpa <= ?", *body.PressureMax)
	}
	if body.SuperconductorType != "" {
		query = query.Where("key_properties.superconductor_type = ?", body.SuperconductorType)
	}
	if body.ReviewStatus != "" {
		query = query.Where("papers.review_status = ?", body.ReviewStatus)
	}
	if body.ChartOnly {
		query = query.Where("key_properties.is_primary = true")
	}

	// 计算 total
	var total int64
	query.Count(&total)

	// 排序 + 分页
	type row struct {
		models.KeyProperty
		models.Paper
	}

	var rows []row
	query.Order("papers.year DESC, key_properties.id ASC").
		Offset(body.Offset).Limit(body.Limit).
		Find(&rows)

	items := make([]gin.H, 0, len(rows))
	for _, r := range rows {
		items = append(items, flatRecordToDict(r.KeyProperty, r.Paper))
	}

	c.JSON(http.StatusOK, gin.H{"items": items, "total": total})
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
	// 聚合 Tc
	var tcMax *float64
	for _, kp := range p.KeyProperties {
		if kp.Name == "critical_temperature" && kp.ValueMax != nil {
			if tcMax == nil || *kp.ValueMax > *tcMax {
				tcMax = kp.ValueMax
			}
		}
	}

	return gin.H{
		"id":                   p.ID,
		"doi":                  p.DOI,
		"title":                p.Title,
		"authors":              p.Authors,
		"journal":              p.Journal,
		"volume":               p.Volume,
		"pages":                p.Pages,
		"year":                 p.Year,
		"abstract":             p.Abstract,
		"summary":              p.Summary,
		"paper_type":           p.PaperType,
		"keywords_tags":        p.KeywordsTags,
		"methodology":          p.Methodology,
		"key_finding":          p.KeyFinding,
		"rationale":            p.Rationale,
		"review_status":        p.ReviewStatus,
		"review_comment":       p.ReviewComment,
		"reviewed_by_user_id":  p.ReviewedBy,
		"uploaded_by_user_id":  p.UploadedBy,
		"created_at":           p.CreatedAt,
		"updated_at":           p.UpdatedAt,
		"tc_max":               tcMax,
		"key_properties":       keyPropertiesToDict(p.KeyProperties),
	}
}

func keyPropertiesToDict(kps []models.KeyProperty) []gin.H {
	result := make([]gin.H, 0, len(kps))
	for _, kp := range kps {
		result = append(result, gin.H{
			"id":                  kp.ID,
			"paper_id":            kp.PaperID,
			"superconductor_id":   kp.SuperconductorID,
			"material":            kp.Material,
			"name":                kp.Name,
			"name_raw":            kp.NameRaw,
			"name_note":           kp.NameNote,
			"value_min":           kp.ValueMin,
			"value_max":           kp.ValueMax,
			"value_raw":           kp.ValueRaw,
			"unit":                kp.Unit,
			"pressure_gpa":        kp.PressureGpa,
			"temperature_k":       kp.TemperatureK,
			"condition_note":      kp.ConditionNote,
			"is_primary":          kp.IsPrimary,
			"superconductor_type": kp.SuperconductorType,
			"article_type":        kp.ArticleType,
			"source_label":        kp.SourceLabel,
			"structure_text":      kp.StructureText,
			"structure_format":    kp.StructureFormat,
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
	if body.Limit <= 0 { body.Limit = 30 }

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
			if f, ok := item["compound_symbols"].(string); ok && f != "" { key = f }
		}
		if key == "" {
			src, _ := item["_source"].(string)
			if src == "" { src = "unknown" }
			f := ""
			switch v := item["formula"].(type) {
			case string: f = v
			case *string: if v != nil { f = *v }
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
		aLocal := countLocal(a.items); bLocal := countLocal(b.items)
		if aLocal != bLocal { return aLocal > bLocal }
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
	if start > len(flat) { start = len(flat) }
	end := start + body.Limit
	if end > len(flat) { end = len(flat) }

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
	if len(scIDs) == 0 { return nil }

	var papers []models.Paper
	database.DB.Preload("KeyProperties").
		Where("id IN (SELECT DISTINCT paper_id FROM key_properties WHERE superconductor_id IN ?)", scIDs).
		Find(&papers)

	result := make([]gin.H, 0)
	for _, p := range papers {
		d := paperToDict(p)
		d["_source"] = "local"
		d["compound_symbols"] = ""
		// 从 key_properties 推断 compound_symbols
		for _, kp := range p.KeyProperties {
			if kp.Material != "" {
				if cs, ok := d["compound_symbols"].(string); ok && cs == "" {
					d["compound_symbols"] = kp.Material
				}
			}
		}
		result = append(result, d)
	}
	return result
}

func searchAlexandriaAll(elements []string, mode string) []gin.H {
	entryIDs := alexEntryIDs(elements, mode)
	if len(entryIDs) == 0 { return nil }

	var entries []models.AlexandriaEntry
	database.DB.Where("id IN ? AND imag = ?", entryIDs, false).
		Where("(tc_max IS NOT NULL OR tc_allen_dynes IS NOT NULL)").Find(&entries)

	result := make([]gin.H, 0)
	for _, e := range entries {
		tc := e.TcMax
		if tc == nil { tc = e.TcAllenDynes }
		elems := parseElementsList(*e.Elements)
		elemSlice := make([]string, 0, len(elems))
		for k := range elems { elemSlice = append(elemSlice, k) }
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
		if len(matElems) == 0 || !matchesElements(matElems, selected, mode) { continue }

		elemSlice := make([]string, 0, len(matElems))
		for k := range matElems { elemSlice = append(elemSlice, k) }
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
		if v, ok := item["tc"].(float64); ok { return v }
	}
	if v, ok := item["tc_allen_dynes"].(*float64); ok && v != nil { return *v }
	if v, ok := item["tc_max"].(*float64); ok && v != nil { return *v }
	if v, ok := item["tc_max"].(float64); ok { return v }
	return 0
}

func countLocal(items []gin.H) int {
	n := 0
	for _, it := range items {
		if src, _ := it["_source"].(string); src == "local" { n++ }
	}
	return n
}

func max(a, b int) int {
	if a > b { return a }
	return b
}

func flatRecordToDict(kp models.KeyProperty, paper models.Paper) gin.H {
	pressure := "-"
	if kp.PressureGpa != nil {
		pressure = strconv.FormatFloat(*kp.PressureGpa, 'g', -1, 64) + " GPa"
	}

	tc := "-"
	if kp.ValueMax != nil {
		if kp.ValueMin != nil && *kp.ValueMin != *kp.ValueMax {
			tc = strconv.FormatFloat(*kp.ValueMin, 'f', 1, 64) + "–" + strconv.FormatFloat(*kp.ValueMax, 'f', 1, 64) + " K"
		} else {
			tc = strconv.FormatFloat(*kp.ValueMax, 'f', 1, 64) + " K"
		}
	}

	statusMap := map[string]string{
		"pending": "Pending", "approved": "Approved", "reviewed": "Approved", "rejected": "Rejected",
	}
	status := statusMap[paper.ReviewStatus]
	if status == "" {
		status = "Pending"
	}

	year := 0
	if paper.Year != nil {
		year = *paper.Year
	}

	return gin.H{
		"record_id":  kp.ID,
		"paper_id":   paper.ID,
		"year":       year,
		"formula":    kp.Material,
		"type":       kp.SuperconductorType,
		"pressure":   pressure,
		"tc":         tc,
		"space_group": "-",
		"source":     "Local",
		"status":     status,
		"doi":        paper.DOI,
	}
}
