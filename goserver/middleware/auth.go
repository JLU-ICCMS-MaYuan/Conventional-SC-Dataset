package middleware

import (
	"net/http"
	"strings"
	"time"

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

// AdminRequired 管理员权限检查（需在 AuthRequired 之后）
func AdminRequired(c *gin.Context) {
	c.Next() // 暂时放行，后续查 DB 验证角色
}
