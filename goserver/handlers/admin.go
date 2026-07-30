package handlers

import (
	"fmt"
	"net/http"
	"strconv"

	"scwiki/server/database"
	"scwiki/server/middleware"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
	"golang.org/x/crypto/bcrypt"
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

// UpdatePaper 编辑论文（含 key_properties 增删改）
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

	// 更新论文级字段
	allowed := []string{"doi", "title", "authors", "journal", "volume", "pages",
		"year", "abstract", "review_comment", "review_status",
		"summary", "paper_type", "keywords_tags", "source_file_path",
		"methodology", "key_finding", "rationale"}
	updates := make(map[string]interface{})
	for _, k := range allowed {
		if v, ok := body[k]; ok {
			updates[k] = v
		}
	}
	database.DB.Model(&paper).Updates(updates)

	// 处理 key_properties 增删改
	kpsRaw, ok := body["key_properties"]
	if ok {
		if kps, isArray := kpsRaw.([]interface{}); isArray {
			kpFields := []string{"material", "name", "name_raw", "name_note",
				"value_min", "value_max", "value_raw", "unit",
				"pressure_gpa", "temperature_k", "is_primary",
				"superconductor_type", "article_type", "condition_note",
				"structure_text", "structure_format"}

			// 收集提交中的 KP ID 列表（排除新增和标记删除的）
			keepIds := make(map[uint]bool)

			for _, kpRaw := range kps {
				kpMap, isMap := kpRaw.(map[string]interface{})
				if !isMap {
					continue
				}

				// 处理删除标记
				if deleted, _ := kpMap["_deleted"].(bool); deleted {
					if kpId, ok := getFloatAsUint(kpMap["id"]); ok && kpId > 0 {
						database.DB.Where("id = ? AND paper_id = ?", kpId, paper.ID).
							Delete(&models.KeyProperty{})
					}
					continue
				}

				kpId, hasId := getFloatAsUint(kpMap["id"])

				// ── 审查验证 ──────────────────────────────
				material, _ := kpMap["material"].(string)
				name, _ := kpMap["name"].(string)
				if material == "" {
					c.JSON(http.StatusBadRequest, gin.H{"error": "物性 material 不能为空"})
					return
				}
				if name == "" {
					c.JSON(http.StatusBadRequest, gin.H{"error": "物性 name 不能为空"})
					return
				}
				// 数值范围校验：value_min <= value_max
				vmin, hasMin := kpMap["value_min"].(float64)
				vmax, hasMax := kpMap["value_max"].(float64)
				if hasMin && hasMax && vmin > vmax {
					c.JSON(http.StatusBadRequest, gin.H{
						"error": fmt.Sprintf("物性 %s: value_min(%.4f) 不能大于 value_max(%.4f)", material, vmin, vmax),
					})
					return
				}
				// 压强/温度非负校验
				if pg, ok := kpMap["pressure_gpa"].(float64); ok && pg < 0 {
					c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("物性 %s: pressure_gpa 不能为负", material)})
					return
				}
				if tk, ok := kpMap["temperature_k"].(float64); ok && tk < 0 {
					c.JSON(http.StatusBadRequest, gin.H{"error": fmt.Sprintf("物性 %s: temperature_k 不能为负", material)})
					return
				}
				// ──────────────────────────────────────────

				if hasId && kpId > 0 {
					// 更新已有 KP
					keepIds[kpId] = true
					var kp models.KeyProperty
					if err := database.DB.Where("id = ? AND paper_id = ?", kpId, paper.ID).First(&kp).Error; err == nil {
						kpUpdates := make(map[string]interface{})
						for _, f := range kpFields {
							if v, exists := kpMap[f]; exists {
								kpUpdates[f] = v
							}
						}
						if isPrimary, exists := kpMap["is_primary"]; exists {
							if b, ok := isPrimary.(bool); ok {
								kpUpdates["is_primary"] = b
							}
						}
						database.DB.Model(&kp).Updates(kpUpdates)
					}
				} else {
					// 新增 KP
					newKp := models.KeyProperty{
						PaperID: paper.ID,
					}
					if v, ok := kpMap["material"].(string); ok {
						newKp.Material = v
					}
					if v, ok := kpMap["name"].(string); ok {
						newKp.Name = v
					}
					if v, ok := kpMap["name_raw"].(string); ok {
						newKp.NameRaw = v
					}
					if v, ok := kpMap["name_note"].(string); ok {
						newKp.NameNote = &v
					}
					if v, ok := kpMap["value_min"].(float64); ok {
						newKp.ValueMin = &v
					}
					if v, ok := kpMap["value_max"].(float64); ok {
						newKp.ValueMax = &v
					}
					if v, ok := kpMap["value_raw"].(string); ok {
						newKp.ValueRaw = &v
					}
					if v, ok := kpMap["unit"].(string); ok {
						newKp.Unit = &v
					}
					if v, ok := kpMap["pressure_gpa"].(float64); ok {
						newKp.PressureGpa = &v
					}
					if v, ok := kpMap["temperature_k"].(float64); ok {
						newKp.TemperatureK = &v
					}
					if v, ok := kpMap["condition_note"].(string); ok {
						newKp.ConditionNote = &v
					}
					if v, ok := kpMap["superconductor_type"].(string); ok {
						newKp.SuperconductorType = &v
					}
					if v, ok := kpMap["article_type"].(string); ok {
						newKp.ArticleType = &v
					}
					if v, ok := kpMap["is_primary"].(bool); ok {
						newKp.IsPrimary = v
					}
					if v, ok := kpMap["structure_text"].(string); ok {
						newKp.StructureText = &v
					}
					if v, ok := kpMap["structure_format"].(string); ok {
						newKp.StructureFormat = &v
					}
					newKp.SourceLabel = "manual"
					database.DB.Create(&newKp)
				}
			}
		}
	}

	// 重新加载 paper（含更新后的 key_properties）
	database.DB.Preload("KeyProperties").First(&paper, id)
	c.JSON(http.StatusOK, gin.H{"message": "已更新", "paper": paper})
}

