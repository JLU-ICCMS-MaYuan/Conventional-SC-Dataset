package handlers

import (
	"errors"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"scwiki/server/database"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

var (
	errGovernanceSelf    = errors.New("不能对自己的账号执行该操作")
	errLastSuperadmin    = errors.New("系统必须至少保留一名可用的超级管理员")
	errInvalidTransition = errors.New("账号状态或角色不允许该操作")
)

func ListGovernanceUsers(c *gin.Context) {
	var users []models.User
	query := database.DB.Order("created_at DESC").Limit(200)
	if role := c.Query("role"); role != "" {
		query = query.Where("role = ?", role)
	}
	if status := c.Query("status"); status != "" {
		query = query.Where("account_status = ?", status)
	}
	if err := query.Find(&users).Error; err != nil {
		c.JSON(500, gin.H{"error": "用户列表加载失败"})
		return
	}
	result := make([]gin.H, 0, len(users))
	for _, user := range users {
		result = append(result, gin.H{"id": user.ID, "email": user.Email, "username": user.Username, "real_name": user.RealName, "affiliation": user.Affiliation, "role": user.Role, "account_status": user.AccountStatus, "is_email_verified": user.IsEmailVerified, "created_at": user.CreatedAt})
	}
	c.JSON(200, result)
}

func requireGovernanceReason(c *gin.Context) (string, bool) {
	var body struct {
		Reason string `json:"reason"`
	}
	if c.ShouldBindJSON(&body) != nil || strings.TrimSpace(body.Reason) == "" || len([]rune(body.Reason)) > 1000 {
		c.JSON(400, gin.H{"error": "操作原因必填且最多 1000 个字符"})
		return "", false
	}
	return strings.TrimSpace(body.Reason), true
}

func ensureCanRemoveSuperadmin(tx *gorm.DB, target models.User) error {
	if target.Role != "superadmin" || target.AccountStatus != "active" {
		return nil
	}
	var users []models.User
	if err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).Where("role = 'superadmin' AND account_status = 'active'").Find(&users).Error; err != nil {
		return err
	}
	if len(users) <= 1 {
		return errLastSuperadmin
	}
	return nil
}

func governanceError(c *gin.Context, err error) {
	switch {
	case errors.Is(err, errGovernanceSelf), errors.Is(err, errLastSuperadmin):
		c.JSON(403, gin.H{"error": err.Error()})
	case errors.Is(err, errInvalidTransition), errors.Is(err, gorm.ErrInvalidData):
		c.JSON(409, gin.H{"error": errInvalidTransition.Error()})
	case errors.Is(err, gorm.ErrRecordNotFound):
		c.JSON(404, gin.H{"error": "用户不存在"})
	default:
		c.JSON(500, gin.H{"error": "账号治理操作失败"})
	}
}

func changeAccountStatus(c *gin.Context, targetStatus, eventType string) {
	actor, ok := currentUserFromContext(c)
	if !ok {
		return
	}
	reason, ok := requireGovernanceReason(c)
	if !ok {
		return
	}
	var oldAvatar *string
	err := database.DB.Transaction(func(tx *gorm.DB) error {
		var target models.User
		if err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).First(&target, c.Param("id")).Error; err != nil {
			return err
		}
		if target.ID == actor.ID {
			return errGovernanceSelf
		}
		if target.AccountStatus == "deactivated" || target.AccountStatus == targetStatus {
			return errInvalidTransition
		}
		if targetStatus == "active" && target.AccountStatus != "banned" {
			return errInvalidTransition
		}
		if targetStatus != "active" {
			if err := ensureCanRemoveSuperadmin(tx, target); err != nil {
				return err
			}
		}
		oldStatus := target.AccountStatus
		oldAvatar = target.AvatarKey
		updates := map[string]any{"account_status": targetStatus, "session_version": gorm.Expr("session_version + 1")}
		if targetStatus == "deactivated" {
			updates["avatar_key"] = nil
			updates["real_name"] = ""
			updates["affiliation"] = nil
			updates["orcid"] = nil
			updates["research_interests"] = nil
		}
		if err := tx.Model(&target).Updates(updates).Error; err != nil {
			return err
		}
		return tx.Create(&models.UserGovernanceAuditEvent{ActorUserID: actor.ID, TargetUserID: target.ID, EventType: eventType, OldRole: &target.Role, NewRole: &target.Role, OldStatus: &oldStatus, NewStatus: &targetStatus, Reason: reason, CreatedAt: time.Now()}).Error
	})
	if err != nil {
		governanceError(c, err)
		return
	}
	if targetStatus == "deactivated" && oldAvatar != nil {
		_ = os.Remove(filepath.Join(avatarDir, filepath.Base(*oldAvatar)))
	}
	c.JSON(200, gin.H{"message": "账号状态已更新", "account_status": targetStatus})
}

