package handlers

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"scwiki/server/database"
	"scwiki/server/middleware"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

func paperHistoryTestDB(t *testing.T) *gorm.DB {
	t.Helper()
	db, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	if err != nil {
		t.Fatal(err)
	}
	if err := db.AutoMigrate(&models.User{}, &models.Paper{}, &models.PaperHistoryEvent{}); err != nil {
		t.Fatal(err)
	}
	previous := database.DB
	database.DB = db
	t.Cleanup(func() { database.DB = previous })
	return db
}

func historyUser(id uint, role string) *models.User {
	return &models.User{ID: id, Email: "user" + string(rune(id)) + "@example.test", Username: "user", Role: role}
}

func TestGetPaperHistoryRequiresAdministratorRole(t *testing.T) {
	paperHistoryTestDB(t)
	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.Use(func(c *gin.Context) {
		c.Set("current_user", historyUser(1, "user"))
		c.Next()
	})
	router.GET("/papers/:id/history", middleware.AdminRequired, GetPaperHistory)

	response := httptest.NewRecorder()
	router.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/papers/1/history", nil))
	if response.Code != http.StatusForbidden {
		t.Fatalf("普通用户状态码 = %d，期望 %d", response.Code, http.StatusForbidden)
	}
}

func TestGetPaperHistoryReturnsChronologicalEventsAndReviewComments(t *testing.T) {
	db := paperHistoryTestDB(t)
	paper := models.Paper{ID: 4, Title: strPtr("历史论文"), ReviewStatus: reviewStatusPending, ContentRevision: 2}
	if err := db.Create(&paper).Error; err != nil {
		t.Fatal(err)
	}
	reviewer := "reviewer"
	approved := reviewStatusApproved
	comment := "证据充分"
	if err := db.Create(&[]models.PaperHistoryEvent{
		{PaperID: 4, PaperRevision: 1, EventType: paperHistoryUploaded, OccurredAt: time.Date(2026, 9, 3, 9, 0, 0, 0, time.UTC)},
		{PaperID: 4, PaperRevision: 2, EventType: paperHistoryModified, ActorUsernameSnapshot: &reviewer, OccurredAt: time.Date(2026, 9, 3, 10, 0, 0, 0, time.UTC)},
		{PaperID: 4, PaperRevision: 2, EventType: paperHistoryReviewed, ActorUsernameSnapshot: &reviewer, ReviewStatus: &approved, ReviewComment: &comment, OccurredAt: time.Date(2026, 9, 3, 11, 0, 0, 0, time.UTC)},
	}).Error; err != nil {
		t.Fatal(err)
	}
	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.Use(func(c *gin.Context) {
		c.Set("current_user", historyUser(1, "superadmin"))
		c.Next()
	})
	router.GET("/papers/:id/history", middleware.AdminRequired, GetPaperHistory)

	response := httptest.NewRecorder()
	router.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/papers/4/history", nil))
	if response.Code != http.StatusOK {
		t.Fatalf("状态码 = %d，响应 = %s", response.Code, response.Body.String())
	}
	var body struct {
		PaperID uint `json:"paper_id"`
		Events  []struct {
			EventType string `json:"event_type"`
			Actor     struct {
				Username *string `json:"username"`
				Unknown  bool    `json:"unknown"`
			} `json:"actor"`
			Review *struct {
				Status  string  `json:"status"`
				Comment *string `json:"comment"`
			} `json:"review"`
		} `json:"events"`
	}
	if err := json.Unmarshal(response.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body.PaperID != 4 || len(body.Events) != 3 {
		t.Fatalf("处理记录响应 = %#v", body)
	}
	if body.Events[0].EventType != paperHistoryUploaded || !body.Events[0].Actor.Unknown || body.Events[0].Actor.Username != nil {
		t.Fatalf("未知上传事件 = %#v", body.Events[0])
	}
	if body.Events[1].EventType != paperHistoryModified || body.Events[1].Review != nil {
		t.Fatalf("修改事件 = %#v", body.Events[1])
	}
	if body.Events[2].EventType != paperHistoryReviewed || body.Events[2].Review == nil || body.Events[2].Review.Status != reviewStatusApproved || body.Events[2].Review.Comment == nil || *body.Events[2].Review.Comment != comment {
		t.Fatalf("审核事件 = %#v", body.Events[2])
	}
}
