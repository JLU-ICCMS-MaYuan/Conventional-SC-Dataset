package handlers

import (
	"errors"
	"fmt"
	"math"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"scwiki/server/cache"
	"scwiki/server/database"
	"scwiki/server/middleware"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
	"golang.org/x/crypto/bcrypt"
	"gorm.io/gorm"
)

const (
	reviewStatusPending  = "pending"
	reviewStatusApproved = "approved"
	reviewStatusRejected = "rejected"
)

var (
	validReviewStatuses = map[string]struct{}{
		reviewStatusPending: {}, reviewStatusApproved: {}, reviewStatusRejected: {},
	}
	paperUpdateFields = []string{
		"doi", "title", "authors", "journal", "volume", "pages", "year", "abstract",
		"summary", "paper_type", "theoretical_subtype", "keywords_tags", "source_file_path",
		"methodology", "key_finding", "rationale", "research_materials", "referenced_materials",
		"material_relations", "builds_on",
	}
	keyPropertyUpdateFields = []string{
		"material", "name", "name_raw", "name_note", "value_min", "value_max", "value_raw", "unit",
		"pressure_gpa", "temperature_k", "is_primary", "superconductor_type", "article_type",
		"condition_json", "condition_note", "structure_text", "structure_format",
	}
	errKeyPropertyNotFound = errors.New("物性记录不存在或不属于当前论文")
	pythonBackendClient    = &http.Client{Timeout: 2 * time.Minute}
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

	kps, err := parseAndValidateKeyProperties(body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// 审核状态只能通过 ReviewPaper 修改，避免普通编辑绕过审核动作。
	updates := make(map[string]interface{})
	for _, k := range paperUpdateFields {
		if v, ok := body[k]; ok {
			updates[k] = v
		}
	}

	var paper models.Paper
	err = database.DB.Transaction(func(tx *gorm.DB) error {
		if err := tx.First(&paper, id).Error; err != nil {
			return err
		}
		if len(updates) > 0 {
			if err := tx.Model(&paper).Updates(updates).Error; err != nil {
				return err
			}
		}
		return updateKeyProperties(tx, paper.ID, kps)
	})
	if errors.Is(err, gorm.ErrRecordNotFound) {
		c.JSON(http.StatusNotFound, gin.H{"error": "论文不存在"})
		return
	}
	if errors.Is(err, errKeyPropertyNotFound) {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "保存论文失败"})
		return
	}

	// 重新加载 paper（含更新后的 key_properties）
	if err := database.DB.Preload("KeyProperties").First(&paper, id).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "论文已保存，但读取结果失败"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "已更新", "paper": paper})
}

func parseAndValidateKeyProperties(body map[string]interface{}) ([]map[string]interface{}, error) {
	raw, exists := body["key_properties"]
	if !exists {
		return nil, nil
	}
	items, ok := raw.([]interface{})
	if !ok {
		return nil, errors.New("key_properties 必须是数组")
	}
	kps := make([]map[string]interface{}, 0, len(items))
	for _, item := range items {
		kp, ok := item.(map[string]interface{})
		if !ok {
			return nil, errors.New("key_properties 包含无效项目")
		}
		if deleted, _ := kp["_deleted"].(bool); deleted {
			if id, ok := getFloatAsUint(kp["id"]); !ok || id == 0 {
				return nil, errors.New("删除物性时必须提供有效 id")
			}
			kps = append(kps, kp)
			continue
		}
		material, _ := kp["material"].(string)
		name, _ := kp["name"].(string)
		if material == "" {
			return nil, errors.New("物性 material 不能为空")
		}
		if name == "" {
			return nil, errors.New("物性 name 不能为空")
		}
		vmin, hasMin := kp["value_min"].(float64)
		vmax, hasMax := kp["value_max"].(float64)
		if hasMin && hasMax && vmin > vmax {
			return nil, fmt.Errorf("物性 %s: value_min(%.4f) 不能大于 value_max(%.4f)", material, vmin, vmax)
		}
		if pg, ok := kp["pressure_gpa"].(float64); ok && pg < 0 {
			return nil, fmt.Errorf("物性 %s: pressure_gpa 不能为负", material)
		}
		if tk, ok := kp["temperature_k"].(float64); ok && tk < 0 {
			return nil, fmt.Errorf("物性 %s: temperature_k 不能为负", material)
		}
		kps = append(kps, kp)
	}
	return kps, nil
}

