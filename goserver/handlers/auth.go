package handlers

import (
	"crypto/hmac"
	cryptorand "crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"math/big"
	"net/http"
	"os"
	"strings"
	"time"

	"scwiki/server/cache"
	"scwiki/server/config"
	"scwiki/server/database"
	"scwiki/server/middleware"
	"scwiki/server/models"
	"scwiki/server/services"

	"github.com/gin-gonic/gin"
	"golang.org/x/crypto/bcrypt"
	"gorm.io/gorm"
)

const verificationTTL = 5 * time.Minute

var (
	authMailer         services.Mailer
	verificationSecret []byte
	avatarDir          string
)

func ConfigureAuth(cfg config.Config) {
	authMailer = services.NewSMTPMailer(services.EmailConfig{
		Host: cfg.SMTPHost, Port: cfg.SMTPPort, Username: cfg.SMTPUsername,
		Password: cfg.SMTPPassword, From: cfg.SMTPFrom, TLSMode: cfg.SMTPTLSMode,
	})
	verificationSecret = []byte(cfg.JWTSecret)
	avatarDir = cfg.AvatarDir
	_ = os.MkdirAll(avatarDir, 0o750)
}

func normalizeEmail(email string) string { return strings.ToLower(strings.TrimSpace(email)) }

func emailKey(email string) string {
	sum := sha256.Sum256([]byte(normalizeEmail(email)))
	return hex.EncodeToString(sum[:])
}

func verificationDigest(email, code string) string {
	mac := hmac.New(sha256.New, verificationSecret)
	mac.Write([]byte(normalizeEmail(email)))
	mac.Write([]byte{0})
	mac.Write([]byte(code))
	return hex.EncodeToString(mac.Sum(nil))
}

func verificationCode() (string, error) {
	n, err := cryptorand.Int(cryptorand.Reader, big.NewInt(1_000_000))
	if err != nil {
		return "", err
	}
	return fmt.Sprintf("%06d", n.Int64()), nil
}

func checkSendLimits(email, ip string) (int, error) {
	now := time.Now().UTC()
	keys := []struct {
		key string
		ttl time.Duration
		max int64
	}{
		{"verify:rate:email:hour:" + emailKey(email) + ":" + now.Format("2006010215"), time.Hour, 5},
		{"verify:rate:email:day:" + emailKey(email) + ":" + now.Format("20060102"), 24 * time.Hour, 10},
		{"verify:rate:ip:hour:" + ip + ":" + now.Format("2006010215"), time.Hour, 5},
		{"verify:rate:ip:day:" + ip + ":" + now.Format("20060102"), 24 * time.Hour, 10},
	}
	for _, item := range keys {
		count, err := cache.IncrementWindow(item.key, item.ttl)
		if err != nil {
			return 0, err
		}
		if count > item.max {
			return 3600, nil
		}
	}
	return 0, nil
}

func sendVerification(email, ip string) (int, error) {
	if authMailer == nil {
		return 0, fmt.Errorf("邮件服务未配置")
	}
	retryAfter, err := checkSendLimits(email, ip)
	if err != nil || retryAfter > 0 {
		return retryAfter, err
	}
	code, err := verificationCode()
	if err != nil {
		return 0, err
	}
	key := "verify:code:" + emailKey(email)
	if err := cache.SetString(key, verificationDigest(email, code), verificationTTL); err != nil {
		return 0, err
	}
	if err := authMailer.SendVerificationCode(email, code); err != nil {
		_ = cache.Delete(key)
		return 0, err
	}
	return 0, nil
}

func loginHandler(c *gin.Context) {
	var body struct{ Email, Password string }
	if c.ShouldBindJSON(&body) != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "参数错误"})
		return
	}
	var user models.User
	if database.DB.Where("email = ?", normalizeEmail(body.Email)).First(&user).Error != nil ||
		bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(body.Password)) != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "邮箱或密码错误"})
		return
	}
	if user.AccountStatus != "" && user.AccountStatus != "active" {
		c.JSON(http.StatusForbidden, gin.H{"error": "账号不可用", "code": "account_inactive"})
		return
	}
	if !user.IsEmailVerified {
		c.JSON(http.StatusForbidden, gin.H{"error": "邮箱尚未验证", "code": "email_not_verified"})
		return
	}
	token, err := middleware.GenerateTokenForUser(user)
	if err != nil {
		c.JSON(500, gin.H{"error": "生成 token 失败"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"access_token": token, "token_type": "bearer", "user": clientUserPayload(user)})
}

