package handlers

import (
	"net/http"
	"strconv"

	"scwiki/server/database"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
)

// ListNews 快讯列表
// GET /api/news
func ListNews(c *gin.Context) {
	items := make([]models.NewsItem, 0)

	result := database.DB.Order("event_date DESC").Find(&items)
	if result.Error != nil {
		c.JSON(http.StatusOK, items)
		return
	}
	c.JSON(http.StatusOK, items)
}

// CreateNews 创建快讯
// POST /api/admin/news
func CreateNews(c *gin.Context) {
	var body models.NewsItem
	if err := c.ShouldBindJSON(&body); err != nil || body.Title == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "标题不能为空"})
		return
	}
	database.DB.Create(&body)
	c.JSON(http.StatusOK, body)
}

// UpdateNews 更新快讯
// PUT /api/admin/news/:id
func UpdateNews(c *gin.Context) {
	id, _ := strconv.Atoi(c.Param("id"))
	var body models.NewsItem
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "参数错误"})
		return
	}
	database.DB.Model(&models.NewsItem{}).Where("id = ?", id).Updates(map[string]any{
		"event_date": body.EventDate,
		"title":      body.Title,
		"summary":    body.Summary,
		"link":       body.Link,
	})
	c.JSON(http.StatusOK, gin.H{"message": "已更新"})
}

// DeleteNews 删除快讯
// DELETE /api/admin/news/:id
func DeleteNews(c *gin.Context) {
	id, _ := strconv.Atoi(c.Param("id"))
	database.DB.Delete(&models.NewsItem{}, uint(id))
	c.JSON(http.StatusOK, gin.H{"message": "已删除"})
}
