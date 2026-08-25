package handlers

import (
	"bytes"
	"net/http"
	"net/http/httptest"
	"regexp"
	"testing"
	"time"

	"scwiki/server/cache"
	"scwiki/server/database"
	"scwiki/server/models"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/alicebob/miniredis/v2"
	"github.com/gin-gonic/gin"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

func reviewEventTestDB(t *testing.T) (*gorm.DB, sqlmock.Sqlmock) {
	t.Helper()
	sqlDB, mock, err := sqlmock.New()
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = sqlDB.Close() })
	db, err := gorm.Open(mysql.New(mysql.Config{
		Conn: sqlDB, SkipInitializeWithVersion: true,
	}), &gorm.Config{})
	if err != nil {
		t.Fatal(err)
	}
	return db, mock
}

func TestApplyPaperReviewWritesOneImmutableEvent(t *testing.T) {
	db, mock := reviewEventTestDB(t)
	paper := models.Paper{ID: 11, ContentRevision: 3, ReviewStatus: reviewStatusPending}
	reviewedAt := time.Date(2026, 8, 20, 10, 0, 0, 0, time.UTC)

	mock.ExpectQuery(regexp.QuoteMeta("SELECT count(*) FROM `paper_review_events` WHERE request_id = ?")).
		WithArgs("request-1").WillReturnRows(sqlmock.NewRows([]string{"count"}).AddRow(0))
	mock.ExpectBegin()
	mock.ExpectExec("UPDATE `papers` SET .* WHERE `id` = \\?").
		WithArgs(uint(3), "证据充分", "approved", reviewedAt, uint(7), sqlmock.AnyArg(), uint(11)).
		WillReturnResult(sqlmock.NewResult(0, 1))
	mock.ExpectCommit()
	mock.ExpectBegin()
	mock.ExpectExec("INSERT INTO `paper_review_events`").
		WithArgs(uint(11), uint(3), uint(7), "approved", "证据充分", reviewedAt, "request-1", "single").
		WillReturnResult(sqlmock.NewResult(1, 1))
	mock.ExpectCommit()

	written, err := applyPaperReview(db, &paper, 7, "approved", "证据充分", "request-1", "single", reviewedAt, nil)
	if err != nil {
		t.Fatal(err)
	}
	if !written || paper.ReviewStatus != "approved" || paper.ReviewedBy == nil || *paper.ReviewedBy != 7 {
		t.Fatalf("审核事件未正确应用: written=%v paper=%#v", written, paper)
	}
	if paper.ApprovedRevision == nil || *paper.ApprovedRevision != 3 {
		t.Fatalf("approved_revision = %#v, want 3", paper.ApprovedRevision)
	}
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Fatal(err)
	}
}

func TestApplyPaperReviewIgnoresRetriedRequest(t *testing.T) {
	db, mock := reviewEventTestDB(t)
	paper := models.Paper{ID: 11, ReviewStatus: reviewStatusPending}
	mock.ExpectQuery(regexp.QuoteMeta("SELECT count(*) FROM `paper_review_events` WHERE request_id = ?")).
		WithArgs("request-1").WillReturnRows(sqlmock.NewRows([]string{"count"}).AddRow(1))

	written, err := applyPaperReview(db, &paper, 7, "approved", "证据充分", "request-1", "single", time.Now(), nil)
	if err != nil {
		t.Fatal(err)
	}
	if written {
		t.Fatal("相同 request_id 的重试不应重复计数")
	}
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Fatal(err)
	}
}

func TestApplyPaperReviewCountsUnchangedReviewAsNewParticipation(t *testing.T) {
	db, mock := reviewEventTestDB(t)
	comment := "证据充分"
	paper := models.Paper{ID: 11, ContentRevision: 3, ReviewStatus: "approved", ReviewComment: &comment}
	reviewedAt := time.Date(2026, 8, 20, 11, 0, 0, 0, time.UTC)

	mock.ExpectBegin()
	mock.ExpectExec("UPDATE `papers` SET .* WHERE `id` = \\?").
		WithArgs(uint(3), comment, "approved", reviewedAt, uint(7), sqlmock.AnyArg(), uint(11)).
		WillReturnResult(sqlmock.NewResult(0, 1))
	mock.ExpectCommit()
	mock.ExpectBegin()
	mock.ExpectExec("INSERT INTO `paper_review_events`").
		WithArgs(uint(11), uint(3), uint(7), "approved", comment, reviewedAt, nil, "single").
		WillReturnResult(sqlmock.NewResult(1, 1))
	mock.ExpectCommit()

	written, err := applyPaperReview(db, &paper, 7, "approved", comment, "", "single", reviewedAt, nil)
	if err != nil {
		t.Fatal(err)
	}
	if !written {
		t.Fatal("同一论文的每次实际审核都应计入审核人贡献")
	}
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Fatal(err)
	}
}

func TestReviewPaperCommitsBeforeReviewArtifactCleanupFailure(t *testing.T) {
	db, mock := reviewEventTestDB(t)
	previousDB := database.DB
	database.DB = db
	t.Cleanup(func() { database.DB = previousDB })

	redisServer := miniredis.RunT(t)
	cache.Connect(redisServer.Addr())

	cleanupCalled := false
	pythonServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		cleanupCalled = true
		if r.Method != http.MethodDelete || r.URL.Path != "/api/rag/papers/42/review-artifact" {
			t.Fatalf("unexpected cleanup request: %s %s", r.Method, r.URL.Path)
		}
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer pythonServer.Close()
	t.Setenv("PYTHON_BACKEND_URL", pythonServer.URL)

	paperRows := func(status string) *sqlmock.Rows {
		return sqlmock.NewRows([]string{
			"id", "content_revision", "review_status", "uploaded_by_user_id",
		}).AddRow(42, 1, status, 99)
	}
	mock.ExpectQuery("SELECT \\* FROM `papers`").
		WillReturnRows(paperRows(reviewStatusPending))
	mock.ExpectQuery("SELECT \\* FROM `users`").
		WillReturnRows(sqlmock.NewRows([]string{"id", "email"}).AddRow(7, "admin@example.com"))
	mock.ExpectBegin()
	mock.ExpectQuery("SELECT \\* FROM `papers`").
		WillReturnRows(paperRows(reviewStatusPending))
	mock.ExpectExec("UPDATE `papers` SET").
		WillReturnResult(sqlmock.NewResult(0, 1))
	mock.ExpectExec("INSERT INTO `paper_review_events`").
		WillReturnResult(sqlmock.NewResult(1, 1))
	mock.ExpectCommit()
	mock.ExpectQuery("SELECT \\* FROM `papers`").
		WillReturnRows(paperRows(reviewStatusRejected))

	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.POST("/api/admin/papers/:id/review", func(c *gin.Context) {
		c.Set("user_email", "admin@example.com")
		ReviewPaper(c)
	})
	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(
		http.MethodPost,
		"/api/admin/papers/42/review",
		bytes.NewBufferString(`{"status":"rejected","comment":"证据不足"}`),
	)
	request.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusBadGateway {
		t.Fatalf("status = %d, want %d; body=%s", recorder.Code, http.StatusBadGateway, recorder.Body.String())
	}
	if !cleanupCalled {
		t.Fatal("审核事务提交后应调用临时证据清理")
	}
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Fatal(err)
	}
}
