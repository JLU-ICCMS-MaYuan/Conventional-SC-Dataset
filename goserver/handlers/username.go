package handlers

import (
	"crypto/rand"
	"errors"
	"fmt"
	"math/big"
	"net/http"
	"regexp"
	"strconv"
	"strings"
	"time"

	"scwiki/server/cache"
	"scwiki/server/database"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
	mysqldriver "github.com/go-sql-driver/mysql"
	"gorm.io/gorm"
)

var (
	publicUsernamePattern       = regexp.MustCompile(`^[A-Za-z][A-Za-z0-9_]{2,31}$`)
	errUsernameTaken            = errors.New("用户名已被占用")
	errUsernameChangeNotAllowed = errors.New("没有用户名修改资格")
	reservedUsernames           = map[string]struct{}{
		"admin": {}, "administrator": {}, "root": {},
		"scwiki": {}, "superadmin": {}, "system": {},
	}
)

const historicalUsernameAlphabet = "abcdefghijklmnopqrstuvwxyz0123456789"

func validatePublicUsername(username string) error {
	if !publicUsernamePattern.MatchString(username) {
		return errors.New("用户名须为 3–32 位，以字母开头且只包含字母、数字和下划线")
	}
	normalized := strings.ToLower(username)
	if strings.HasPrefix(normalized, "sc_") {
		return errors.New("sc_ 前缀由系统保留")
	}
	if _, reserved := reservedUsernames[normalized]; reserved {
		return errors.New("该用户名由系统保留")
	}
	return nil
}

func generateHistoricalUsername() (string, error) {
	random := make([]byte, 12)
	for i := range random {
		index, err := rand.Int(rand.Reader, big.NewInt(int64(len(historicalUsernameAlphabet))))
		if err != nil {
			return "", err
		}
		random[i] = historicalUsernameAlphabet[index.Int64()]
	}
	return "sc_" + string(random), nil
}

func usernameAvailable(db *gorm.DB, username string, excludeUserID uint) (bool, error) {
	query := db.Model(&models.User{}).Where("username = ?", username)
	if excludeUserID > 0 {
		query = query.Where("id <> ?", excludeUserID)
	}
	var count int64
	if err := query.Count(&count).Error; err != nil {
		return false, err
	}
	return count == 0, nil
}

func isDuplicateKeyError(err error) bool {
	var mysqlErr *mysqldriver.MySQLError
	return errors.As(err, &mysqlErr) && mysqlErr.Number == 1062
}

func clientUserPayload(user models.User) gin.H {
	return gin.H{
		"id":                      user.ID,
		"email":                   user.Email,
		"username":                user.Username,
		"username_change_allowed": user.UsernameChangeAllowed,
		"role":                    user.Role,
		"is_admin":                user.Role == "admin" || user.Role == "superadmin",
		"is_superadmin":           user.Role == "superadmin",
		"is_approved":             user.IsApproved,
		"is_email_verified":       user.IsEmailVerified,
		"account_status":          user.AccountStatus,
		"avatar_url":              avatarURL(user),
		"created_at":              user.CreatedAt,
		"approved_at":             user.ApprovedAt,
	}
}

func avatarURL(user models.User) *string {
	if user.AvatarKey == nil || *user.AvatarKey == "" {
		return nil
	}
	value := "/api/users/" + user.Username + "/avatar"
	return &value
}

// UsernameAvailability 返回规则与占用状态，不泄露账号资料。
func UsernameAvailability(c *gin.Context) {
	username := c.Query("username")
	if err := validatePublicUsername(username); err != nil {
		c.JSON(http.StatusOK, gin.H{"available": false, "reason": err.Error()})
		return
	}
	available, err := usernameAvailable(database.DB, username, 0)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "用户名检查失败"})
		return
	}
	response := gin.H{"available": available}
	if !available {
		response["reason"] = errUsernameTaken.Error()
	}
	c.JSON(http.StatusOK, response)
}

func currentUserFromContext(c *gin.Context) (*models.User, bool) {
	email, exists := c.Get("user_email")
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "未登录"})
		return nil, false
	}
	var user models.User
	if err := database.DB.Where("email = ?", email).First(&user).Error; err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "用户不存在"})
		return nil, false
	}
	return &user, true
}

func applySelfUsernameChange(db *gorm.DB, userID uint, username string) error {
	return db.Transaction(func(tx *gorm.DB) error {
		result := tx.Model(&models.User{}).
			Where("id = ? AND username_change_allowed = ?", userID, true).
			Updates(map[string]any{"username": username, "username_change_allowed": false})
		if result.Error != nil {
			if isDuplicateKeyError(result.Error) {
				return errUsernameTaken
			}
			return result.Error
		}
		if result.RowsAffected != 1 {
			return errUsernameChangeNotAllowed
		}
		return nil
	})
}