// getFloatAsUint 将 JSON number (float64) 安全转为 uint
func getFloatAsUint(v interface{}) (uint, bool) {
	switch n := v.(type) {
	case float64:
		return uint(n), true
	case int:
		return uint(n), true
	case int64:
		return uint(n), true
	}
	return 0, false
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
// 我的上传
// ═══════════════════════════════════════════════

// GetMyUploads 当前用户的上传记录
// GET /api/papers/my-uploads?limit=20&offset=0
func GetMyUploads(c *gin.Context) {
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "50"))
	offset, _ := strconv.Atoi(c.DefaultQuery("offset", "0"))

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

	var total int64
	query := database.DB.Model(&models.Paper{}).Where("uploaded_by_user_id = ?", user.ID)
	query.Count(&total)

	var papers []models.Paper
	query.Preload("KeyProperties").
		Order("created_at DESC").
		Limit(limit).Offset(offset).
		Find(&papers)

	c.JSON(http.StatusOK, gin.H{
		"items":     papers,
		"total":     total,
		"page_size": limit,
	})
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

// DeleteUser 删除用户
// DELETE /api/admin/users/:id
func DeleteUser(c *gin.Context) {
	id, _ := strconv.Atoi(c.Param("id"))
	database.DB.Delete(&models.User{}, uint(id))
	c.JSON(http.StatusOK, gin.H{"message": "已删除"})
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

	// 验证密码（bcrypt）
	if user.PasswordHash == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "账号未设置密码，请通过注册流程创建"})
		return
	}
	if err := bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(body.Password)); err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "邮箱或密码错误"})
		return
	}

	// 检查审批状态
	if !user.IsApproved {
		c.JSON(http.StatusForbidden, gin.H{"error": "账号尚未通过审批"})
		return
	}

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

// Register 注册
// POST /api/auth/register
func Register(c *gin.Context) {
	var body struct {
		Email    string `json:"email"`
		Password string `json:"password"`
		RealName string `json:"real_name"`
		IsAdmin  bool   `json:"is_admin"`
	}
	if err := c.ShouldBindJSON(&body); err != nil || body.Email == "" || body.Password == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "邮箱和密码不能为空"})
		return
	}

	var existing models.User
	if database.DB.Where("email = ?", body.Email).First(&existing).Error == nil {
		c.JSON(http.StatusConflict, gin.H{"error": "该邮箱已注册"})
		return
	}

	hash, err := bcrypt.GenerateFromPassword([]byte(body.Password), bcrypt.DefaultCost)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "密码加密失败"})
		return
	}

	role := "user"
	if body.IsAdmin {
		role = "admin"
	}

	user := models.User{
		Email:        body.Email,
		PasswordHash: string(hash),
		RealName:     body.RealName,
		Role:         role,
		IsApproved:   false,
	}
	database.DB.Create(&user)

	c.JSON(http.StatusOK, gin.H{
		"message": "注册成功，等待管理员审核",
		"user": gin.H{
			"id":       user.ID,
			"email":    user.Email,
			"real_name": user.RealName,
			"role":     user.Role,
		},
	})
}
