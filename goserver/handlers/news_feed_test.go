package handlers

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	"github.com/gin-gonic/gin"
	"gorm.io/driver/mysql"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
	"scwiki/server/database"
	"scwiki/server/models"
)

func newsTestDB(t *testing.T) *gorm.DB {
	t.Helper()
	db, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	if err != nil {
		t.Fatal(err)
	}
	sqlDB, _ := db.DB()
	sqlDB.SetMaxOpenConns(1)
	old := database.DB
	database.DB = db
	t.Cleanup(func() { database.DB = old; sqlDB.Close() })
	if err := db.AutoMigrate(&models.NewsFeedItem{}, &models.NewsFeedSource{}, &models.NewsItem{}); err != nil {
		t.Fatal(err)
	}
	return db
}

func newsRequest(path string) *httptest.ResponseRecorder {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.GET("/api/news/feed", ListNewsFeed)
	router.GET("/api/news", ListNews)
	result := httptest.NewRecorder()
	router.ServeHTTP(result, httptest.NewRequest(http.MethodGet, path, nil))
	return result
}

func TestNewsFeedPaginationAndKinds(t *testing.T) {
	db := newsTestDB(t)
	for _, item := range []models.NewsFeedItem{
		{ID: "a", Kind: "preprint", Title: "Older", PublishedAt: "2026-08-29T00:00:00Z", Authors: "[]", Links: "[]"},
		{ID: "b", Kind: "preprint", Title: "Newer", PublishedAt: "2026-08-30T00:00:00Z", Authors: "[]", Links: "[]"},
		{ID: "c", Kind: "news", Title: "News", PublishedAt: "2026-08-31T00:00:00Z", Authors: "[]", Links: "[]"},
	} {
		if err := db.Create(&item).Error; err != nil {
			t.Fatal(err)
		}
	}
	response := newsRequest("/api/news/feed?kind=preprint&page=2&page_size=1")
	if response.Code != 200 {
		t.Fatalf("%d %s", response.Code, response.Body.String())
	}
	var body struct {
		Items []struct {
			ID      string
			Notice  string
			Authors []string
		}
		Total   int
		Sources []struct {
			Source string
			Status string
		}
	}
	if err := json.Unmarshal(response.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body.Total != 2 || len(body.Items) != 1 || body.Items[0].ID != "a" {
		t.Fatalf("%+v", body)
	}
	if body.Items[0].Notice != "自动采集，未经本站审核" || len(body.Sources) != 3 || body.Sources[0].Status != "never" {
		t.Fatalf("%+v", body)
	}
}

func TestNewsFeedBadParametersAndDatabaseErrors(t *testing.T) {
	db := newsTestDB(t)
	for _, query := range []string{"?page=0", "?page=-1", "?page=wat", "?page=10001", "?page_size=101", "?kind=all"} {
		if response := newsRequest("/api/news/feed" + query); response.Code != 400 {
			t.Fatalf("%s: %d", query, response.Code)
		}
	}
	if response := newsRequest("/api/news"); response.Code != 200 || response.Body.String() != "[]" {
		t.Fatalf("%d %s", response.Code, response.Body.String())
	}
	sqlDB, _ := db.DB()
	sqlDB.Close()
	for _, path := range []string{"/api/news/feed", "/api/news"} {
		response := newsRequest(path)
		if response.Code != 500 {
			t.Fatalf("%s: %d", path, response.Code)
		}
	}
}

// 可选：读取同一隔离 MySQL，验证 Python 写入与 Go 读取的真实契约。
func TestNewsFeedMySQLContract(t *testing.T) {
	dsn := os.Getenv("NEWS_TEST_MYSQL_DSN")
	if dsn == "" {
		t.Skip("需要显式测试 MySQL DSN")
	}
	db, err := gorm.Open(mysql.Open(dsn), &gorm.Config{})
	if err != nil {
		t.Fatal(err)
	}
	old := database.DB
	database.DB = db
	sqlDB, _ := db.DB()
	t.Cleanup(func() { database.DB = old; sqlDB.Close() })
	response := newsRequest("/api/news/feed")
	if response.Code != 200 {
		t.Fatalf("%d %s", response.Code, response.Body.String())
	}
	var result struct {
		Items []newsFeedView
		Total int
	}
	if err := json.Unmarshal(response.Body.Bytes(), &result); err != nil {
		t.Fatal(err)
	}
	if result.Total < 1 || len(result.Items) == 0 {
		t.Fatal("未读到 Python 写入的资讯")
	}
	for _, item := range result.Items {
		if item.Notice == "" || item.URL == "" {
			t.Fatalf("契约缺字段: %+v", item)
		}
	}
}

// 仅供本地浏览器验证。生产路由有分支既有编译问题时，不伪称已验证完整服务。
func TestNewsFeedBrowserPreview(t *testing.T) {
	address := os.Getenv("NEWS_TEST_PREVIEW_ADDRESS")
	if address == "" {
		t.Skip("未启用临时预览")
	}
	dsn := os.Getenv("NEWS_TEST_MYSQL_DSN")
	if dsn == "" {
		t.Fatal("预览只允许显式测试数据库")
	}
	db, err := gorm.Open(mysql.Open(dsn), &gorm.Config{})
	if err != nil {
		t.Fatal(err)
	}
	database.DB = db
	router := gin.New()
	router.GET("/api/news/feed", ListNewsFeed)
	router.GET("/api/news", func(c *gin.Context) {
		c.JSON(200, []models.NewsItem{{ID: 1, Title: "人工快讯（隔离测试样本）", EventDate: "2026-08-31", Summary: "用于检查人工快讯与自动资讯并存，不写入业务数据库。"}})
	})
	router.Static("/assets", "/preview/assets")
	router.GET("/news", func(c *gin.Context) { c.File("/preview/index.html") })
	t.Fatal(http.ListenAndServe(address, router))
}
