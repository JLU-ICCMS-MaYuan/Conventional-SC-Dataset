package handlers

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"reflect"
	"testing"

	"scwiki/server/database"
	"scwiki/server/middleware"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
)

// 覆盖真实处理器、角色守卫、文本列落库和详情读取，防止前端列表被双重编码。
func TestAdminPaperListFields(t *testing.T) {
	previous := database.DB
	t.Cleanup(func() { database.DB = previous })
	db := paperDetailTestDB(t)
	if err := db.AutoMigrate(&models.PaperHistoryEvent{}); err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&models.Paper{ID: 88, Title: strPtr("Mercury"), ContentRevision: 1, ReviewStatus: "pending"}).Error; err != nil {
		t.Fatal(err)
	}
	middleware.InitJWT("admin-paper-list-fields-test")
	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.PUT("/api/admin/papers/:id", middleware.AuthRequired, middleware.AdminRequired, UpdatePaper)
	router.GET("/api/admin/papers/:id", middleware.AuthRequired, middleware.AdminRequired, GetPaperDetail)

	for _, role := range []string{"admin", "superadmin"} {
		t.Run(role, func(t *testing.T) {
			actor := models.User{Email: role + "@example.test", Username: role, Role: role, AccountStatus: "active"}
			if err := db.Create(&actor).Error; err != nil {
				t.Fatal(err)
			}
			token, err := middleware.GenerateTokenForUser(actor)
			if err != nil {
				t.Fatal(err)
			}
			for _, empty := range []bool{false, true} {
				values := map[string][]string{
					"authors":       {"Doe, Jane", "张三"},
					"keywords_tags": {"mercury", "[FeSe]"},
					"methodology":   {"Resistance, cooling", "Compare \"zero\" resistance"},
				}
				body := map[string]string{}
				for field, items := range values {
					if empty {
						items = []string{}
						values[field] = items
					}
					encoded, _ := json.Marshal(items)
					body[field] = string(encoded)
				}
				raw, _ := json.Marshal(body)
				request := httptest.NewRequest(http.MethodPut, "/api/admin/papers/88", bytes.NewReader(raw))
				request.Header.Set("Content-Type", "application/json")
				request.Header.Set("Authorization", "Bearer "+token)
				response := httptest.NewRecorder()
				router.ServeHTTP(response, request)
				if response.Code != http.StatusOK {
					t.Fatalf("保存失败：%d %s", response.Code, response.Body.String())
				}
				var persisted models.Paper
				if err := db.First(&persisted, 88).Error; err != nil {
					t.Fatal(err)
				}
				for field, value := range map[string]*string{
					"authors": persisted.Authors, "keywords_tags": persisted.KeywordsTags, "methodology": persisted.Methodology,
				} {
					var items []string
					if value == nil || json.Unmarshal([]byte(*value), &items) != nil || !reflect.DeepEqual(items, values[field]) {
						t.Fatalf("%s 未按列表文本完整持久化：%v", field, value)
					}
				}
				request = httptest.NewRequest(http.MethodGet, "/api/admin/papers/88", nil)
				request.Header.Set("Authorization", "Bearer "+token)
				response = httptest.NewRecorder()
				router.ServeHTTP(response, request)
				if response.Code != http.StatusOK {
					t.Fatalf("重载失败：%s", response.Body.String())
				}
				var detail map[string]interface{}
				if err := json.Unmarshal(response.Body.Bytes(), &detail); err != nil {
					t.Fatal(err)
				}
				for field, value := range body {
					if detail[field] != value {
						t.Fatalf("%s 重载值 = %v，期望 %s", field, detail[field], value)
					}
				}
			}
		})
	}
}
