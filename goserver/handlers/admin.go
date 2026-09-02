package handlers

import (
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"math"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"scwiki/server/cache"
	"scwiki/server/database"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
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
		"summary", "paper_type", "theoretical_subtype", "keywords_tags",
		"superconductor_kind",
		"methodology", "key_finding", "research_motivation", "research_materials",
		"material_relations", "builds_on", "knowledge_graph_title",
	}
	// 请求字段 → superconductor_properties 真实列。
	// Updates(map) 直接把键当列名，因此这里必须用数据库列名（material_raw / unit_raw）。
	// 压强、温度等条件字段属材料状态，不经物性接口修改；名称由 name_raw 承载。
	keyPropertyUpdateFields = map[string]string{
		"material":       "material_raw",
		"name_raw":       "name_raw",
		"value_min":      "value_min",
		"value_max":      "value_max",
		"value_raw":      "value_raw",
		"value_number":   "value_number",
		"unit":           "unit_raw",
		"canonical_unit": "canonical_unit",
		"condition_note": "condition_note",
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
		// 子查询：找出含该材料的 paper_id。化学式在 superconductors，
		// 原文材料名在 superconductor_properties.material_raw；key_properties 表已不存在。
		query = query.Where(`id IN (
			SELECT ms.paper_id FROM material_states ms
			JOIN superconductors sc ON sc.id = ms.superconductor_id
			WHERE sc.chemical_formula LIKE ?
			UNION
			SELECT sp.paper_id FROM superconductor_properties sp WHERE sp.material_raw LIKE ?
		)`, like, like)
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
	// 材料状态下的 Tc、物性与结构必须预加载，否则编辑页只能看到空数组
	// （GORM 未预加载的关联序列化为空，且接口返回 200 无错误信号）。
	if err := database.DB.
		Preload("KeyProperties").
		Preload("MaterialFamilyLinks.MaterialFamily").
		Preload("MaterialStates.Superconductor").
		Preload("MaterialStates.StructureFamilyLinks.StructureFamily").
		Preload("MaterialStates.TcResults").
		Preload("MaterialStates.Properties").
		Preload("MaterialStates.Structures").
		First(&paper, id).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "论文不存在"})
		return
	}
	paper.MaterialFamilies = materialFamiliesFromLinks(paper.MaterialFamilyLinks)
	c.JSON(http.StatusOK, paper)
}

