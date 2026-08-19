package handlers

import (
	"fmt"
	"log"
	"net/http"
	"time"

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
	const cacheKey = "chart:approved:tc_pressure"
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
		PaperID  uint    `gorm:"column:paper_id"`
	}
	var rows []row
	database.DB.Raw(`
		SELECT material, value_max AS y, COALESCE(pressure_gpa,0) AS x,
			COALESCE(superconductor_type,'others') AS sc_type,
			CASE WHEN article_type='e' THEN 'experimental' ELSE 'theoretical' END AS type,
			paper_id
			FROM key_properties kp JOIN papers p ON kp.paper_id = p.id
			WHERE kp.name = 'critical_temperature' AND kp.value_max IS NOT NULL
			AND kp.pressure_gpa IS NOT NULL AND kp.is_primary = true
			AND p.review_status = 'approved'
	`).Scan(&rows)

	for _, r := range rows {
		t := r.Type
		if t == "" {
			t = "theoretical"
		}
		item := gin.H{
			"formula": r.Material,
			"y":       r.Tc, "x": r.Pressure,
			"sc_type": r.SCType, "type": t,
		}
		if r.PaperID > 0 {
			item["paper_id"] = r.PaperID
		}
		result = append(result, item)
	}
	cache.Set(cacheKey, result, 0) // 永久缓存
	c.JSON(http.StatusOK, result)
}

// TcYearChart Tc-Year 散点图数据
// GET /api/papers/stats/tc-year
func TcYearChart(c *gin.Context) {
	const cacheKey = "chart:approved:tc_year"
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
		PaperID  uint    `gorm:"column:paper_id"`
	}
	var rows []row
	database.DB.Raw(`
		SELECT p.year AS x, kp.value_max AS y,
			CASE WHEN kp.article_type='e' THEN 'experimental' ELSE 'theoretical' END AS type,
			COALESCE(kp.superconductor_type,'others') AS sc_type,
			kp.material AS formula, COALESCE(p.doi,'') AS doi,
			kp.paper_id AS paper_id
		FROM key_properties kp JOIN papers p ON kp.paper_id = p.id
			WHERE kp.name = 'critical_temperature' AND kp.value_max IS NOT NULL
			AND p.year IS NOT NULL AND kp.is_primary = true
			AND p.review_status = 'approved'
	`).Scan(&rows)

	result = make([]gin.H, 0, len(rows))
	for _, r := range rows {
		t := r.Type
		if t == "" {
			t = "theoretical"
		}
		item := gin.H{
			"x": r.Year, "y": r.Tc, "type": t,
			"sc_type": r.SCType, "formula": r.Material, "doi": r.DOI,
		}
		if r.PaperID > 0 {
			item["paper_id"] = r.PaperID
		}
		result = append(result, item)
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
	if len(body.PaperIDs) == 0 || !isValidReviewStatus(body.Status) {
		c.JSON(http.StatusBadRequest, gin.H{"error": "论文列表为空或审核状态无效"})
		return
	}
	email, exists := c.Get("user_email")
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "未登录"})
		return
	}
	var user models.User
	if err := database.DB.Where("email = ?", email).First(&user).Error; err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "用户不存在"})
		return
	}

	uniqueIDs := make(map[uint]struct{}, len(body.PaperIDs))
	for _, id := range body.PaperIDs {
		uniqueIDs[id] = struct{}{}
	}
	var papers []models.Paper
	if err := database.DB.Where("id IN ?", body.PaperIDs).Find(&papers).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "读取论文失败"})
		return
	}
	if len(papers) != len(uniqueIDs) {
		c.JSON(http.StatusNotFound, gin.H{"error": "部分论文不存在"})
		return
	}
	for _, paper := range papers {
		if paper.UploadedBy != nil && *paper.UploadedBy == user.ID {
			c.JSON(http.StatusForbidden, gin.H{"error": "不能审核自己提交的论文"})
			return
		}
	}

	now := time.Now()
	if err := database.DB.Model(&models.Paper{}).Where("id IN ?", body.PaperIDs).Updates(map[string]interface{}{
		"review_status":       body.Status,
		"reviewed_by_user_id": user.ID,
		"reviewed_at":         now,
	}).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "批量审核失败"})
		return
	}
	cache.FlushPattern("chart:*")
	cache.FlushPattern("search:*")
	failedIDs := make([]uint, 0)
	authorization := c.GetHeader("Authorization")
	for _, id := range body.PaperIDs {
		if err := finalizeReviewArtifacts(body.Status, fmt.Sprint(id), authorization); err != nil {
			log.Printf("批量审核已保存，但 paper_id=%d 后处理失败: %v", id, err)
			failedIDs = append(failedIDs, id)
		}
	}
	if len(failedIDs) > 0 {
		c.JSON(http.StatusBadGateway, gin.H{
			"error":            "批量审核已保存，但部分论文发布或清理失败，请重新审核以重试",
			"failed_paper_ids": failedIDs,
		})
		return
	}
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
