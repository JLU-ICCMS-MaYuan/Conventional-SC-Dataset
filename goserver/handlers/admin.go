package handlers

import (
	"net/http"
	"strconv"

	"scwiki/server/database"
	"scwiki/server/middleware"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
)

// ═══════════════════════════════════════════════
// 论文管理
// ═══════════════════════════════════════════════

// GetPapers 论文列表 + 筛选
// GET /api/admin/papers/all?limit=20&offset=0&review_status=pending&keyword=xxx&year_min=2020
func GetPapers(c *gin.Context) {
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "20"))
	offset, _ := strconv.Atoi(c.DefaultQuery("offset", "0"))
	status := c.Query("review_status")
	keyword := c.Query("keyword")
	material := c.Query("material")
	yearMin := c.Query("year_min")
	yearMax := c.Query("year_max")

	// GORM 链式查询 —— 类似 SQLAlchemy query
	query := database.DB.Model(&models.Paper{})

	if status != "" {
		query = query.Where("review_status = ?", status)
	}
	if keyword != "" {
		like := "%" + keyword + "%"
		query = query.Where("title LIKE ? OR doi LIKE ? OR journal LIKE ?", like, like, like)
	}
	if material != "" {
		like := "%" + material + "%"
		// 子查询：找出有这个 material 的 paper_id
		query = query.Where("id IN (SELECT paper_id FROM key_properties WHERE material LIKE ?)", like)
	}
	if yearMin != "" {
		query = query.Where("year >= ?", yearMin)
	}
	if yearMax != "" {
		query = query.Where("year <= ?", yearMax)
	}

	var total int64
	query.Count(&total)

	var papers []models.Paper
	query.Preload("KeyProperties"). // 预加载关联，类似 joinedload
					Order("created_at DESC").
					Limit(limit).Offset(offset).
					Find(&papers) // &papers = 传指针，GORM 往里面填数据

	c.JSON(http.StatusOK, gin.H{
		"items":     papers,
		"total":     total,
		"page_size": limit,
	})
}

// GetPaperDetail 论文详情 + key_properties
// GET /api/admin/papers/:id
func GetPaperDetail(c *gin.Context) {
	id := c.Param("id")
	var paper models.Paper
	// First = SELECT ... LIMIT 1
	if err := database.DB.Preload("KeyProperties").First(&paper, id).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "论文不存在"})
		return
	}
	c.JSON(http.StatusOK, paper)
}

// UpdatePaper 编辑论文
// PUT /api/admin/papers/:id
func UpdatePaper(c *gin.Context) {
	id := c.Param("id")
	var body map[string]interface{}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "JSON 格式错误"})
		return
	}

	var paper models.Paper
	if err := database.DB.First(&paper, id).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "论文不存在"})
		return
	}

	// 只更新允许的字段
	allowed := []string{"doi", "title", "authors", "journal", "volume", "pages",
		"year", "abstract", "review_comment", "review_status",
		"summary", "paper_type", "keywords_tags", "source_file_path",
		"methodology", "key_finding", "rationale"}
	updates := make(map[string]interface{})
	for _, k := range allowed {
		if v, ok := body[k]; ok { // ok = key 存在
			updates[k] = v
		}
	}

	database.DB.Model(&paper).Updates(updates)
	c.JSON(http.StatusOK, gin.H{"message": "已更新", "paper": paper})
}

// ReviewPaper 审核论文
// POST /api/admin/papers/:id/review
func ReviewPaper(c *gin.Context) {
	id := c.Param("id")
	var body struct {
		Status  string `json:"status"`
		Comment string `json:"comment"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "参数错误"})
		return
	}

	var paper models.Paper
	if err := database.DB.First(&paper, id).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "论文不存在"})
		return
	}

	// 获取当前用户 email（从 JWT 中间件存入）
	email, _ := c.Get("user_email")
	// 查用户 ID
	var user models.User
	database.DB.Where("email = ?", email).First(&user)

	database.DB.Model(&paper).Updates(map[string]interface{}{
		"review_status":        body.Status,
		"review_comment":       body.Comment,
		"reviewed_by_user_id":  user.ID,
	})

	c.JSON(http.StatusOK, gin.H{"message": "审核完成", "paper": paper})
}

// DeletePaper 删除论文
// DELETE /api/admin/papers/:id
func DeletePaper(c *gin.Context) {
	id := c.Param("id")
	// 先删 key_properties
	database.DB.Where("paper_id = ?", id).Delete(&models.KeyProperty{})
	database.DB.Delete(&models.Paper{}, id)
	c.JSON(http.StatusOK, gin.H{"message": "已删除"})
}

// ═══════════════════════════════════════════════
// 用户管理
// ═══════════════════════════════════════════════

// GetUsers 用户列表
// GET /api/admin/users
func GetUsers(c *gin.Context) {
	var users []models.User
	database.DB.Find(&users)
	c.JSON(http.StatusOK, users)
}

// UpdateUser 编辑用户权限
// PUT /api/admin/users/:id
func UpdateUser(c *gin.Context) {
	id := c.Param("id")
	var body struct {
		Role       string `json:"role"`
		IsApproved bool   `json:"is_approved"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "参数错误"})
		return
	}

	var user models.User
	if err := database.DB.First(&user, id).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "用户不存在"})
		return
	}

	database.DB.Model(&user).Updates(map[string]interface{}{
		"role":        body.Role,
		"is_approved": body.IsApproved,
	})
	c.JSON(http.StatusOK, gin.H{"message": "已更新", "user": user})
}

// ═══════════════════════════════════════════════
// 仪表盘统计
// ═══════════════════════════════════════════════

// GetStats 概览统计
// GET /api/admin/stats
func GetStats(c *gin.Context) {
	var userCount, paperCount, pendingCount int64
	database.DB.Model(&models.User{}).Count(&userCount)
	database.DB.Model(&models.Paper{}).Count(&paperCount)
	database.DB.Model(&models.User{}).Where("is_approved = ?", false).Count(&pendingCount)

	c.JSON(http.StatusOK, gin.H{
		"users":   userCount,
		"papers":  paperCount,
		"pending": pendingCount,
	})
}

// ═══════════════════════════════════════════════
// 登录
// ═══════════════════════════════════════════════

// Login 登录
// POST /api/auth/login
func Login(c *gin.Context) {
	var body struct {
		Email    string `json:"email"`
		Password string `json:"password"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "参数错误"})
		return
	}

	var user models.User
	if err := database.DB.Where("email = ?", body.Email).First(&user).Error; err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "邮箱或密码错误"})
		return
	}

	// TODO: 验证密码（bcrypt）
	token, err := middleware.GenerateToken(user.Email)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "生成 token 失败"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"access_token": token,
		"token_type":   "bearer",
		"user": gin.H{
			"id":            user.ID,
			"email":         user.Email,
			"real_name":     user.RealName,
			"role":          user.Role,
			"is_admin":      user.Role == "admin" || user.Role == "superadmin",
			"is_superadmin": user.Role == "superadmin",
			"is_approved":   user.IsApproved,
		},
	})
}
