package handlers

import (
	"net/http"

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
	type row struct {
		Material  string  `json:"material"`
		Tc        float64 `json:"y"`
		Pressure  float64 `json:"x"`
		Year      *int    `json:"year"`
		SCType    string  `json:"sc_type"`
		Type      string  `json:"type"`
	}
	var rows []row
	database.DB.Table("key_properties").
		Select("material, value_max AS y, COALESCE(pressure_gpa,0) AS x, superconductor_type AS sc_type, article_type AS type").
		Where("name = ? AND value_max IS NOT NULL AND pressure_gpa IS NOT NULL AND is_primary = ?", "critical_temperature", true).
		Find(&rows)

	for i := range rows {
		if rows[i].Type == "e" {
			rows[i].Type = "experimental"
		} else {
			rows[i].Type = "theoretical"
		}
	}
	c.JSON(http.StatusOK, rows)
}

// TcYearChart Tc-Year 散点图数据
// GET /api/papers/stats/tc-year
func TcYearChart(c *gin.Context) {
	type row struct {
		Year     int     `json:"x"`
		Tc       float64 `json:"y"`
		Type     string  `json:"type"`
		SCType   string  `json:"sc_type"`
		Material string  `json:"formula"`
		DOI      string  `json:"doi"`
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
	`).Find(&rows)
	c.JSON(http.StatusOK, rows)
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