// UpdateOwnUsername 允许历史账号成功自助更名一次。
func UpdateOwnUsername(c *gin.Context) {
	user, ok := currentUserFromContext(c)
	if !ok {
		return
	}
	var body struct {
		Username string `json:"username"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "参数错误"})
		return
	}
	if err := validatePublicUsername(body.Username); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	available, err := usernameAvailable(database.DB, body.Username, user.ID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "用户名检查失败"})
		return
	}
	if !available {
		c.JSON(http.StatusConflict, gin.H{"error": errUsernameTaken.Error()})
		return
	}
	if err := applySelfUsernameChange(database.DB, user.ID, body.Username); err != nil {
		switch {
		case errors.Is(err, errUsernameChangeNotAllowed):
			c.JSON(http.StatusForbidden, gin.H{"error": err.Error()})
		case errors.Is(err, errUsernameTaken):
			c.JSON(http.StatusConflict, gin.H{"error": err.Error()})
		default:
			c.JSON(http.StatusInternalServerError, gin.H{"error": "用户名修改失败"})
		}
		return
	}
	cache.FlushPattern("community:contributions:*")
	if err := database.DB.First(user, user.ID).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "读取用户失败"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "用户名已更新", "user": clientUserPayload(*user)})
}

func applyAdminUsernameChange(
	db *gorm.DB,
	target *models.User,
	changedByUserID uint,
	username string,
	reason string,
	changedAt time.Time,
) error {
	oldUsername := target.Username
	return db.Transaction(func(tx *gorm.DB) error {
		if err := tx.Model(&models.User{}).Where("id = ?", target.ID).
			Update("username", username).Error; err != nil {
			if isDuplicateKeyError(err) {
				return errUsernameTaken
			}
			return err
		}
		event := models.UsernameChangeAuditEvent{
			TargetUserID: target.ID, ChangedByUserID: changedByUserID,
			OldUsername: oldUsername, NewUsername: username,
			Reason: reason, CreatedAt: changedAt,
		}
		return tx.Create(&event).Error
	})
}

// AdminUpdateUsername 超级管理员带原因更名，并在同一事务写审计。
func AdminUpdateUsername(c *gin.Context) {
	actor, ok := currentUserFromContext(c)
	if !ok {
		return
	}
	if actor.Role != "superadmin" {
		c.JSON(http.StatusForbidden, gin.H{"error": "需要超级管理员权限"})
		return
	}
	targetID, err := strconv.ParseUint(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "用户 ID 无效"})
		return
	}
	var body struct {
		Username string `json:"username"`
		Reason   string `json:"reason"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "参数错误"})
		return
	}
	body.Reason = strings.TrimSpace(body.Reason)
	if err := validatePublicUsername(body.Username); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if body.Reason == "" || len([]rune(body.Reason)) > 500 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "更名原因须为 1–500 字符"})
		return
	}
	var target models.User
	if err := database.DB.First(&target, uint(targetID)).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "用户不存在"})
		return
	}
	if target.Username == body.Username {
		c.JSON(http.StatusBadRequest, gin.H{"error": "新用户名不能与当前用户名相同"})
		return
	}
	available, err := usernameAvailable(database.DB, body.Username, target.ID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "用户名检查失败"})
		return
	}
	if !available {
		c.JSON(http.StatusConflict, gin.H{"error": errUsernameTaken.Error()})
		return
	}
	if err := applyAdminUsernameChange(database.DB, &target, actor.ID, body.Username, body.Reason, time.Now()); err != nil {
		if errors.Is(err, errUsernameTaken) {
			c.JSON(http.StatusConflict, gin.H{"error": err.Error()})
		} else {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "用户名修改失败"})
		}
		return
	}
	cache.FlushPattern("community:contributions:*")
	target.Username = body.Username
	c.JSON(http.StatusOK, gin.H{"message": "用户名已更新", "user": clientUserPayload(target)})
}

// GetUsernameAuditEvents 返回只追加的更名审计记录。
func GetUsernameAuditEvents(c *gin.Context) {
	type auditRow struct {
		ID                uint      `json:"id"`
		TargetUserID      uint      `json:"target_user_id"`
		ChangedByUserID   uint      `json:"changed_by_user_id"`
		ChangedByUsername string    `json:"changed_by_username"`
		OldUsername       string    `json:"old_username"`
		NewUsername       string    `json:"new_username"`
		Reason            string    `json:"reason"`
		CreatedAt         time.Time `json:"created_at"`
	}
	var rows []auditRow
	err := database.DB.Table("username_change_audit_events AS e").
		Select("e.id, e.target_user_id, e.changed_by_user_id, u.username AS changed_by_username, e.old_username, e.new_username, e.reason, e.created_at").
		Joins("JOIN users u ON u.id = e.changed_by_user_id").
		Order("e.created_at DESC, e.id DESC").Limit(200).Scan(&rows).Error
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("读取更名审计失败: %v", err)})
		return
	}
	c.JSON(http.StatusOK, rows)
}