func registerHandler(c *gin.Context) {
	var body struct {
		Email    string `json:"email"`
		Password string `json:"password"`
		Username string `json:"username"`
		RealName string `json:"real_name"`
	}
	if c.ShouldBindJSON(&body) != nil || body.Email == "" || body.Username == "" || len(body.Password) < 10 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "邮箱、用户名不能为空，密码至少 10 位"})
		return
	}
	body.Email = normalizeEmail(body.Email)
	if err := validatePublicUsername(body.Username); err != nil {
		c.JSON(400, gin.H{"error": err.Error()})
		return
	}
	var existing models.User
	err := database.DB.Where("email = ?", body.Email).First(&existing).Error
	if err == nil {
		if existing.IsEmailVerified {
			c.JSON(409, gin.H{"error": "该邮箱已注册"})
			return
		}
		if retry, sendErr := sendVerification(body.Email, c.ClientIP()); sendErr != nil {
			c.JSON(503, gin.H{"error": "验证码发送失败"})
			return
		} else if retry > 0 {
			c.Header("Retry-After", fmt.Sprint(retry))
			c.JSON(429, gin.H{"error": "请求过于频繁"})
			return
		}
		c.JSON(http.StatusAccepted, gin.H{"requires_email_verification": true, "resend_after_seconds": 60})
		return
	}
	if err != gorm.ErrRecordNotFound {
		c.JSON(500, gin.H{"error": "注册失败"})
		return
	}
	available, err := usernameAvailable(database.DB, body.Username, 0)
	if err != nil {
		c.JSON(500, gin.H{"error": "用户名检查失败"})
		return
	}
	if !available {
		c.JSON(409, gin.H{"error": errUsernameTaken.Error()})
		return
	}
	hash, err := bcrypt.GenerateFromPassword([]byte(body.Password), bcrypt.DefaultCost)
	if err != nil {
		c.JSON(500, gin.H{"error": "密码加密失败"})
		return
	}
	user := models.User{Email: body.Email, Username: body.Username, PasswordHash: string(hash), RealName: strings.TrimSpace(body.RealName), Role: "user", IsApproved: true, IsEmailVerified: false, AccountStatus: "active"}
	if err := database.DB.Create(&user).Error; err != nil {
		c.JSON(409, gin.H{"error": "邮箱或用户名已被占用"})
		return
	}
	if retry, sendErr := sendVerification(body.Email, c.ClientIP()); sendErr != nil {
		c.JSON(503, gin.H{"error": "验证码发送失败，可稍后重新发送"})
		return
	} else if retry > 0 {
		c.Header("Retry-After", fmt.Sprint(retry))
		c.JSON(429, gin.H{"error": "请求过于频繁"})
		return
	}
	c.JSON(http.StatusAccepted, gin.H{"requires_email_verification": true, "resend_after_seconds": 60})
}

func VerifyEmail(c *gin.Context) {
	var body struct {
		Email string `json:"email"`
		Code  string `json:"code"`
	}
	if c.ShouldBindJSON(&body) != nil || len(body.Code) != 6 {
		c.JSON(400, gin.H{"error": "验证码无效"})
		return
	}
	body.Email = normalizeEmail(body.Email)
	status, err := cache.ConsumeVerificationCode("verify:code:"+emailKey(body.Email), "verify:attempts:"+emailKey(body.Email), verificationDigest(body.Email, body.Code), 5, verificationTTL)
	if err != nil {
		c.JSON(503, gin.H{"error": "验证服务暂不可用"})
		return
	}
	if status != "valid" {
		c.JSON(400, gin.H{"error": "验证码无效或已过期", "code": status})
		return
	}
	var user models.User
	if database.DB.Where("email = ?", body.Email).First(&user).Error != nil {
		c.JSON(400, gin.H{"error": "验证码无效或已过期"})
		return
	}
	if err := database.DB.Model(&user).Updates(map[string]any{"is_email_verified": true, "is_approved": true}).Error; err != nil {
		c.JSON(500, gin.H{"error": "验证失败"})
		return
	}
	user.IsEmailVerified, user.IsApproved = true, true
	token, err := middleware.GenerateTokenForUser(user)
	if err != nil {
		c.JSON(500, gin.H{"error": "生成 token 失败"})
		return
	}
	c.JSON(200, gin.H{"access_token": token, "token_type": "bearer", "user": clientUserPayload(user)})
}

func ResendVerification(c *gin.Context) {
	var body struct {
		Email string `json:"email"`
	}
	if c.ShouldBindJSON(&body) != nil {
		c.JSON(202, gin.H{"message": "如果邮箱可验证，验证码将发送"})
		return
	}
	email := normalizeEmail(body.Email)
	var user models.User
	if database.DB.Where("email = ?", email).First(&user).Error == nil && !user.IsEmailVerified {
		retry, err := sendVerification(email, c.ClientIP())
		if err != nil {
			c.JSON(503, gin.H{"error": "验证码发送失败"})
			return
		}
		if retry > 0 {
			c.Header("Retry-After", fmt.Sprint(retry))
			c.JSON(429, gin.H{"error": "请求过于频繁"})
			return
		}
	}
	c.JSON(202, gin.H{"message": "如果邮箱可验证，验证码将发送", "resend_after_seconds": 60})
}

func GetCurrentUser(c *gin.Context) {
	value, ok := c.Get("current_user")
	if !ok {
		c.JSON(401, gin.H{"error": "未登录"})
		return
	}
	c.JSON(200, gin.H{"user": clientUserPayload(*value.(*models.User))})
}
