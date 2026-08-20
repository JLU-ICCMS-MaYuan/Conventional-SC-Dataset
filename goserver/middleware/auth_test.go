package middleware

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
)

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
	token, err := GenerateToken("reviewer@example.com")
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
