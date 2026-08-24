package handlers

import (
	"errors"
	"testing"
	"time"

	"scwiki/server/models"

	"github.com/DATA-DOG/go-sqlmock"
	mysqldriver "github.com/go-sql-driver/mysql"
)

func TestValidatePublicUsername(t *testing.T) {
	for _, value := range []string{"Alice", "alice", "A_1", "Researcher_2026"} {
		if err := validatePublicUsername(value); err != nil {
			t.Fatalf("validatePublicUsername(%q) = %v", value, err)
		}
	}
	for _, value := range []string{"ab", "1alice", "a-b", "a b", "管理员", "Admin", "ROOT", "sc_demo", "SC_demo"} {
		if err := validatePublicUsername(value); err == nil {
			t.Fatalf("validatePublicUsername(%q) should fail", value)
		}
	}
}

func TestApplySelfUsernameChangeConsumesOpportunityAtomically(t *testing.T) {
	db, mock := reviewEventTestDB(t)
	mock.ExpectBegin()
	mock.ExpectExec("UPDATE `users` SET .*username.*username_change_allowed.*").
		WillReturnResult(sqlmock.NewResult(0, 1))
	mock.ExpectCommit()

	if err := applySelfUsernameChange(db, 7, "ChosenName"); err != nil {
		t.Fatal(err)
	}
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Fatal(err)
	}
}

func TestApplySelfUsernameChangeRejectsMissingOpportunity(t *testing.T) {
	db, mock := reviewEventTestDB(t)
	mock.ExpectBegin()
	mock.ExpectExec("UPDATE `users` SET .*username.*username_change_allowed.*").
		WillReturnResult(sqlmock.NewResult(0, 0))
	mock.ExpectRollback()

	err := applySelfUsernameChange(db, 7, "ChosenName")
	if !errors.Is(err, errUsernameChangeNotAllowed) {
		t.Fatalf("error = %v", err)
	}
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Fatal(err)
	}
}

func TestApplyAdminUsernameChangeWritesAuditInSameTransaction(t *testing.T) {
	db, mock := reviewEventTestDB(t)
	target := &models.User{ID: 9, Username: "OldName", UsernameChangeAllowed: true}
	changedAt := time.Date(2026, 8, 21, 10, 0, 0, 0, time.UTC)
	mock.ExpectBegin()
	mock.ExpectExec("UPDATE `users` SET .*username.*").WillReturnResult(sqlmock.NewResult(0, 1))
	mock.ExpectExec("INSERT INTO `username_change_audit_events`").WillReturnResult(sqlmock.NewResult(1, 1))
	mock.ExpectCommit()

	if err := applyAdminUsernameChange(db, target, 1, "NewName", "修正拼写", changedAt); err != nil {
		t.Fatal(err)
	}
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Fatal(err)
	}
}

func TestApplyAdminUsernameChangeRollsBackWhenAuditFails(t *testing.T) {
	db, mock := reviewEventTestDB(t)
	target := &models.User{ID: 9, Username: "OldName"}
	mock.ExpectBegin()
	mock.ExpectExec("UPDATE `users` SET .*username.*").WillReturnResult(sqlmock.NewResult(0, 1))
	mock.ExpectExec("INSERT INTO `username_change_audit_events`").WillReturnError(errors.New("audit unavailable"))
	mock.ExpectRollback()

	if err := applyAdminUsernameChange(db, target, 1, "NewName", "修正拼写", time.Now()); err == nil {
		t.Fatal("audit failure must roll back username change")
	}
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Fatal(err)
	}
}

func TestDuplicateUsernameError(t *testing.T) {
	if !isDuplicateKeyError(&mysqldriver.MySQLError{Number: 1062, Message: "duplicate"}) {
		t.Fatal("MySQL duplicate key should map to username conflict")
	}
}

func TestGeneratedHistoricalUsernameFormat(t *testing.T) {
	seen := map[string]struct{}{}
	for i := 0; i < 100; i++ {
		value, err := generateHistoricalUsername()
		if err != nil {
			t.Fatal(err)
		}
		if len(value) != 15 || value[:3] != "sc_" {
			t.Fatalf("generated username = %q", value)
		}
		if _, exists := seen[value]; exists {
			t.Fatalf("duplicate generated username = %q", value)
		}
		seen[value] = struct{}{}
	}
}
