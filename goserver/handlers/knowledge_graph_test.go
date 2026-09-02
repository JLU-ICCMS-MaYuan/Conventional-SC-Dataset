package handlers

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"

	"scwiki/server/database"
	"scwiki/server/middleware"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

func graphTestDB(t *testing.T) *gorm.DB {
	t.Helper()
	db, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	if err != nil {
		t.Fatal(err)
	}
	if err := db.AutoMigrate(&models.Paper{}, &models.User{}, &models.PaperGraphMark{}); err != nil {
		t.Fatalf("基础表迁移失败: %v", err)
	}
	statements := []string{
		`CREATE TABLE material_families (id INTEGER PRIMARY KEY, code TEXT NOT NULL, name_zh TEXT NOT NULL, name_en TEXT, normalized_name TEXT NOT NULL)`,
		`CREATE TABLE paper_material_families (paper_id INTEGER NOT NULL, paper_revision INTEGER NOT NULL, material_family_id INTEGER NOT NULL, PRIMARY KEY (paper_id, paper_revision, material_family_id))`,
		`CREATE TABLE paper_references (id INTEGER PRIMARY KEY AUTOINCREMENT, paper_id INTEGER NOT NULL, paper_revision INTEGER NOT NULL, reference_index INTEGER NOT NULL, raw_citation TEXT NOT NULL, doi TEXT, title TEXT, normalized_title TEXT, authors TEXT, year INTEGER, cited_paper_id INTEGER, match_status TEXT NOT NULL, match_method TEXT, match_checked_at DATETIME, created_at DATETIME, updated_at DATETIME)`,
	}
	for _, statement := range statements {
		if err := db.Exec(statement).Error; err != nil {
			t.Fatalf("创建测试表失败: %v", err)
		}
	}
	previous := database.DB
	database.DB = db
	t.Cleanup(func() { database.DB = previous })
	return db
}

func graphPaper(t *testing.T, db *gorm.DB, id uint, title string, status string, kind string) {
	t.Helper()
	year := 2000 + int(id)
	approvedRevision := uint(1)
	paper := models.Paper{
		ID: id, Title: &title, Year: &year, ContentRevision: 1,
		ReviewStatus: status, SuperconductorKind: kind,
	}
	if status == "approved" {
		paper.ApprovedRevision = &approvedRevision
	}
	if err := db.Create(&paper).Error; err != nil {
		t.Fatalf("创建论文 %d 失败: %v", id, err)
	}
}

func graphReference(t *testing.T, db *gorm.DB, source, target uint, index int) {
	t.Helper()
	if err := db.Exec(`INSERT INTO paper_references
		(paper_id, paper_revision, reference_index, raw_citation, cited_paper_id, match_status)
		VALUES (?, 1, ?, 'citation', ?, 'matched')`, source, index, target).Error; err != nil {
		t.Fatalf("创建引用 %d -> %d 失败: %v", source, target, err)
	}
}

func graphResponse(t *testing.T, handler gin.HandlerFunc, path string) map[string]interface{} {
	return graphResponseAt(t, handler, "/graph", "/graph"+path)
}

func graphResponseAt(t *testing.T, handler gin.HandlerFunc, route, requestPath string) map[string]interface{} {
	t.Helper()
	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.GET(route, handler)
	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodGet, requestPath, nil)
	router.ServeHTTP(recorder, request)
	if recorder.Code != http.StatusOK {
		t.Fatalf("请求 %s 返回 HTTP %d: %s", requestPath, recorder.Code, recorder.Body.String())
	}
	var body map[string]interface{}
	if err := json.Unmarshal(recorder.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	return body
}

func graphNodesFromResponse(t *testing.T, body map[string]interface{}) []map[string]interface{} {
	t.Helper()
	raw, ok := body["nodes"].([]interface{})
	if !ok {
		t.Fatalf("nodes 不是数组: %#v", body["nodes"])
	}
	result := make([]map[string]interface{}, 0, len(raw))
	for _, item := range raw {
		result = append(result, item.(map[string]interface{}))
	}
	return result
}

func TestKGOverviewUsesApprovedCurrentPapersAndDeduplicatesCitationSources(t *testing.T) {
	db := graphTestDB(t)
	graphPaper(t, db, 1, "Origin", "approved", "conventional")
	graphPaper(t, db, 2, "Branch", "approved", "conventional")
	graphPaper(t, db, 3, "Unknown type", "approved", "unknown")
	graphPaper(t, db, 4, "Pending", "pending", "conventional")
	if err := db.Exec("INSERT INTO material_families (id, code, name_zh, normalized_name) VALUES (7, 'cu', '铜基超导体', '铜基超导体')").Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Exec("INSERT INTO paper_material_families VALUES (1, 1, 7), (2, 1, 7)").Error; err != nil {
		t.Fatal(err)
	}
	graphReference(t, db, 2, 1, 0)
	graphReference(t, db, 3, 1, 0)
	graphReference(t, db, 3, 2, 1)
	graphReference(t, db, 3, 1, 2) // 同一来源重复引文不能增加计数
	graphReference(t, db, 4, 1, 0) // 待审核来源不能算公开被引

	body := graphResponse(t, KGOverview, "?material_family_id=7&superconductor_kind=conventional")
	nodes := graphNodesFromResponse(t, body)
	if len(nodes) != 2 || body["total_nodes"] != float64(2) {
		t.Fatalf("分类筛选结果错误: %#v", body)
	}
	if nodes[0]["paper_id"] != float64(1) || nodes[0]["citation_count"] != float64(2) {
		t.Fatalf("Origin 计数/排序错误: %#v", nodes[0])
	}
	if nodes[1]["paper_id"] != float64(2) || nodes[1]["citation_count"] != float64(1) {
		t.Fatalf("Branch 计数/排序错误: %#v", nodes[1])
	}
	edges := body["edges"].([]interface{})
	if len(edges) != 1 || edges[0].(map[string]interface{})["citing_paper_id"] != float64(2) {
		t.Fatalf("概览边去重/分类错误: %#v", edges)
	}
}

