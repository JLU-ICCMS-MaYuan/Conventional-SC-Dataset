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

var chartTcColumns = map[string]string{
	"experimental_tc":           "sr.experimental_tc",
	"anisotropic_eliashberg_tc": "sr.anisotropic_eliashberg_tc",
	"isotropic_eliashberg_tc":   "sr.isotropic_eliashberg_tc",
	"allen_dynes_tc":            "sr.allen_dynes_tc",
	"mcmillan_tc":               "sr.mcmillan_tc",
}

func resolveChartTcField(value string) (string, string, bool) {
	field := strings.TrimSpace(value)
	if field == "" {
		field = defaultTcField
	}
	column, ok := chartTcColumns[field]
	if !ok {
		return "", "", false
	}
	return field, column, true
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
	tcField, tcColumn, ok := resolveChartTcField(c.Query("tc_field"))
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
		Material string  `gorm:"column:material"`
		Tc       float64 `gorm:"column:y"`
		Pressure float64 `gorm:"column:x"`
		SCType   string  `gorm:"column:sc_type"`
		Type     string  `gorm:"column:type"`
		PaperID  uint    `gorm:"column:paper_id"`
		DOI      string  `gorm:"column:doi"`
		Year     int     `gorm:"column:year"`
	}
	var rows []row
	query := fmt.Sprintf(`
		SELECT sc.chemical_formula AS material, %s AS y, sr.pressure_gpa AS x,
			COALESCE(sr.superconductor_type,'others') AS sc_type,
			CASE WHEN sr.article_type='e' THEN 'experimental' ELSE 'theoretical' END AS type,
			sr.paper_id, COALESCE(p.doi,'') AS doi, COALESCE(p.year,0) AS year
		FROM superconductor_records sr
		JOIN superconductors sc ON sc.id = sr.superconductor_id
		JOIN papers p ON p.id = sr.paper_id AND p.review_status = 'approved'
		WHERE sr.show_in_chart = true AND %s IS NOT NULL
			AND sr.pressure_gpa IS NOT NULL
	`, tcColumn, tcColumn)
	database.DB.Raw(query).Scan(&rows)

	result = make([]gin.H, 0, len(rows))
	for _, r := range rows {
		t := r.Type
		if t == "" {
			t = "theoretical"
		}
		item := gin.H{
			"formula": r.Material,
			"y":       r.Tc, "x": r.Pressure,
			"sc_type": r.SCType, "type": t, "tc_field": tcField,
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

// TcYearChart Tc-Year 散点图数据
// GET /api/papers/stats/tc-year
func TcYearChart(c *gin.Context) {
	tcField, tcColumn, ok := resolveChartTcField(c.Query("tc_field"))
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
		Year     int     `gorm:"column:x"`
		Tc       float64 `gorm:"column:y"`
		Type     string  `gorm:"column:type"`
		SCType   string  `gorm:"column:sc_type"`
		Material string  `gorm:"column:formula"`
		DOI      string  `gorm:"column:doi"`
		PaperID  uint    `gorm:"column:paper_id"`
		Pressure float64 `gorm:"column:pressure_gpa"`
	}
	var rows []row
	query := fmt.Sprintf(`
		SELECT p.year AS x, %s AS y,
			CASE WHEN sr.article_type='e' THEN 'experimental' ELSE 'theoretical' END AS type,
			COALESCE(sr.superconductor_type,'others') AS sc_type,
			sc.chemical_formula AS formula, COALESCE(p.doi,'') AS doi,
			sr.paper_id AS paper_id, sr.pressure_gpa
		FROM superconductor_records sr
		JOIN superconductors sc ON sc.id = sr.superconductor_id
		JOIN papers p ON p.id = sr.paper_id AND p.review_status = 'approved'
		WHERE sr.show_in_chart = true AND %s IS NOT NULL AND p.year IS NOT NULL
	`, tcColumn, tcColumn)
	database.DB.Raw(query).Scan(&rows)

	result = make([]gin.H, 0, len(rows))
	for _, r := range rows {
		t := r.Type
		if t == "" {
			t = "theoretical"
		}
		item := gin.H{
			"x": r.Year, "y": r.Tc, "type": t,
			"sc_type": r.SCType, "formula": r.Material, "doi": r.DOI,
			"year": r.Year, "pressure_gpa": r.Pressure, "tc_field": tcField,
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
