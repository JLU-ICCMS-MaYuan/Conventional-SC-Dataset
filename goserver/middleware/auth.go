package middleware

import (
	"net/http"
	"strings"
	"time"

	"scwiki/server/database"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
)

var jwtSecret []byte

// InitJWT 设置 JWT 密钥
func InitJWT(secret string) {
	jwtSecret = []byte(secret)
}

// Claims JWT 载荷
type Claims struct {
	Email          string `json:"sub"`
	SessionVersion int64  `json:"sv"`
	jwt.RegisteredClaims
}

// GenerateToken 生成 token（管理员创建用）
func GenerateToken(email string) (string, error) {
	return generateToken(email, 0)
}

// GenerateTokenForUser 为已从数据库读取的用户签发带会话版本的 Token。
func GenerateTokenForUser(user models.User) (string, error) {
	return generateToken(user.Email, user.SessionVersion)
}

func generateToken(email string, sessionVersion int64) (string, error) {
	claims := Claims{
		Email:          email,
		SessionVersion: sessionVersion,
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(60 * 24 * time.Hour)), // 60天
		},
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString(jwtSecret)
}

func authenticatedUser(c *gin.Context, claims *Claims) (*models.User, bool) {
	var user models.User
	if database.DB == nil || database.DB.Where("email = ?", claims.Email).First(&user).Error != nil {
		c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "用户不存在"})
		return nil, false
	}
	if user.AccountStatus != "" && user.AccountStatus != "active" {
		c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "账号不可用", "code": "account_inactive"})
		return nil, false
	}
	if user.SessionVersion != claims.SessionVersion {
		c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "登录已失效", "code": "session_revoked"})
		return nil, false
	}
	c.Set("user_email", user.Email)
	c.Set("current_user", &user)
	return &user, true
}

// AuthRequired gin 中间件 —— 验证 JWT
// gin.HandlerFunc 本质是 func(c *gin.Context)
// c *gin.Context 包含 request + response + 中间件状态
func AuthRequired(c *gin.Context) {
	// Bearer token
	header := c.GetHeader("Authorization")
	if header == "" || !strings.HasPrefix(header, "Bearer ") {
		c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "未登录"})
		return
	}

	tokenStr := strings.TrimPrefix(header, "Bearer ")
	claims := &Claims{}
	token, err := jwt.ParseWithClaims(tokenStr, claims, func(t *jwt.Token) (interface{}, error) {
		return jwtSecret, nil
	})

	if err != nil || !token.Valid {
		c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "token 无效"})
		return
	}

	if _, ok := authenticatedUser(c, claims); !ok {
		return
	}
	c.Next() // ← 放行到下一个 handler
}

// OptionalAuth 允许匿名访问；若携带 Token，则必须验证成功。
func OptionalAuth(c *gin.Context) {
	header := c.GetHeader("Authorization")
	if header == "" {
		c.Next()
		return
	}
	if !strings.HasPrefix(header, "Bearer ") {
		c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "token 无效"})
		return
	}
	claims := &Claims{}
	token, err := jwt.ParseWithClaims(strings.TrimPrefix(header, "Bearer "), claims, func(t *jwt.Token) (interface{}, error) {
		return jwtSecret, nil
	})
	if err != nil || !token.Valid {
		c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "token 无效"})
		return
	}
	if _, ok := authenticatedUser(c, claims); !ok {
		return
	}
	c.Next()
}

// AdminRequired 管理员权限检查（需在 AuthRequired 之后）
func AdminRequired(c *gin.Context) {
	value, exists := c.Get("current_user")
	if !exists {
		c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "未登录"})
		return
	}
	user := value.(*models.User)

	if user.Role != "admin" && user.Role != "superadmin" {
		c.AbortWithStatusJSON(http.StatusForbidden, gin.H{"error": "需要管理员权限"})
		return
	}

	c.Next()
}

// SuperAdminRequired 超级管理员权限检查（需在 AuthRequired 之后）。
func SuperAdminRequired(c *gin.Context) {
	value, exists := c.Get("current_user")
	if !exists {
		c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "未登录"})
		return
	}
	user := value.(*models.User)
	if user.Role != "superadmin" {
		c.AbortWithStatusJSON(http.StatusForbidden, gin.H{"error": "需要超级管理员权限"})
		return
	}
	c.Next()
}
