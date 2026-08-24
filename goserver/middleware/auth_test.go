package middleware

import (
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

func authTestUser(t *testing.T, status string, sessionVersion int64) models.User {
	return authTestUserWithRole(t, status, sessionVersion, "user")
}

func authTestUserWithRole(t *testing.T, status string, sessionVersion int64, role string) models.User {
	t.Helper()
	db, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	if err != nil {
		t.Fatal(err)
	}
	if err := db.AutoMigrate(&models.User{}); err != nil {
		t.Fatal(err)
	}
	database.DB = db
	user := models.User{Email: "reviewer@example.com", Username: "reviewer", PasswordHash: "unused", Role: role, AccountStatus: status, SessionVersion: sessionVersion, IsEmailVerified: true, IsApproved: true}
	if err := db.Where("email = ?", user.Email).Assign(user).FirstOrCreate(&user).Error; err != nil {
		t.Fatal(err)
	}
	return user
}

func roleRouter() *gin.Engine {
	router := gin.New()
	router.GET("/admin", AuthRequired, AdminRequired, func(c *gin.Context) { c.Status(http.StatusNoContent) })
	router.GET("/superadmin", AuthRequired, SuperAdminRequired, func(c *gin.Context) { c.Status(http.StatusNoContent) })
	return router
}

func requestWithUser(t *testing.T, path, role string) *httptest.ResponseRecorder {
	t.Helper()
	InitJWT("test-secret")
	user := authTestUserWithRole(t, "active", 0, role)
	token, err := GenerateTokenForUser(user)
	if err != nil {
		t.Fatal(err)
	}
	request := httptest.NewRequest(http.MethodGet, path, nil)
	request.Header.Set("Authorization", "Bearer "+token)
	response := httptest.NewRecorder()
	roleRouter().ServeHTTP(response, request)
	return response
}

func TestAdminCannotEnterSuperadminRoutes(t *testing.T) {
	if response := requestWithUser(t, "/superadmin", "admin"); response.Code != http.StatusForbidden {
		t.Fatalf("status = %d, want 403", response.Code)
	}
}

func TestSuperadminCanUseReviewAndGovernanceRoutes(t *testing.T) {
	if response := requestWithUser(t, "/admin", "superadmin"); response.Code != http.StatusNoContent {
		t.Fatalf("admin route status = %d", response.Code)
	}
	if response := requestWithUser(t, "/superadmin", "superadmin"); response.Code != http.StatusNoContent {
		t.Fatalf("superadmin route status = %d", response.Code)
	}
}

func optionalAuthRouter() *gin.Engine {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.GET("/public", OptionalAuth, func(c *gin.Context) {
		email, _ := c.Get("user_email")
		c.JSON(http.StatusOK, gin.H{"email": email})
	})
	return router
}

func TestOptionalAuthAllowsAnonymous(t *testing.T) {
	request := httptest.NewRequest(http.MethodGet, "/public", nil)
	response := httptest.NewRecorder()
	optionalAuthRouter().ServeHTTP(response, request)
	if response.Code != http.StatusOK {
		t.Fatalf("status = %d", response.Code)
	}
}

func TestOptionalAuthRejectsInvalidToken(t *testing.T) {
	InitJWT("test-secret")
	request := httptest.NewRequest(http.MethodGet, "/public", nil)
	request.Header.Set("Authorization", "Bearer invalid")
	response := httptest.NewRecorder()
	optionalAuthRouter().ServeHTTP(response, request)
	if response.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d", response.Code)
	}
}

func TestOptionalAuthSetsValidIdentity(t *testing.T) {
	InitJWT("test-secret")
	user := authTestUser(t, "active", 4)
	token, err := GenerateTokenForUser(user)
	if err != nil {
		t.Fatal(err)
	}
	request := httptest.NewRequest(http.MethodGet, "/public", nil)
	request.Header.Set("Authorization", "Bearer "+token)
	response := httptest.NewRecorder()
	optionalAuthRouter().ServeHTTP(response, request)
	if response.Code != http.StatusOK {
		t.Fatalf("status = %d", response.Code)
	}
	if !strings.Contains(response.Body.String(), "reviewer@example.com") {
		t.Fatalf("identity missing: %s", response.Body.String())
	}
}

func TestOptionalAuthRejectsRevokedSession(t *testing.T) {
	InitJWT("test-secret")
	user := authTestUser(t, "active", 2)
	token, err := GenerateTokenForUser(user)
	if err != nil {
		t.Fatal(err)
	}
	database.DB.Model(&models.User{}).Where("id = ?", user.ID).Update("session_version", 3)
	request := httptest.NewRequest(http.MethodGet, "/public", nil)
	request.Header.Set("Authorization", "Bearer "+token)
	response := httptest.NewRecorder()
	optionalAuthRouter().ServeHTTP(response, request)
	if response.Code != http.StatusUnauthorized || !strings.Contains(response.Body.String(), "session_revoked") {
		t.Fatalf("response = %d %s", response.Code, response.Body.String())
	}
}

func TestOptionalAuthRejectsBannedAccount(t *testing.T) {
	InitJWT("test-secret")
	user := authTestUser(t, "banned", 0)
	token, err := GenerateTokenForUser(user)
	if err != nil {
		t.Fatal(err)
	}
	request := httptest.NewRequest(http.MethodGet, "/public", nil)
	request.Header.Set("Authorization", "Bearer "+token)
	response := httptest.NewRecorder()
	optionalAuthRouter().ServeHTTP(response, request)
	if response.Code != http.StatusUnauthorized || !strings.Contains(response.Body.String(), "account_inactive") {
		t.Fatalf("response = %d %s", response.Code, response.Body.String())
	}
}
