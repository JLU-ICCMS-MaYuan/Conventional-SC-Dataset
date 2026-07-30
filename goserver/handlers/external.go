package handlers

import (
	"net/http"

	"scwiki/server/database"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
)

// ═══════════════════════════════════════════════
// 外部数据源 API（替代 Python /api/alexandria/* + /api/htsc2025/*）
// ═══════════════════════════════════════════════

// SearchAlexandria 搜索 Alexandria 数据集
// POST /api/alexandria/search
func SearchAlexandria(c *gin.Context) {
	var body struct {
		Elements      []string `json:"elements"`
		Mode          string   `json:"mode"`
		TcMin         *float64 `json:"tc_min"`
		TcMax         *float64 `json:"tc_max"`
		PressureMin   *float64 `json:"pressure_min"`
		PressureMax   *float64 `json:"pressure_max"`
		SpaceGroupMin *int     `json:"space_group_min"`
		SpaceGroupMax *int     `json:"space_group_max"`
		Limit         int      `json:"limit"`
		Offset        int      `json:"offset"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "参数错误"})
		return
	}
	if body.Limit <= 0 {
		body.Limit = 50
	}

	// 找到匹配的元素→entry 映射
	entryIDs := alexEntryIDs(body.Elements, body.Mode)
	if len(body.Elements) > 0 && len(entryIDs) == 0 {
		c.JSON(http.StatusOK, gin.H{"items": []any{}, "total": 0})
		return
	}

	query := database.DB.Model(&models.AlexandriaEntry{}).
		Where("imag = ?", false).
		Where("(tc_max IS NOT NULL OR tc_allen_dynes IS NOT NULL)")

	if len(entryIDs) > 0 {
		query = query.Where("id IN ?", entryIDs)
	}
	if body.TcMin != nil {
		query = query.Where("COALESCE(tc_max, tc_allen_dynes) >= ?", *body.TcMin)
	}
	if body.TcMax != nil {
		query = query.Where("COALESCE(tc_max, tc_allen_dynes) <= ?", *body.TcMax)
	}
	if body.SpaceGroupMin != nil {
		query = query.Where("spg >= ?", *body.SpaceGroupMin)
	}
	if body.SpaceGroupMax != nil {
		query = query.Where("spg <= ?", *body.SpaceGroupMax)
	}

	var total int64
	query.Count(&total)

	var entries []models.AlexandriaEntry
	query.Limit(body.Limit).Offset(body.Offset).Find(&entries)

	items := make([]gin.H, 0, len(entries))
	for _, e := range entries {
		tc := e.TcMax
		if tc == nil {
			tc = e.TcAllenDynes
		}
		items = append(items, gin.H{
			"mat_id":        e.MatID,
			"formula":       e.Formula,
			"elements":      e.Elements,
			"tc_max":        e.TcMax,
			"tc_allen_dynes": e.TcAllenDynes,
			"tc_mcmillan":   e.TcMcMillan,
			"tc_eliashberg": e.TcEliashberg,
			"spg":           e.SPG,
			"wlog":          e.WLog,
			"dos_ef":        e.DosEf,
			"band_gap":      e.BandGap,
			"e_above_hull":  e.EAboveHull,
			"structure_cif": e.StructureCIF,
			"nsites":        e.NSites,
			"lambda_val":    e.LambdaVal,
			"_source":       "alexandria",
		})
	}

	c.JSON(http.StatusOK, gin.H{"items": items, "total": int(total)})
}

// SearchHTSC 搜索 HTSC-2025 数据集
// POST /api/htsc2025/search
func SearchHTSC(c *gin.Context) {
	var body struct {
		Elements    []string `json:"elements"`
		Mode        string   `json:"mode"`
		TcMin       *float64 `json:"tc_min"`
		TcMax       *float64 `json:"tc_max"`
		PressureMin *float64 `json:"pressure_min"`
		PressureMax *float64 `json:"pressure_max"`
		Limit       int      `json:"limit"`
		Offset      int      `json:"offset"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "参数错误"})
		return
	}
	if body.Limit <= 0 {
		body.Limit = 50
	}

	query := database.DB.Model(&models.HTSCMaterial{}).Where("tc IS NOT NULL")

	if len(body.Elements) > 0 {
		var ids []uint
		for _, mat := range allHTSCMaterials() {
			elemStr := ""
			if mat.Elements != nil {
				elemStr = *mat.Elements
			}
			matElements := parseElementsList(elemStr)
			selected := stringSet(body.Elements)
			if matchesElements(matElements, selected, body.Mode) {
				ids = append(ids, mat.ID)
			}
		}
		if len(ids) == 0 {
			c.JSON(http.StatusOK, gin.H{"items": []any{}, "total": 0})
			return
		}
		query = query.Where("id IN ?", ids)
	}

	if body.TcMin != nil {
		query = query.Where("tc >= ?", *body.TcMin)
	}
	if body.TcMax != nil {
		query = query.Where("tc <= ?", *body.TcMax)
	}

	var total int64
	query.Count(&total)

	var materials []models.HTSCMaterial
	query.Limit(body.Limit).Offset(body.Offset).Order("tc DESC").Find(&materials)

	items := make([]gin.H, 0, len(materials))
	for _, m := range materials {
		items = append(items, gin.H{
			"name":        m.Name,
			"formula":     m.Formula,
			"class_name":  m.ClassName,
			"tc":          m.Tc,
			"elements":    m.Elements,
			"composition": m.Composition,
			"_source":     "htsc2025",
		})
	}

	c.JSON(http.StatusOK, gin.H{"items": items, "total": int(total)})
}

// ── helpers ────────────────────────────────────

func alexEntryIDs(elements []string, mode string) []uint {
	if len(elements) == 0 {
		return nil
	}

	// 元素匹配逻辑（与 Python 一致）
	selected := stringSet(elements)
	var allIdx []models.AlexandriaElementIdx
	database.DB.Find(&allIdx)

	// 按 entry_id 分组
	entryElements := make(map[uint]map[string]bool)
	for _, idx := range allIdx {
		if entryElements[idx.EntryID] == nil {
			entryElements[idx.EntryID] = make(map[string]bool)
		}
		entryElements[idx.EntryID][idx.Element] = true
	}

	var ids []uint
	for entryID, elems := range entryElements {
		if matchesElements(elems, selected, mode) {
			ids = append(ids, entryID)
		}
	}
	return ids
}

func allHTSCMaterials() []models.HTSCMaterial {
	var mats []models.HTSCMaterial
	database.DB.Find(&mats)
	return mats
}

func matchesElements(materialElems, selected map[string]bool, mode string) bool {
	switch mode {
	case "elements_exact_search":
		return stringSetEqual(materialElems, selected)
	case "elements_contained_search":
		return isSubset(selected, materialElems)
	default: // elements_combination_search
		return isSubset(materialElems, selected)
	}
}

// elemStr 辅助：转换 elements JSON 字符串到 set
