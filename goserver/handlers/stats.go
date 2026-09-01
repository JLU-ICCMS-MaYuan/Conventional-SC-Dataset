package handlers

import (
	"fmt"
	"log"
	"net/http"
	"strings"
	"sync"
	"time"

	"scwiki/server/cache"
	"scwiki/server/database"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

const contributionCacheKey = "community:contributions:v2"

var contributionRefreshMu sync.Mutex
var contributionSnapshotLoader = loadContributionSnapshot

type contributionRow struct {
	UserID            uint      `gorm:"column:user_id"`
	Username          string    `gorm:"column:username"`
	AccountStatus     string    `gorm:"column:account_status"`
	ContributionCount int64     `gorm:"column:contribution_count"`
	ReachedAt         time.Time `gorm:"column:reached_at"`
}

type contributionRank struct {
	Rank              int    `json:"rank"`
	UserID            uint   `json:"user_id"`
	Username          string `json:"username"`
	DisplayName       string `json:"display_name"`
	AvatarText        string `json:"avatar_text"`
	ContributionCount int64  `json:"contribution_count"`
	AccountStatus     string `json:"account_status"`
}

type contributionSnapshot struct {
	ParticipantCount int                `json:"participant_count"`
	UploadRanks      []contributionRank `json:"upload_ranks"`
	ReviewRanks      []contributionRank `json:"review_ranks"`
	GeneratedAt      time.Time          `json:"generated_at"`
}

func avatarText(name string) string {
	name = strings.TrimSpace(name)
	if name == "" {
		return "贡"
	}
	return string([]rune(name)[0])
}

func rankContributionRows(rows []contributionRow) []contributionRank {
	ranks := make([]contributionRank, 0, len(rows))
	for i, row := range rows {
		name := strings.TrimSpace(row.Username)
		if row.AccountStatus == "deactivated" {
			name = "已注销用户"
		}
		if name == "" {
			name = "sc_unknown"
		}
		ranks = append(ranks, contributionRank{
			Rank: i + 1, UserID: row.UserID, Username: name, DisplayName: name,
			AvatarText: avatarText(name), ContributionCount: row.ContributionCount,
			AccountStatus: row.AccountStatus,
		})
	}
	return ranks
}

func loadContributionSnapshot() (contributionSnapshot, error) {
	var uploadRows, reviewRows []contributionRow
	// username 是唯一公开身份；display_name 仅在响应层作为兼容别名。
	if err := database.DB.Raw(`
		SELECT u.id AS user_id, u.username AS username, u.account_status AS account_status,
		       COUNT(p.id) AS contribution_count,
		       MAX(COALESCE(p.reviewed_at, p.updated_at, p.created_at)) AS reached_at
		FROM users u JOIN papers p ON p.uploaded_by_user_id = u.id
		WHERE p.review_status = 'approved'
		GROUP BY u.id, u.username, u.account_status
		ORDER BY contribution_count DESC, reached_at ASC, user_id ASC
	`).Scan(&uploadRows).Error; err != nil {
		return contributionSnapshot{}, err
	}
	if err := database.DB.Raw(`
		SELECT u.id AS user_id, u.username AS username, u.account_status AS account_status,
		       COUNT(e.id) AS contribution_count, MAX(e.reviewed_at) AS reached_at
		FROM users u JOIN paper_review_events e ON e.reviewer_user_id = u.id
		GROUP BY u.id, u.username, u.account_status
		ORDER BY contribution_count DESC, reached_at ASC, user_id ASC
	`).Scan(&reviewRows).Error; err != nil {
		return contributionSnapshot{}, err
	}
	participants := make(map[uint]struct{}, len(uploadRows)+len(reviewRows))
	for _, row := range uploadRows {
		participants[row.UserID] = struct{}{}
	}
	for _, row := range reviewRows {
		participants[row.UserID] = struct{}{}
	}
	return contributionSnapshot{
		ParticipantCount: len(participants), UploadRanks: rankContributionRows(uploadRows),
		ReviewRanks: rankContributionRows(reviewRows), GeneratedAt: time.Now(),
	}, nil
}

func contributionRankForUser(ranks []contributionRank, userID uint) *contributionRank {
	for i := range ranks {
		if ranks[i].UserID == userID {
			item := ranks[i]
			return &item
		}
	}
	return nil
}

func topContributionRanks(ranks []contributionRank, limit int) []contributionRank {
	if len(ranks) <= limit {
		return ranks
	}
	return ranks[:limit]
}

func parseContributionRefresh(value string) (bool, bool) {
	switch value {
	case "", "false":
		return false, true
	case "true":
		return true, true
	default:
		return false, false
	}
}

// CommunityContributions 返回公开 Top 20，并为登录用户附加全量个人排名。
func CommunityContributions(c *gin.Context) {
	refresh, valid := parseContributionRefresh(c.Query("refresh"))
	if !valid {
		c.JSON(http.StatusBadRequest, gin.H{"error": "refresh 必须是 true 或 false"})
		return
	}
	var snapshot contributionSnapshot
	if !refresh && cache.Get(contributionCacheKey, &snapshot) {
		// 命中共享快照。
	} else {
		contributionRefreshMu.Lock()
		defer contributionRefreshMu.Unlock()
		if !refresh && cache.Get(contributionCacheKey, &snapshot) {
			// 等待其他请求重建后复用。
		} else {
			var err error
			snapshot, err = contributionSnapshotLoader()
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "贡献榜单加载失败"})
				return
			}
			cache.Set(contributionCacheKey, snapshot, time.Hour)
		}
	}
	uploadTop := topContributionRanks(snapshot.UploadRanks, 20)
	reviewTop := topContributionRanks(snapshot.ReviewRanks, 20)
	response := gin.H{
		"participant_count":  snapshot.ParticipantCount,
		"upload_leaderboard": uploadTop,
		"review_leaderboard": reviewTop,
		"generated_at":       snapshot.GeneratedAt,
	}
	if email, ok := c.Get("user_email"); ok {
		var user models.User
		if err := database.DB.Where("email = ?", email).First(&user).Error; err != nil {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "用户不存在"})
			return
		}
		response["current_user"] = gin.H{
			"upload": contributionRankForUser(snapshot.UploadRanks, user.ID),
			"review": contributionRankForUser(snapshot.ReviewRanks, user.ID),
		}
	}
	c.JSON(http.StatusOK, response)
}

