package main

import (
	"log"
	"net/http/httputil"
	"net/url"

	"scwiki/server/config"
	"scwiki/server/database"
	"scwiki/server/handlers"
	"scwiki/server/middleware"

	"github.com/gin-gonic/gin"
)

func main() {
	// 1. 加载配置
	cfg := config.Load()

	// 2. 连接数据库
	database.Connect(cfg.MySQL_DSN)

	// 3. 初始化 JWT
	middleware.InitJWT(cfg.JWTSecret)

	// 4. 创建路由引擎
	// gin.Default() = 带 Logger + Recovery 中间件
	r := gin.Default()

	// 5. 注册路由
	// CORS
	r.Use(func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,PATCH,OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Content-Type,Authorization")
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}
		c.Next()
	})

	// 公开路由（不需要 JWT）
	r.POST("/api/auth/login", handlers.Login)
	r.GET("/api/admin/stats", handlers.GetStats) // 仪表盘可公开

	// 认证路由组（普通用户可访问，仅需登录）
	auth := r.Group("/api")
	auth.Use(middleware.AuthRequired)
	{
		auth.GET("/papers/my-uploads", handlers.GetMyUploads)
	}

	// 管理员路由组
	// Group 类似 FastAPI 的 APIRouter(prefix="/api/admin")
	admin := r.Group("/api/admin")
	admin.Use(middleware.AuthRequired) // 组级中间件 = 所有子路由都要验证
	{
		admin.GET("/papers/all", handlers.GetPapers)
		admin.GET("/papers/:id", handlers.GetPaperDetail)
		admin.PUT("/papers/:id", handlers.UpdatePaper)
		admin.POST("/papers/:id/review", handlers.ReviewPaper)
		admin.DELETE("/papers/:id", handlers.DeletePaper)
		admin.GET("/users", handlers.GetUsers)
		admin.PUT("/users/:id", handlers.UpdateUser)
	}

	// 健康检查
	r.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{"status": "ok"})
	})

	// 7. 反向代理：转发未匹配请求到 Python
	pyURL, _ := url.Parse("http://127.0.0.1:8000")
	proxy := httputil.NewSingleHostReverseProxy(pyURL)
	r.NoRoute(func(c *gin.Context) {
		proxy.ServeHTTP(c.Writer, c.Request)
	})

	// 8. 启动
	log.Printf("Go server starting on :%s (Python backend: 8000)", cfg.Port)
	r.Run(":" + cfg.Port) // 默认监听 0.0.0.0:8080
}