func BanUser(c *gin.Context)        { changeAccountStatus(c, "banned", "banned") }
func UnbanUser(c *gin.Context)      { changeAccountStatus(c, "active", "unbanned") }
func DeactivateUser(c *gin.Context) { changeAccountStatus(c, "deactivated", "deactivated") }

func ChangeUserRole(c *gin.Context) {
	actor, ok := currentUserFromContext(c)
	if !ok {
		return
	}
	var body struct {
		Role   string `json:"role"`
		Reason string `json:"reason"`
	}
	if c.ShouldBindJSON(&body) != nil || (body.Role != "user" && body.Role != "admin" && body.Role != "superadmin") || strings.TrimSpace(body.Reason) == "" {
		c.JSON(400, gin.H{"error": "角色无效且操作原因必填"})
		return
	}
	err := database.DB.Transaction(func(tx *gorm.DB) error {
		var target models.User
		if err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).First(&target, c.Param("id")).Error; err != nil {
			return err
		}
		if target.ID == actor.ID {
			return errGovernanceSelf
		}
		if target.AccountStatus != "active" || target.Role == body.Role {
			return errInvalidTransition
		}
		if target.Role == "superadmin" {
			if err := ensureCanRemoveSuperadmin(tx, target); err != nil {
				return err
			}
		}
		oldRole := target.Role
		if err := tx.Model(&target).Updates(map[string]any{"role": body.Role, "session_version": gorm.Expr("session_version + 1")}).Error; err != nil {
			return err
		}
		event := "role_changed"
		if oldRole == "admin" && body.Role == "user" {
			event = "role_demoted"
		}
		return tx.Create(&models.UserGovernanceAuditEvent{ActorUserID: actor.ID, TargetUserID: target.ID, EventType: event, OldRole: &oldRole, NewRole: &body.Role, OldStatus: &target.AccountStatus, NewStatus: &target.AccountStatus, Reason: strings.TrimSpace(body.Reason), CreatedAt: time.Now()}).Error
	})
	if err != nil {
		governanceError(c, err)
		return
	}
	c.JSON(200, gin.H{"message": "角色已更新", "role": body.Role})
}

func ListProfileAudits(c *gin.Context) {
	var events []models.ProfileChangeAuditEvent
	if err := database.DB.Order("created_at DESC").Limit(200).Find(&events).Error; err != nil {
		c.JSON(500, gin.H{"error": "审计加载失败"})
		return
	}
	c.JSON(200, events)
}

func ListGovernanceAudits(c *gin.Context) {
	var events []models.UserGovernanceAuditEvent
	if err := database.DB.Order("created_at DESC").Limit(200).Find(&events).Error; err != nil {
		c.JSON(500, gin.H{"error": "审计加载失败"})
		return
	}
	c.JSON(200, events)
}

func DeprecatedDeleteUser(c *gin.Context) {
	c.JSON(http.StatusMethodNotAllowed, gin.H{"error": "请使用账号注销操作"})
}
