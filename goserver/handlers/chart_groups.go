package handlers

import (
	"net/http"
	"strconv"

	"scwiki/server/database"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
)

// ═══════════════════════════════════════════════
// 图表组合 API（替代 Python /api/chart-groups/*）
// ═══════════════════════════════════════════════

// ListChartGroups 列表（公开+预设+自己的）
// GET /api/chart-groups
func ListChartGroups(c *gin.Context) {
	var groups []models.ChartGroup
	query := database.DB.Preload("Items").Order("updated_at DESC")

	// 简单处理：返回全部公开+预设。认证用户额外看到自己的。
	isPublic := c.Query("is_public")
	isPreset := c.Query("is_preset")
	if isPublic == "true" {
		query = query.Where("is_public = ?", true)
	}
	if isPreset == "true" {
		query = query.Where("is_preset = ?", true)
	}

	query.Find(&groups)
	c.JSON(http.StatusOK, groups)
}

// GetChartGroup 组合详情
// GET /api/chart-groups/:id
func GetChartGroup(c *gin.Context) {
	id, _ := strconv.Atoi(c.Param("id"))
	var group models.ChartGroup
	if err := database.DB.Preload("Items").First(&group, uint(id)).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "组合不存在"})
		return
	}
	c.JSON(http.StatusOK, group)
}

// CreateChartGroup 创建组合
// POST /api/chart-groups
func CreateChartGroup(c *gin.Context) {
	var body struct {
		Name        string `json:"name"`
		Description string `json:"description"`
		IsPublic    bool   `json:"is_public"`
		Items       []struct {
			KeyPropertyID     *uint    `json:"key_property_id"`
			CustomLabel       *string  `json:"custom_label"`
			CustomTc          *float64 `json:"custom_tc"`
			CustomPressure    *float64 `json:"custom_pressure"`
			CustomType        *string  `json:"custom_type"`
			CustomArticleType *string  `json:"custom_article_type"`
			CustomYear        *int     `json:"custom_year"`
		} `json:"items"`
	}
	if err := c.ShouldBindJSON(&body); err != nil || body.Name == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "名称不能为空"})
		return
	}

	group := models.ChartGroup{
		Name:    body.Name,
		IsPublic: body.IsPublic,
	}
	if body.Description != "" {
		group.Description = &body.Description
	}

	email, _ := c.Get("user_email")
	if email != nil {
		var user models.User
		if database.DB.Where("email = ?", email).First(&user).Error == nil {
			group.CreatedBy = &user.ID
		}
	}

	// SortOrder 用数组下标，保持前端传入顺序；与 UpdateChartGroup 一致。
	for i, item := range body.Items {
		it := models.ChartGroupItem{
			SortOrder:         i,
			KeyPropertyID:     item.KeyPropertyID,
			CustomLabel:       item.CustomLabel,
			CustomTc:          item.CustomTc,
			CustomPressure:    item.CustomPressure,
			CustomType:        item.CustomType,
			CustomArticleType: item.CustomArticleType,
			CustomYear:        item.CustomYear,
		}
		group.Items = append(group.Items, it)
	}

	database.DB.Create(&group)
	c.JSON(http.StatusOK, group)
}

// UpdateChartGroup 更新组合
// PUT /api/chart-groups/:id
func UpdateChartGroup(c *gin.Context) {
	id, _ := strconv.Atoi(c.Param("id"))
	var group models.ChartGroup
	if err := database.DB.First(&group, uint(id)).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "组合不存在"})
		return
	}

	var body struct {
		Name        *string `json:"name"`
		Description *string `json:"description"`
		IsPublic    *bool   `json:"is_public"`
		Items       []struct {
			ID                *uint    `json:"id"`
			KeyPropertyID     *uint    `json:"key_property_id"`
			CustomLabel       *string  `json:"custom_label"`
			CustomTc          *float64 `json:"custom_tc"`
			CustomPressure    *float64 `json:"custom_pressure"`
			CustomType        *string  `json:"custom_type"`
			CustomArticleType *string  `json:"custom_article_type"`
			CustomYear        *int     `json:"custom_year"`
		} `json:"items"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "参数错误"})
		return
	}

	updates := map[string]any{}
	if body.Name != nil {
		updates["name"] = *body.Name
	}
	if body.Description != nil {
		updates["description"] = *body.Description
	}
	if body.IsPublic != nil {
		updates["is_public"] = *body.IsPublic
	}
	if len(updates) > 0 {
		database.DB.Model(&group).Updates(updates)
	}

	if body.Items != nil {
		database.DB.Where("group_id = ?", group.ID).Delete(&models.ChartGroupItem{})
		for i, item := range body.Items {
			it := models.ChartGroupItem{
				GroupID:           group.ID,
				SortOrder:         i,
				KeyPropertyID:     item.KeyPropertyID,
				CustomLabel:       item.CustomLabel,
				CustomTc:          item.CustomTc,
				CustomPressure:    item.CustomPressure,
				CustomType:        item.CustomType,
				CustomArticleType: item.CustomArticleType,
				CustomYear:        item.CustomYear,
			}
			database.DB.Create(&it)
		}
	}

	c.JSON(http.StatusOK, gin.H{"message": "已更新"})
}

// DeleteChartGroup 删除组合
// DELETE /api/chart-groups/:id
func DeleteChartGroup(c *gin.Context) {
	id, _ := strconv.Atoi(c.Param("id"))
	database.DB.Where("group_id = ?", id).Delete(&models.ChartGroupItem{})
	database.DB.Delete(&models.ChartGroup{}, uint(id))
	c.JSON(http.StatusOK, gin.H{"message": "已删除"})
}

// TogglePublic 管理员切换公开状态
// PATCH /api/chart-groups/:id/public
func ToggleChartGroupPublic(c *gin.Context) {
	id, _ := strconv.Atoi(c.Param("id"))
	var body struct {
		IsPublic bool `json:"is_public"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "参数错误"})
		return
	}
	database.DB.Model(&models.ChartGroup{}).Where("id = ?", id).Update("is_public", body.IsPublic)
	c.JSON(http.StatusOK, gin.H{"message": "已更新"})
}
