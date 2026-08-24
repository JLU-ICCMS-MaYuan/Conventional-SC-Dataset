package handlers

import (
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"scwiki/server/database"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

func governanceTestDB(t *testing.T) *gorm.DB {
	t.Helper()
	db, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	if err != nil {
		t.Fatal(err)
	}
	if err := db.AutoMigrate(&models.User{}); err != nil {
		t.Fatal(err)
	}
	database.DB = db
	return db
}

func createGovernanceUser(t *testing.T, db *gorm.DB, username, role, status string) models.User {
	t.Helper()
	user := models.User{Email: strings.ToLower(username) + "@example.test", Username: username, PasswordHash: "unused", Role: role, AccountStatus: status, IsApproved: true, IsEmailVerified: true}
	if err := db.Create(&user).Error; err != nil {
		t.Fatal(err)
	}
	return user
}

func TestLastActiveSuperadminCannotBeRemoved(t *testing.T) {
	db := governanceTestDB(t)
	first := createGovernanceUser(t, db, "FirstSuper", "superadmin", "active")
	if err := ensureCanRemoveSuperadmin(db, first); !errors.Is(err, errLastSuperadmin) {
		t.Fatalf("last superadmin error = %v", err)
	}
	createGovernanceUser(t, db, "SecondSuper", "superadmin", "active")
	if err := ensureCanRemoveSuperadmin(db, first); err != nil {
		t.Fatalf("two superadmins should be safe: %v", err)
	}
}

func TestPublicProfileUsesExplicitWhitelistAndStatusMapping(t *testing.T) {
	db := governanceTestDB(t)
	affiliation, orcid := "吉林大学", "0000-0002-1825-0097"
	interests, _ := json.Marshal([]string{"超导", "机器学习"})
	user := createGovernanceUser(t, db, "PublicAdmin", "admin", "banned")
	if err := db.Model(&user).Updates(map[string]any{"real_name": "公开姓名", "affiliation": affiliation, "orcid": orcid, "research_interests": interests}).Error; err != nil {
		t.Fatal(err)
	}
	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.GET("/users/:username", GetPublicProfile)
	response := httptest.NewRecorder()
	router.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/users/PublicAdmin", nil))
	if response.Code != http.StatusOK {
		t.Fatalf("profile = %d %s", response.Code, response.Body.String())
	}
	body := response.Body.String()
	for _, expected := range []string{"公开姓名", "吉林大学", "超导", "管理员", `"is_banned":true`} {
		if !strings.Contains(body, expected) {
			t.Fatalf("missing %q in %s", expected, body)
		}
	}
	for _, forbidden := range []string{"example.test", "password_hash", "session_version", "is_email_verified"} {
		if strings.Contains(body, forbidden) {
			t.Fatalf("public profile leaked %q: %s", forbidden, body)
		}
	}
}

func TestDeactivatedProfileIsNotPublished(t *testing.T) {
	db := governanceTestDB(t)
	createGovernanceUser(t, db, "GoneUser", "user", "deactivated")
	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.GET("/users/:username", GetPublicProfile)
	response := httptest.NewRecorder()
	router.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/users/GoneUser", nil))
	if response.Code != http.StatusNotFound {
		t.Fatalf("status = %d", response.Code)
	}
}
