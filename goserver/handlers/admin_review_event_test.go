package handlers

import (
	"regexp"
	"testing"
	"time"

	"scwiki/server/models"

	"github.com/DATA-DOG/go-sqlmock"
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
	paper := models.Paper{ID: 11, ReviewStatus: reviewStatusPending}
	reviewedAt := time.Date(2026, 8, 20, 10, 0, 0, 0, time.UTC)

	mock.ExpectQuery(regexp.QuoteMeta("SELECT count(*) FROM `paper_review_events` WHERE request_id = ?")).
		WithArgs("request-1").WillReturnRows(sqlmock.NewRows([]string{"count"}).AddRow(0))
	mock.ExpectBegin()
	mock.ExpectExec("UPDATE `papers` SET .* WHERE `id` = \\?").
		WithArgs("证据充分", "approved", reviewedAt, uint(7), sqlmock.AnyArg(), uint(11)).
		WillReturnResult(sqlmock.NewResult(0, 1))
	mock.ExpectCommit()
	mock.ExpectBegin()
	mock.ExpectExec("INSERT INTO `paper_review_events`").
		WithArgs(uint(11), uint(7), "approved", "证据充分", reviewedAt, "request-1", "single").
		WillReturnResult(sqlmock.NewResult(1, 1))
	mock.ExpectCommit()

	written, err := applyPaperReview(db, &paper, 7, "approved", "证据充分", "request-1", "single", reviewedAt)
	if err != nil {
		t.Fatal(err)
	}
	if !written || paper.ReviewStatus != "approved" || paper.ReviewedBy == nil || *paper.ReviewedBy != 7 {
		t.Fatalf("审核事件未正确应用: written=%v paper=%#v", written, paper)
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

	written, err := applyPaperReview(db, &paper, 7, "approved", "证据充分", "request-1", "single", time.Now())
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
	paper := models.Paper{ID: 11, ReviewStatus: "approved", ReviewComment: &comment}
	reviewedAt := time.Date(2026, 8, 20, 11, 0, 0, 0, time.UTC)

	mock.ExpectBegin()
	mock.ExpectExec("UPDATE `papers` SET .* WHERE `id` = \\?").
		WithArgs(comment, "approved", reviewedAt, uint(7), sqlmock.AnyArg(), uint(11)).
		WillReturnResult(sqlmock.NewResult(0, 1))
	mock.ExpectCommit()
	mock.ExpectBegin()
	mock.ExpectExec("INSERT INTO `paper_review_events`").
		WithArgs(uint(11), uint(7), "approved", comment, reviewedAt, nil, "single").
		WillReturnResult(sqlmock.NewResult(1, 1))
	mock.ExpectCommit()

	written, err := applyPaperReview(db, &paper, 7, "approved", comment, "", "single", reviewedAt)
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