// paperUpdatesFromBody 从请求体提取白名单字段，供 UpdatePaper 使用。
// 白名单之外（如 review_status）不得进入更新集，审核状态只能通过 ReviewPaper 修改。
func paperUpdatesFromBody(body map[string]interface{}) map[string]interface{} {
	updates := make(map[string]interface{})
	for _, k := range paperUpdateFields {
		if v, ok := body[k]; ok {
			updates[k] = v
		}
	}
	return updates
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
	updates := paperUpdatesFromBody(body)
	if value, exists := updates["superconductor_kind"]; exists {
		kind, ok := value.(string)
		if !ok || !validSuperconductorKind(kind) {
			c.JSON(http.StatusBadRequest, gin.H{"error": "superconductor_kind 无效"})
			return
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
			for field, column := range keyPropertyUpdateFields {
				if value, exists := values[field]; exists {
					kpUpdates[column] = value
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

// newKeyProperty 只接受 superconductor_properties 的真实列。
// 无对应列的字段（压强、温度、主次标记、结构文本等）一律不接受，而非接受后静默丢弃——
// 后者会让管理员以为改动已保存。
func newKeyProperty(paperID uint, values map[string]interface{}) models.KeyProperty {
	kp := models.KeyProperty{PaperID: paperID}
	kp.Material, _ = values["material"].(string)
	kp.NameRaw, _ = values["name_raw"].(string)
	assignFloatPointer(values, "value_min", &kp.ValueMin)
	assignFloatPointer(values, "value_max", &kp.ValueMax)
	assignFloatPointer(values, "value_number", &kp.ValueNumber)
	assignStringPointer(values, "value_raw", &kp.ValueRaw)
	assignStringPointer(values, "unit", &kp.Unit)
	assignStringPointer(values, "canonical_unit", &kp.CanonicalUnit)
	assignStringPointer(values, "condition_note", &kp.ConditionNote)
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
func applyPaperReview(tx *gorm.DB, paper *models.Paper, reviewerID uint, status, comment, requestID, source string, reviewedAt time.Time, classificationSnapshot json.RawMessage) (bool, error) {
	if requestID != "" {
		var count int64
		if err := tx.Model(&models.PaperReviewEvent{}).Where("request_id = ?", requestID).Count(&count).Error; err != nil {
			return false, err
		}
		if count > 0 {
			return false, nil
		}
	}
	revision := paper.ContentRevision
	if revision == 0 {
		revision = 1
	}
	var approvedRevision interface{}
	if status == reviewStatusApproved {
		approvedRevision = revision
	}
	if err := tx.Model(paper).Updates(map[string]interface{}{
		"approved_revision": approvedRevision,
		"review_status":     status, "review_comment": comment,
		"reviewed_by_user_id": reviewerID, "reviewed_at": reviewedAt,
	}).Error; err != nil {
		return false, err
	}
	var requestIDPtr *string
	if requestID != "" {
		requestIDPtr = &requestID
	}
	commentCopy := comment
	event := models.PaperReviewEvent{
		PaperID: paper.ID, PaperRevision: revision,
		ReviewerUserID: reviewerID, Status: status,
		ReviewComment: &commentCopy, ReviewedAt: reviewedAt,
		RequestID: requestIDPtr, Source: source,
		ClassificationSnapshot: classificationSnapshot,
	}
	if err := tx.Create(&event).Error; err != nil {
		return false, err
	}
	paper.ReviewStatus = status
	paper.ReviewComment = &commentCopy
	paper.ReviewedBy = &reviewerID
	paper.ReviewedAt = &reviewedAt
	if status == reviewStatusApproved {
		paper.ApprovedRevision = &revision
	} else {
		paper.ApprovedRevision = nil
	}
	return true, nil
}

func ReviewPaper(c *gin.Context) {
	id := c.Param("id")
	var body struct {
		Status                string                         `json:"status"`
		Comment               string                         `json:"comment"`
		ReviewRequestID       string                         `json:"review_request_id"`
		AdminInternalNote     *string                        `json:"admin_internal_note"`
		SuperconductorKind    string                         `json:"superconductor_kind"`
		MaterialFamilies      []classificationSelection      `json:"material_families"`
		MaterialStates        []materialClassificationUpdate `json:"material_states"`
		ClassificationContext json.RawMessage                `json:"classification_context"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		if errors.Is(err, errLegacyClassificationContract) {
			c.JSON(http.StatusBadRequest, gin.H{"code": "legacy_classification_contract", "error": "superconductor_kind 必须设置在论文级"})
			return
		}
		c.JSON(http.StatusBadRequest, gin.H{"error": "参数错误"})
		return
	}
	if !isValidReviewStatus(body.Status) {
		c.JSON(http.StatusBadRequest, gin.H{"error": "无效的审核状态"})
		return
	}
	if len(body.ReviewRequestID) > 64 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "review_request_id 过长"})
		return
	}
	if len(body.ClassificationContext) > 256*1024 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "classification_context 过大"})
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
	if err := database.DB.Transaction(func(tx *gorm.DB) error {
		if err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).First(&paper, paper.ID).Error; err != nil {
			return err
		}
		if body.ReviewRequestID != "" {
			var count int64
			if err := tx.Model(&models.PaperReviewEvent{}).
				Where("request_id = ?", body.ReviewRequestID).Count(&count).Error; err != nil {
				return err
			}
			if count > 0 {
				return nil
			}
		}
		var classificationSnapshot json.RawMessage
		if body.Status == reviewStatusApproved {
			snapshot, err := applyPaperClassifications(
				tx, &paper, user.ID, body.SuperconductorKind, body.MaterialFamilies, body.MaterialStates,
			)
			if err != nil {
				return err
			}
			if err := validatePaperClassificationComplete(tx, &paper); err != nil {
				return err
			}
			context := body.ClassificationContext
			if len(context) == 0 {
				context = json.RawMessage(`{}`)
			}
			classificationSnapshot, err = json.Marshal(struct {
				Context             json.RawMessage               `json:"context"`
				SuperconductorKind string                        `json:"superconductor_kind"`
				MaterialFamilies    []classificationSnapshotTerm  `json:"material_families"`
				MaterialStates      []classificationSnapshotState `json:"material_states"`
			}{
				Context:             context,
				SuperconductorKind: snapshot.SuperconductorKind,
				MaterialFamilies:    snapshot.MaterialFamilies,
				MaterialStates:      snapshot.MaterialStates,
			})
			if err != nil {
				return err
			}
		}
		_, err := applyPaperReview(tx, &paper, user.ID, body.Status, body.Comment, body.ReviewRequestID, "single", now, classificationSnapshot)
		if err != nil {
			return err
		}
		if body.AdminInternalNote != nil {
			return tx.Model(&paper).Update("admin_internal_note", *body.AdminInternalNote).Error
		}
		return nil
	}); err != nil {
		var incomplete *classificationIncompleteError
		if errors.As(err, &incomplete) {
			c.JSON(http.StatusConflict, gin.H{
				"code":               "classification_incomplete",
				"error":              "材料分类尚未完成，不能批准论文",
				"material_state_ids": incomplete.MaterialStateIDs,
			})
			return
		}
		if errors.Is(err, errClassificationInvalid) {
			c.JSON(http.StatusBadRequest, gin.H{"code": "classification_invalid", "error": "材料分类选择无效"})
			return
		}
		if errors.Is(err, errClassificationNotFound) || errors.Is(err, gorm.ErrRecordNotFound) {
			c.JSON(http.StatusNotFound, gin.H{"code": "classification_not_found", "error": "论文当前版本、材料状态或目录项不存在"})
			return
		}
		if errors.Is(err, errClassificationNameConflict) {
			c.JSON(http.StatusConflict, gin.H{"code": "classification_name_conflict", "error": "分类名称与现有目录冲突"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "审核操作失败"})
		return
	}
	if err := database.DB.First(&paper, id).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "审核已保存，但读取结果失败"})
		return
	}

	cache.FlushPattern("chart:*")
	cache.FlushPattern("search:*")
	cache.FlushPattern("community:contributions:*")
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

type classificationIncompleteError struct {
	MaterialStateIDs []uint64
}

func (err *classificationIncompleteError) Error() string {
	return "材料分类尚未完成"
}

func validatePaperClassificationComplete(tx *gorm.DB, paper *models.Paper) error {
	revision := paper.ContentRevision
	if revision == 0 {
		revision = 1
	}
	var states []models.MaterialState
	if err := tx.Where("paper_id = ? AND paper_revision = ?", paper.ID, revision).Find(&states).Error; err != nil {
		return err
	}
	if len(states) == 0 && paper.PaperType != nil && *paper.PaperType != "review" {
		return &classificationIncompleteError{MaterialStateIDs: []uint64{}}
	}
	var familyCount int64
	if err := tx.Model(&models.PaperMaterialFamily{}).
		Where("paper_id = ? AND paper_revision = ?", paper.ID, revision).
		Count(&familyCount).Error; err != nil {
		return err
	}
	if familyCount == 0 {
		return &classificationIncompleteError{MaterialStateIDs: []uint64{}}
	}
	missing := make([]uint64, 0)
	for _, state := range states {
		if state.ElementCount == nil || *state.ElementCount < 1 || *state.ElementCount > 118 {
			missing = append(missing, state.ID)
		}
	}
	if len(missing) > 0 {
		return &classificationIncompleteError{MaterialStateIDs: missing}
	}
	return nil
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
	idStr := c.Param("id")
	id64, err := strconv.ParseUint(idStr, 10, 32)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "无效的论文 ID"})
		return
	}
	paperID := uint(id64)

	authToken := c.GetHeader("Authorization")
	if err := CascadeDeletePaper(paperID, authToken); err != nil {
		if errors.Is(err, ErrPaperNotFound) {
			c.JSON(http.StatusNotFound, gin.H{"error": "论文不存在"})
			return
		}
		log.Printf("删除论文 %d 失败: %v", paperID, err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "删除失败，请重试"})
		return
	}

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
	c.JSON(http.StatusMethodNotAllowed, gin.H{
		"error": "通用权限更新接口已停用，请使用需要原因和审计的治理动作",
		"code":  "governance_action_required",
	})
}

// DeleteUser 删除用户
// DELETE /api/admin/users/:id
func DeleteUser(c *gin.Context) {
	c.JSON(http.StatusMethodNotAllowed, gin.H{
		"error": "物理删除已停用，请使用可审计的账号注销操作",
		"code":  "account_deactivation_required",
	})
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
	loginHandler(c)
}

// Register 注册
// POST /api/auth/register
func Register(c *gin.Context) {
	registerHandler(c)
}