func updateKeyProperties(tx *gorm.DB, paperID uint, kps []map[string]interface{}) error {
	for _, values := range kps {
		kpID, hasID := getFloatAsUint(values["id"])
		if deleted, _ := values["_deleted"].(bool); deleted {
			result := tx.Where("id = ? AND paper_id = ?", kpID, paperID).Delete(&models.KeyProperty{})
			if result.Error != nil {
				return result.Error
			}
			if result.RowsAffected != 1 {
				return errKeyPropertyNotFound
			}
			continue
		}
		if hasID && kpID > 0 {
			var kp models.KeyProperty
			if err := tx.Where("id = ? AND paper_id = ?", kpID, paperID).First(&kp).Error; err != nil {
				if errors.Is(err, gorm.ErrRecordNotFound) {
					return errKeyPropertyNotFound
				}
				return err
			}
			kpUpdates := make(map[string]interface{})
			for _, field := range keyPropertyUpdateFields {
				if value, exists := values[field]; exists {
					kpUpdates[field] = value
				}
			}
			if len(kpUpdates) > 0 {
				if err := tx.Model(&kp).Updates(kpUpdates).Error; err != nil {
					return err
				}
			}
			continue
		}

		newKP := newKeyProperty(paperID, values)
		if err := tx.Create(&newKP).Error; err != nil {
			return err
		}
	}
	return nil
}

func newKeyProperty(paperID uint, values map[string]interface{}) models.KeyProperty {
	kp := models.KeyProperty{PaperID: paperID, SourceLabel: "manual"}
	kp.Material, _ = values["material"].(string)
	kp.Name, _ = values["name"].(string)
	kp.NameRaw, _ = values["name_raw"].(string)
	assignStringPointer(values, "name_note", &kp.NameNote)
	assignFloatPointer(values, "value_min", &kp.ValueMin)
	assignFloatPointer(values, "value_max", &kp.ValueMax)
	assignStringPointer(values, "value_raw", &kp.ValueRaw)
	assignStringPointer(values, "unit", &kp.Unit)
	assignFloatPointer(values, "pressure_gpa", &kp.PressureGpa)
	assignFloatPointer(values, "temperature_k", &kp.TemperatureK)
	assignStringPointer(values, "condition_json", &kp.ConditionJSON)
	assignStringPointer(values, "condition_note", &kp.ConditionNote)
	assignStringPointer(values, "superconductor_type", &kp.SuperconductorType)
	assignStringPointer(values, "article_type", &kp.ArticleType)
	assignStringPointer(values, "structure_text", &kp.StructureText)
	assignStringPointer(values, "structure_format", &kp.StructureFormat)
	kp.IsPrimary, _ = values["is_primary"].(bool)
	return kp
}

func assignStringPointer(values map[string]interface{}, key string, target **string) {
	if value, ok := values[key].(string); ok {
		*target = &value
	}
}

func assignFloatPointer(values map[string]interface{}, key string, target **float64) {
	if value, ok := values[key].(float64); ok {
		*target = &value
	}
}

