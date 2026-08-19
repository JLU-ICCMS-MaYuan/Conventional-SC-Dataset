package main

import (
	"compress/gzip"
	"io"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"
	"time"

	"scwiki/server/config"
	"scwiki/server/database"
	"scwiki/server/handlers"
	"scwiki/server/middleware"

	"github.com/gin-gonic/gin"
)

// gzipMiddleware 对大于 1KB 的 JSON/HTML 响应启用 gzip 压缩
func gzipMiddleware(c *gin.Context) {
	if !strings.Contains(c.GetHeader("Accept-Encoding"), "gzip") {
		c.Next()
		return
	}
	c.Writer.Header().Set("Content-Encoding", "gzip")
	c.Writer.Header().Del("Content-Length")

	gz := gzip.NewWriter(c.Writer)
	defer gz.Close()

	c.Writer = &gzipWriter{ResponseWriter: c.Writer, Writer: gz}
	c.Next()
}

type gzipWriter struct {
	gin.ResponseWriter
	Writer io.Writer
}

func (w *gzipWriter) Write(data []byte) (int, error) {
	w.Header().Del("Content-Length")
	return w.Writer.Write(data)
}

func (w *gzipWriter) WriteHeader(code int) {
	w.Header().Del("Content-Length")
	w.ResponseWriter.WriteHeader(code)
}

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

	// 5. 加载知识图谱数据
	handlers.LoadGraph(cfg.DataDir + "/graph.json")

	// 6. 注册路由
	// Gzip 压缩
	r.Use(gzipMiddleware)

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
	r.POST("/api/auth/register", handlers.Register)

	// 论文公开 API（替代 Python /api/papers/*）
	papers := r.Group("/api/papers")
	{
		papers.GET("/:id", handlers.GetPaper)
		papers.POST("/search/records", handlers.SearchRecords)
		papers.POST("/search/all", handlers.SearchAll)
	}

	// 知识图谱 API（替代 Python /api/knowledge-graph/*）
	kg := r.Group("/api/knowledge-graph")
	{
		kg.GET("/overview", handlers.KGOverview)
		kg.GET("/papers/:paper_id", handlers.KGPaperDetail)
		kg.GET("/papers/:paper_id/neighbors", handlers.KGNeighbors)
		kg.GET("/stats", handlers.KGGraphStats)
	}

	// 外部数据源 API（替代 Python /api/alexandria/* + /api/htsc2025/*）
	r.POST("/api/alexandria/search", handlers.SearchAlexandria)
	r.POST("/api/htsc2025/search", handlers.SearchHTSC)

	// 图表组合 API（替代 Python /api/chart-groups/*）
	cg := r.Group("/api/chart-groups")
	{
		cg.GET("", handlers.ListChartGroups)
		cg.GET("/:id", handlers.GetChartGroup)
		cg.POST("", handlers.CreateChartGroup)
		cg.PUT("/:id", handlers.UpdateChartGroup)
		cg.DELETE("/:id", handlers.DeleteChartGroup)
		cg.PATCH("/:id/public", handlers.ToggleChartGroupPublic)
	}

	// 快讯 API
	r.GET("/api/news", handlers.ListNews)
	// 认证路由组（普通用户可访问，仅需登录）
	auth := r.Group("/api")
	auth.Use(middleware.AuthRequired)
	{
		auth.GET("/papers/my-uploads", handlers.GetMyUploads)
		auth.GET("/papers/my-uploads/:id", handlers.GetMyUploadDetail)
	}

	// 管理员路由组
	admin := r.Group("/api/admin")
	admin.Use(middleware.AuthRequired, middleware.AdminRequired)
	{
		admin.GET("/papers/all", handlers.GetPapers)
		admin.GET("/papers/:id", handlers.GetPaperDetail)
		admin.PUT("/papers/:id", handlers.UpdatePaper)
		admin.POST("/papers/:id/review", handlers.ReviewPaper)
		admin.DELETE("/papers/:id", handlers.DeletePaper)
		admin.POST("/papers/batch-review", handlers.BatchReview)
		admin.POST("/papers/batch-delete", handlers.BatchDelete)
		admin.GET("/users", handlers.GetUsers)
		admin.PUT("/users/:id", handlers.UpdateUser)
		admin.PUT("/users/:id/permissions", handlers.UpdateUser)
		admin.DELETE("/users/:id", handlers.DeleteUser)
		admin.GET("/all-users", handlers.AllUsers)
		admin.GET("/stats", handlers.GetStats)
		admin.POST("/news", handlers.CreateNews)
		admin.PUT("/news/:id", handlers.UpdateNews)
		admin.DELETE("/news/:id", handlers.DeleteNews)
	}

	// 统计 API
	r.GET("/api/papers/stats/tc-pressure", handlers.TcPressureChart)
	r.GET("/api/papers/stats/tc-year", handlers.TcYearChart)
	r.GET("/api/papers/stats/chart-data", handlers.TcPressureChart)

	// 健康检查
	r.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{"status": "ok"})
	})

	// 7. 反向代理：转发未匹配请求到 Python（配置连接池）
	pyURL, _ := url.Parse(cfg.PythonBackend)
	proxy := httputil.NewSingleHostReverseProxy(pyURL)
	proxy.Transport = &http.Transport{
		MaxIdleConns:          100,
		MaxIdleConnsPerHost:   100,
		MaxConnsPerHost:       200,
		IdleConnTimeout:       90 * time.Second,
		ResponseHeaderTimeout: 30 * time.Second,
	}
	r.NoRoute(func(c *gin.Context) {
		proxy.ServeHTTP(c.Writer, c.Request)
	})

	// 8. 启动
	log.Printf("Go server starting on :%s (Python backend: 8000)", cfg.Port)
	r.Run(":" + cfg.Port) // 默认监听 0.0.0.0:8080
}
