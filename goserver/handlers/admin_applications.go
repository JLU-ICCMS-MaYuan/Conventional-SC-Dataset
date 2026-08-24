package handlers

import (
	"net/http"
	"strings"
	"time"

	"scwiki/server/database"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

func SubmitAdminApplication(c *gin.Context) {
	user, ok := currentUserFromContext(c)
	if !ok {
		return
	}
	if user.Role != "user" || user.AccountStatus != "active" || !user.IsEmailVerified || strings.TrimSpace(user.RealName) == "" || user.Affiliation == nil || strings.TrimSpace(*user.Affiliation) == "" {
		c.JSON(400, gin.H{"error": "申请前需验证邮箱并填写真实姓名和所属机构"})
		return
	}
	guard := true
	application := models.AdminApplication{UserID: user.ID, RealNameSnapshot: user.RealName, AffiliationSnapshot: *user.Affiliation, ORCIDSnapshot: user.ORCID, ResearchInterestsSnapshot: user.ResearchInterests, Status: "pending", PendingGuard: &guard, SubmittedAt: time.Now()}
	if err := database.DB.Create(&application).Error; err != nil {
		c.JSON(409, gin.H{"error": "已有待审核申请"})
		return
	}
	c.JSON(http.StatusCreated, application)
}

func GetOwnAdminApplications(c *gin.Context) {
	user, ok := currentUserFromContext(c)
	if !ok {
		return
	}
	var applications []models.AdminApplication
	database.DB.Where("user_id = ?", user.ID).Order("submitted_at DESC").Find(&applications)
	c.JSON(200, applications)
}

func WithdrawAdminApplication(c *gin.Context) {
	user, ok := currentUserFromContext(c)
	if !ok {
		return
	}
	now := time.Now()
	result := database.DB.Model(&models.AdminApplication{}).Where("id = ? AND user_id = ? AND status = 'pending'", c.Param("id"), user.ID).Updates(map[string]any{"status": "withdrawn", "pending_guard": nil, "withdrawn_at": now})
	if result.Error != nil {
		c.JSON(500, gin.H{"error": "撤回失败"})
		return
	}
	if result.RowsAffected != 1 {
		c.JSON(409, gin.H{"error": "申请已不是待审核状态"})
		return
	}
	c.JSON(200, gin.H{"message": "申请已撤回"})
}

func ListAdminApplications(c *gin.Context) {
	query := database.DB.Order("submitted_at DESC")
	if status := c.Query("status"); status != "" {
		query = query.Where("status = ?", status)
	}
	var applications []models.AdminApplication
	if err := query.Limit(100).Find(&applications).Error; err != nil {
		c.JSON(500, gin.H{"error": "申请列表加载失败"})
		return
	}
	c.JSON(200, applications)
}

func ApproveAdminApplication(c *gin.Context) {
	actor, ok := currentUserFromContext(c)
	if !ok {
		return
	}
	now := time.Now()
	err := database.DB.Transaction(func(tx *gorm.DB) error {
		var app models.AdminApplication
		if err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).First(&app, c.Param("id")).Error; err != nil {
			return err
		}
		if app.Status != "pending" {
			return gorm.ErrInvalidData
		}
		var user models.User
		if err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).First(&user, app.UserID).Error; err != nil {
			return err
		}
		if user.Role != "user" || user.AccountStatus != "active" {
			return gorm.ErrInvalidData
		}
		if err := tx.Model(&user).Updates(map[string]any{"role": "admin", "session_version": gorm.Expr("session_version + 1")}).Error; err != nil {
			return err
		}
		if err := tx.Model(&app).Updates(map[string]any{"status": "approved", "pending_guard": nil, "reviewed_by_user_id": actor.ID, "reviewed_at": now}).Error; err != nil {
			return err
		}
		oldRole, newRole := "user", "admin"
		return tx.Create(&models.UserGovernanceAuditEvent{ActorUserID: actor.ID, TargetUserID: user.ID, EventType: "role_promoted", OldRole: &oldRole, NewRole: &newRole, Reason: "管理员资格申请通过", CreatedAt: now}).Error
	})
	if err != nil {
		c.JSON(409, gin.H{"error": "申请已处理或申请人状态不再符合条件"})
		return
	}
	c.JSON(200, gin.H{"message": "已批准管理员申请"})
}

func RejectAdminApplication(c *gin.Context) {
	actor, ok := currentUserFromContext(c)
	if !ok {
		return
	}
	var body struct {
		Reason string `json:"reason"`
	}
	if c.ShouldBindJSON(&body) != nil || strings.TrimSpace(body.Reason) == "" || len([]rune(body.Reason)) > 1000 {
		c.JSON(400, gin.H{"error": "拒绝原因必填且最多 1000 个字符"})
		return
	}
	now := time.Now()
	result := database.DB.Model(&models.AdminApplication{}).Where("id = ? AND status = 'pending'", c.Param("id")).Updates(map[string]any{"status": "rejected", "pending_guard": nil, "rejection_reason": strings.TrimSpace(body.Reason), "reviewed_by_user_id": actor.ID, "reviewed_at": now})
	if result.Error != nil {
		c.JSON(500, gin.H{"error": "拒绝失败"})
		return
	}
	if result.RowsAffected != 1 {
		c.JSON(409, gin.H{"error": "申请已不是待审核状态"})
		return
	}
	c.JSON(200, gin.H{"message": "已拒绝管理员申请"})
}