// getFloatAsUint 将 JSON number (float64) 安全转为 uint
func getFloatAsUint(v interface{}) (uint, bool) {
	switch n := v.(type) {
	case float64:
		if n < 0 || math.Trunc(n) != n {
			return 0, false
		}
		return uint(n), true
	case int:
		if n < 0 {
			return 0, false
		}
		return uint(n), true
	case int64:
		if n < 0 {
			return 0, false
		}
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
	if !isValidReviewStatus(body.Status) {
		c.JSON(http.StatusBadRequest, gin.H{"error": "无效的审核状态"})
		return
	}

	var paper models.Paper
	if err := database.DB.First(&paper, id).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "论文不存在"})
		return
	}

	// 获取当前用户 email（从 JWT 中间件存入）
	email, exists := c.Get("user_email")
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "未登录"})
		return
	}
	// 查用户 ID
	var user models.User
	if err := database.DB.Where("email = ?", email).First(&user).Error; err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "用户不存在"})
		return
	}
	if paper.UploadedBy != nil && *paper.UploadedBy == user.ID {
		c.JSON(http.StatusForbidden, gin.H{"error": "不能审核自己提交的论文"})
		return
	}

	now := time.Now()
	if err := database.DB.Model(&paper).Updates(map[string]interface{}{
		"review_status":       body.Status,
		"review_comment":      body.Comment,
		"reviewed_by_user_id": user.ID,
		"reviewed_at":         now,
	}).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "审核操作失败"})
		return
	}
	if err := database.DB.First(&paper, id).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "审核已保存，但读取结果失败"})
		return
	}

	cache.FlushPattern("chart:*")
	cache.FlushPattern("search:*")
	if err := finalizeReviewArtifacts(body.Status, id, c.GetHeader("Authorization")); err != nil {
		message := "审核已保存，但临时证据清理失败，请重新审核以重试"
		if body.Status == reviewStatusApproved {
			message = "审核已保存，但向量发布失败，请重新审核以重试"
		}
		c.JSON(http.StatusBadGateway, gin.H{"error": message, "detail": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "审核完成", "paper": paper})
}

func isValidReviewStatus(status string) bool {
	_, ok := validReviewStatuses[status]
	return ok
}

func shouldCleanupReviewArtifact(status string) bool {
	return status == reviewStatusApproved || status == reviewStatusRejected
}

func pythonBackendURL() string {
	baseURL := os.Getenv("PYTHON_BACKEND_URL")
	if baseURL == "" {
		baseURL = "http://127.0.0.1:8000"
	}
	return baseURL
}

func finalizeReviewArtifacts(status, paperID, authorization string) error {
	baseURL := pythonBackendURL()
	if status == reviewStatusApproved {
		if err := publishApprovedPaperAt(baseURL, paperID, authorization); err != nil {
			return err
		}
	}
	if shouldCleanupReviewArtifact(status) {
		return cleanupReviewArtifactAt(baseURL, paperID, authorization)
	}
	return nil
}

func publishApprovedPaperAt(baseURL, paperID, authorization string) error {
	url := strings.TrimRight(baseURL, "/") + "/api/rag/papers/" + paperID + "/publish"
	return callPythonPaperEndpoint(http.MethodPost, url, authorization, false)
}

func cleanupReviewArtifactAt(baseURL, paperID, authorization string) error {
	url := strings.TrimRight(baseURL, "/") + "/api/rag/papers/" + paperID + "/review-artifact"
	return callPythonPaperEndpoint(http.MethodDelete, url, authorization, true)
}

func callPythonPaperEndpoint(method, url, authorization string, missingIsSuccess bool) error {
	req, err := http.NewRequest(method, url, nil)
	if err != nil {
		return err
	}
	if authorization != "" {
		req.Header.Set("Authorization", authorization)
	}
	resp, err := pythonBackendClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if (resp.StatusCode >= 200 && resp.StatusCode < 300) || (missingIsSuccess && resp.StatusCode == http.StatusNotFound) {
		return nil
	}
	return fmt.Errorf("Python 返回 HTTP %d", resp.StatusCode)
}

// DeletePaper 删除论文
// DELETE /api/admin/papers/:id
func DeletePaper(c *gin.Context) {
	id := c.Param("id")
	// 先删 key_properties
	database.DB.Where("paper_id = ?", id).Delete(&models.KeyProperty{})
	database.DB.Delete(&models.Paper{}, id)
	cache.FlushPattern("chart:*")
	cache.FlushPattern("search:*")
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

// GetMyUploadDetail 返回当前用户自己的草稿或待审论文详情。
func GetMyUploadDetail(c *gin.Context) {
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
	var paper models.Paper
	if err := database.DB.Preload("KeyProperties").
		Where("id = ? AND uploaded_by_user_id = ?", c.Param("id"), user.ID).
		First(&paper).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "论文不存在"})
		return
	}
	c.JSON(http.StatusOK, paper)
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
	cache.FlushPattern("chart:*")
	cache.FlushPattern("search:*")
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
			"id":        user.ID,
			"email":     user.Email,
			"real_name": user.RealName,
			"role":      user.Role,
		},
	})
}
