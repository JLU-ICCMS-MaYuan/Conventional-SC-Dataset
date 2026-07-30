package handlers

import (
	"net/http"

	"scwiki/server/cache"
	"scwiki/server/database"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
)

// ═══════════════════════════════════════════════
// 统计 API（替代 Python papers stats + admin users）
// ═══════════════════════════════════════════════

// TcPressureChart Tc-P 散点图数据
// GET /api/papers/stats/tc-pressure
func TcPressureChart(c *gin.Context) {
	const cacheKey = "chart:tc_pressure"
	var result []gin.H
	if cache.Get(cacheKey, &result) {
		c.JSON(http.StatusOK, result)
		return
	}

	type row struct {
		Material string  `gorm:"column:material"`
		Tc       float64 `gorm:"column:y"`
		Pressure float64 `gorm:"column:x"`
		SCType   string  `gorm:"column:sc_type"`
		Type     string  `gorm:"column:type"`
	}
	var rows []row
	database.DB.Raw(`
		SELECT material, value_max AS y, COALESCE(pressure_gpa,0) AS x,
			COALESCE(superconductor_type,'others') AS sc_type,
			CASE WHEN article_type='e' THEN 'experimental' ELSE 'theoretical' END AS type
		FROM key_properties
		WHERE name = 'critical_temperature' AND value_max IS NOT NULL
		AND pressure_gpa IS NOT NULL AND is_primary = true
	`).Scan(&rows)

	for _, r := range rows {
		t := r.Type
		if t == "" { t = "theoretical" }
		result = append(result, gin.H{
			"material": r.Material, "formula": r.Material, "label": r.Material,
			"y": r.Tc, "x": r.Pressure,
			"sc_type": r.SCType, "type": t,
		})
	}
	cache.Set(cacheKey, result, 0) // 永久缓存
	c.JSON(http.StatusOK, result)
}

// TcYearChart Tc-Year 散点图数据
// GET /api/papers/stats/tc-year
func TcYearChart(c *gin.Context) {
	const cacheKey = "chart:tc_year"
	var result []gin.H
	if cache.Get(cacheKey, &result) {
		c.JSON(http.StatusOK, result)
		return
	}

	type row struct {
		Year     int     `gorm:"column:x"`
		Tc       float64 `gorm:"column:y"`
		Type     string  `gorm:"column:type"`
		SCType   string  `gorm:"column:sc_type"`
		Material string  `gorm:"column:formula"`
		DOI      string  `gorm:"column:doi"`
	}
	var rows []row
	database.DB.Raw(`
		SELECT p.year AS x, kp.value_max AS y,
			CASE WHEN kp.article_type='e' THEN 'experimental' ELSE 'theoretical' END AS type,
			COALESCE(kp.superconductor_type,'others') AS sc_type,
			kp.material AS formula, COALESCE(p.doi,'') AS doi
		FROM key_properties kp JOIN papers p ON kp.paper_id = p.id
		WHERE kp.name = 'critical_temperature' AND kp.value_max IS NOT NULL
		AND p.year IS NOT NULL AND kp.is_primary = true
	`).Scan(&rows)

	result = make([]gin.H, 0, len(rows))
	for _, r := range rows {
		t := r.Type
		if t == "" { t = "theoretical" }
		result = append(result, gin.H{
			"x": r.Year, "y": r.Tc, "type": t,
			"sc_type": r.SCType, "formula": r.Material, "doi": r.DOI,
		})
	}
	cache.Set(cacheKey, result, 0) // 永久缓存
	c.JSON(http.StatusOK, result)
}

// AllUsers 用户列表（替代 Python /api/admin/all-users）
// GET /api/admin/all-users
func AllUsers(c *gin.Context) {
	var users []models.User
	database.DB.Find(&users)

	type userInfo struct {
		models.User
		SubmittedCount int64 `json:"submitted_count"`
		ReviewedCount  int64 `json:"reviewed_count"`
	}

	result := make([]userInfo, 0, len(users))
	for _, u := range users {
		ui := userInfo{User: u}
		database.DB.Model(&models.Paper{}).Where("uploaded_by_user_id = ?", u.ID).Count(&ui.SubmittedCount)
		database.DB.Model(&models.Paper{}).Where("reviewed_by_user_id = ?", u.ID).Count(&ui.ReviewedCount)
		result = append(result, ui)
	}
	c.JSON(http.StatusOK, result)
}

// BatchReview 批量审核
// POST /api/admin/papers/batch-review
func BatchReview(c *gin.Context) {
	var body struct {
		PaperIDs []uint `json:"paper_ids"`
		Status   string `json:"status"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "参数错误"})
		return
	}
	database.DB.Model(&models.Paper{}).Where("id IN ?", body.PaperIDs).Update("review_status", body.Status)
	c.JSON(http.StatusOK, gin.H{"message": "批量审核完成"})
}

// BatchDelete 批量删除
// POST /api/admin/papers/batch-delete
func BatchDelete(c *gin.Context) {
	var body struct {
		PaperIDs []uint `json:"paper_ids"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "参数错误"})
		return
	}
	database.DB.Where("paper_id IN ?", body.PaperIDs).Delete(&models.KeyProperty{})
	database.DB.Delete(&models.Paper{}, body.PaperIDs)
	c.JSON(http.StatusOK, gin.H{"message": "批量删除完成"})
}