const defaultTcField = "experimental_tc"

// chartTcColumns 把对外的 tc_field 契约映射到条件化模型的 tc_results.tc_method 取值。
// 旧模型每种 Tc 是 superconductor_records 上的一列，故字段名映射到列名；该表迁移后已删除，
// Tc 现在是 tc_results 的行，方法存在 tc_method 里，所以映射目标从「列」变成「行过滤值」。
// 对外白名单与默认值保持不变，前端偏好无需迁移。
var chartTcColumns = map[string]string{
	"experimental_tc":           "experimental",
	"anisotropic_eliashberg_tc": "anisotropic_eliashberg",
	"isotropic_eliashberg_tc":   "isotropic_eliashberg",
	"allen_dynes_tc":            "allen_dynes",
	"mcmillan_tc":               "mcmillan",
}

// resolveChartTcField 返回 (对外字段名, tc_results.tc_method 取值, 是否合法)。
func resolveChartTcField(value string) (string, string, bool) {
	field := strings.TrimSpace(value)
	if field == "" {
		field = defaultTcField
	}
	method, ok := chartTcColumns[field]
	if !ok {
		return "", "", false
	}
	return field, method, true
}

// 图表点的公共可见性边界：论文审核通过，且数据属于已批准的那一版内容。
// tc_results/material_states 按 (paper_id, paper_revision) 绑定版本，不加版本条件会把
// 审核后又被编辑出的新版本数据混进公共图表。
const chartApprovedJoin = `
	FROM tc_results t
	JOIN material_states ms ON ms.id = t.material_state_id
	JOIN superconductors sc ON sc.id = ms.superconductor_id
	JOIN papers p ON p.id = t.paper_id
		AND p.review_status = 'approved'
		AND t.paper_revision = p.content_revision
	LEFT JOIN material_families mf ON mf.id = ms.material_family_id`

