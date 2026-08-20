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
	Email string `json:"sub"`
	jwt.RegisteredClaims
}

// GenerateToken 生成 token（管理员创建用）
func GenerateToken(email string) (string, error) {
	claims := Claims{
		Email: email,
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(60 * 24 * time.Hour)), // 60天
		},
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString(jwtSecret)
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

	// 把 email 存入 context，后续 handler 可读取
	c.Set("user_email", claims.Email)
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
	c.Set("user_email", claims.Email)
	c.Next()
}

// AdminRequired 管理员权限检查（需在 AuthRequired 之后）
func AdminRequired(c *gin.Context) {
	email, exists := c.Get("user_email")
	if !exists {
		c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "未登录"})
		return
	}

	var user models.User
	if err := database.DB.Where("email = ?", email).First(&user).Error; err != nil {
		c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "用户不存在"})
		return
	}

	if user.Role != "admin" && user.Role != "superadmin" {
		c.AbortWithStatusJSON(http.StatusForbidden, gin.H{"error": "需要管理员权限"})
		return
	}

	c.Next()
}