func TestKGPaperNeighborsPaginatesBothDirectionsAndUsesOneNodePerPaper(t *testing.T) {
	db := graphTestDB(t)
	graphPaper(t, db, 1, "Center", "approved", "conventional")
	for id := uint(2); id <= 8; id++ {
		graphPaper(t, db, id, "Downstream "+strconv.FormatUint(uint64(id), 10), "approved", "conventional")
		graphReference(t, db, id, 1, 0)
	}
	graphPaper(t, db, 9, "Upstream", "approved", "conventional")
	graphReference(t, db, 1, 9, 0)
	graphReference(t, db, 1, 1, 1) // 原文循环事实保留，但查询不会递归

	body := graphResponseAt(t, KGPaperNeighbors, "/papers/:paperId/neighbors", "/papers/1/neighbors?direction=downstream&limit=5&offset=0")
	nodes := graphNodesFromResponse(t, body)
	if len(nodes) != 5 || body["remaining_count"] != float64(2) {
		t.Fatalf("下游分页或剩余数错误: %#v", body)
	}
	if nodes[0]["paper_id"] != float64(2) {
		t.Fatalf("下游排序错误: %#v", nodes)
	}

	body = graphResponseAt(t, KGPaperNeighbors, "/papers/:paperId/neighbors", "/papers/1/neighbors?direction=downstream&limit=5&offset=5")
	if len(graphNodesFromResponse(t, body)) != 2 || body["remaining_count"] != float64(0) {
		t.Fatalf("下游第二页错误: %#v", body)
	}

	body = graphResponseAt(t, KGPaperNeighbors, "/papers/:paperId/neighbors", "/papers/1/neighbors?direction=upstream&limit=5&offset=0")
	nodes = graphNodesFromResponse(t, body)
	if len(nodes) != 1 || nodes[0]["paper_id"] != float64(9) {
		t.Fatalf("上游方向错误: %#v", body)
	}
}

func TestKGSearchCanFindUnknownClassificationPaper(t *testing.T) {
	db := graphTestDB(t)
	graphPaper(t, db, 1, "Visible conventional paper", "approved", "conventional")
	graphPaper(t, db, 2, "Rare unknown paper", "approved", "unknown")
	body := graphResponse(t, KGSearch, "?q=Rare%20unknown")
	nodes := graphNodesFromResponse(t, body)
	if len(nodes) != 1 || nodes[0]["paper_id"] != float64(2) {
		t.Fatalf("搜索结果错误: %#v", body)
	}
}

func TestReplacePaperGraphMarksRequiresAdminAndApprovedPaper(t *testing.T) {
	db := graphTestDB(t)
	graphPaper(t, db, 1, "Approved", "approved", "conventional")
	graphPaper(t, db, 2, "Pending", "pending", "conventional")
	admin := models.User{ID: 7, Email: "admin@example.test", Username: "graph-admin", Role: "admin", IsApproved: true, AccountStatus: "active"}
	if err := db.Create(&admin).Error; err != nil {
		t.Fatal(err)
	}

	request := func(actor *models.User, paperID uint) *httptest.ResponseRecorder {
		router := gin.New()
		router.Use(func(c *gin.Context) {
			c.Set("current_user", actor)
			c.Set("user_email", actor.Email)
			c.Next()
		})
		router.PUT("/papers/:paperId/graph-marks", middleware.AdminRequired, ReplacePaperGraphMarks)
		recorder := httptest.NewRecorder()
		request := httptest.NewRequest(http.MethodPut, "/papers/"+strconv.FormatUint(uint64(paperID), 10)+"/graph-marks", strings.NewReader(`{"marks":["origin","origin","breakthrough"]}`))
		request.Header.Set("Content-Type", "application/json")
		router.ServeHTTP(recorder, request)
		return recorder
	}

	recorder := request(&admin, 1)
	if recorder.Code != http.StatusOK {
		t.Fatalf("管理员标记返回 HTTP %d: %s", recorder.Code, recorder.Body.String())
	}
	var markCount int64
	if err := db.Model(&models.PaperGraphMark{}).Where("paper_id = ?", 1).Count(&markCount).Error; err != nil {
		t.Fatal(err)
	}
	if markCount != 2 {
		t.Fatalf("标记去重失败，得到 %d 条", markCount)
	}

	normal := models.User{ID: 8, Email: "user@example.test", Username: "graph-user", Role: "user", IsApproved: true, AccountStatus: "active"}
	recorder = request(&normal, 1)
	if recorder.Code != http.StatusForbidden {
		t.Fatalf("普通用户应被管理员路由拒绝，得到 HTTP %d: %s", recorder.Code, recorder.Body.String())
	}

	recorder = request(&admin, 2)
	if recorder.Code != http.StatusConflict {
		t.Fatalf("未审核论文应返回 409，得到 HTTP %d: %s", recorder.Code, recorder.Body.String())
	}
}