// 只有区间没有单值的 Tc 条目取区间中点，否则这些数据永远上不了图。
const chartTcValueExpr = `CAST(COALESCE(t.tc_value_k, (t.tc_min_k + t.tc_max_k) / 2) AS DOUBLE)`

// 分类维度取材料家族（material_families），支持用户自建家族；
// 未分类的状态归入 family_id = 0 的「其他」。
//
// 注意：这两个字段必须直接声明在各 row 结构体上。GORM 的 Raw().Scan() 走
// 原始列名匹配，不会填充匿名嵌入结构体的字段，嵌入会让家族恒为 NULL。
func chartFamilyID(id *uint) uint {
	if id == nil {
		return 0
	}
	return *id
}

func chartFamilyName(name *string) string {
	if name == nil || *name == "" {
		return "其他"
	}
	return *name
}

func chartCacheKey(chart, field string) string {
	return fmt.Sprintf("chart:approved:%s:%s", chart, field)
}

// ═══════════════════════════════════════════════
// 统计 API（替代 Python papers stats + admin users）
// ═══════════════════════════════════════════════

// TcPressureChart Tc-P 散点图数据
// GET /api/papers/stats/tc-pressure
func TcPressureChart(c *gin.Context) {
	tcField, tcMethod, ok := resolveChartTcField(c.Query("tc_field"))
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "不支持的 Tc 字段"})
		return
	}
	cacheKey := chartCacheKey("tc_pressure", tcField)
	var result []gin.H
	if cache.Get(cacheKey, &result) {
		c.JSON(http.StatusOK, result)
		return
	}

	type row struct {
		Material   string  `gorm:"column:material"`
		Tc         float64 `gorm:"column:y"`
		Pressure   float64 `gorm:"column:x"`
		FamilyID   *uint   `gorm:"column:family_id"`
		FamilyName *string `gorm:"column:family_name"`
		Type       string  `gorm:"column:type"`
		PaperID    uint    `gorm:"column:paper_id"`
		DOI        string  `gorm:"column:doi"`
		Year       int     `gorm:"column:year"`
	}
	var rows []row
	query := fmt.Sprintf(`
		SELECT sc.chemical_formula AS material,
			%s AS y, CAST(ms.pressure_value_gpa AS DOUBLE) AS x,
			ms.material_family_id AS family_id, mf.name_zh AS family_name,
			t.result_kind AS type,
			t.paper_id AS paper_id, COALESCE(p.doi,'') AS doi, COALESCE(p.year,0) AS year
		%s
		WHERE t.tc_method = ?
			AND %s IS NOT NULL
			AND ms.pressure_value_gpa IS NOT NULL
	`, chartTcValueExpr, chartApprovedJoin, chartTcValueExpr)
	if err := database.DB.Raw(query, tcMethod).Scan(&rows).Error; err != nil {
		// 静默返回空数组会把 schema 漂移伪装成「暂无数据」，#30 的旧表查询正是这样
		// 在条件化模型迁移后无声失效的。这里必须让错误浮出来，且不缓存失败结果。
		log.Printf("Tc-Pressure 图表查询失败 (tc_field=%s): %v", tcField, err)
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "图表数据暂不可用"})
		return
	}

	result = make([]gin.H, 0, len(rows))
	for _, r := range rows {
		item := gin.H{
			"formula": r.Material,
			"y":       r.Tc, "x": r.Pressure,
			"family_id": chartFamilyID(r.FamilyID), "family_name": chartFamilyName(r.FamilyName),
			"type": chartResultType(r.Type), "tc_field": tcField,
			"doi": r.DOI, "year": r.Year,
		}
		if r.PaperID > 0 {
			item["paper_id"] = r.PaperID
		}
		result = append(result, item)
	}
	cache.Set(cacheKey, result, 0) // 永久缓存
	c.JSON(http.StatusOK, result)
}

// chartResultType 把 tc_results.result_kind 归一到图表的实验/计算两分。
// 旧实现依据 superconductor_records.article_type='e'，该列已随表删除。
func chartResultType(resultKind string) string {
	if resultKind == "experimental" {
		return "experimental"
	}
	return "theoretical"
}

// TcYearChart Tc-Year 散点图数据
// GET /api/papers/stats/tc-year
func TcYearChart(c *gin.Context) {
	tcField, tcMethod, ok := resolveChartTcField(c.Query("tc_field"))
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "不支持的 Tc 字段"})
		return
	}
	cacheKey := chartCacheKey("tc_year", tcField)
	var result []gin.H
	if cache.Get(cacheKey, &result) {
		c.JSON(http.StatusOK, result)
		return
	}

	type row struct {
		Year       int      `gorm:"column:x"`
		Tc         float64  `gorm:"column:y"`
		Type       string   `gorm:"column:type"`
		FamilyID   *uint    `gorm:"column:family_id"`
		FamilyName *string  `gorm:"column:family_name"`
		Material   string   `gorm:"column:formula"`
		DOI        string   `gorm:"column:doi"`
		PaperID    uint     `gorm:"column:paper_id"`
		Pressure   *float64 `gorm:"column:pressure_gpa"`
	}
	var rows []row
	query := fmt.Sprintf(`
		SELECT p.year AS x, %s AS y,
			t.result_kind AS type,
			ms.material_family_id AS family_id, mf.name_zh AS family_name,
			sc.chemical_formula AS formula, COALESCE(p.doi,'') AS doi,
			t.paper_id AS paper_id, CAST(ms.pressure_value_gpa AS DOUBLE) AS pressure_gpa
		%s
		WHERE t.tc_method = ?
			AND %s IS NOT NULL
			AND p.year IS NOT NULL
	`, chartTcValueExpr, chartApprovedJoin, chartTcValueExpr)
	if err := database.DB.Raw(query, tcMethod).Scan(&rows).Error; err != nil {
		log.Printf("Tc-Year 图表查询失败 (tc_field=%s): %v", tcField, err)
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "图表数据暂不可用"})
		return
	}

	result = make([]gin.H, 0, len(rows))
	for _, r := range rows {
		item := gin.H{
			"x": r.Year, "y": r.Tc, "type": chartResultType(r.Type),
			"family_id": chartFamilyID(r.FamilyID), "family_name": chartFamilyName(r.FamilyName),
			"formula": r.Material, "doi": r.DOI,
			"year": r.Year, "tc_field": tcField,
		}
		if r.Pressure != nil {
			item["pressure_gpa"] = *r.Pressure
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
		PaperIDs        []uint `json:"paper_ids"`
		Status          string `json:"status"`
		ReviewRequestID string `json:"review_request_id"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "参数错误"})
		return
	}
	if len(body.PaperIDs) == 0 || !isValidReviewStatus(body.Status) {
		c.JSON(http.StatusBadRequest, gin.H{"error": "论文列表为空或审核状态无效"})
		return
	}
	if body.Status == reviewStatusApproved {
		c.JSON(http.StatusBadRequest, gin.H{"error": "批准论文前需要逐篇确认材料分类"})
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

	if len(body.ReviewRequestID) > 48 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "review_request_id 过长"})
		return
	}
	now := time.Now()
	if err := database.DB.Transaction(func(tx *gorm.DB) error {
		for i := range papers {
			requestID := body.ReviewRequestID
			if requestID != "" {
				requestID = fmt.Sprintf("%s:%d", requestID, papers[i].ID)
			}
			if _, err := applyPaperReview(tx, &papers[i], user.ID, body.Status, "", requestID, "batch", now, nil); err != nil {
				return err
			}
		}
		return nil
	}); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "批量审核失败"})
		return
	}
	cache.FlushPattern("chart:*")
	cache.FlushPattern("search:*")
	cache.FlushPattern("community:contributions:*")
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

	authToken := c.GetHeader("Authorization")
	failedIDs := make([]uint, 0)

	for _, id := range body.PaperIDs {
		if err := CascadeDeletePaper(id, authToken); err != nil {
			log.Printf("批量删除: paper %d 失败: %v", id, err)
			failedIDs = append(failedIDs, id)
		}
	}

	if len(failedIDs) > 0 {
		c.JSON(http.StatusPartialContent, gin.H{
			"message":    "部分删除失败",
			"failed_ids": failedIDs,
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "批量删除完成"})
}
