package handlers

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"scwiki/server/cache"
	"scwiki/server/database"
	"scwiki/server/middleware"
	"scwiki/server/models"

	"github.com/alicebob/miniredis/v2"
	"github.com/gin-gonic/gin"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

type verificationFakeMailer struct {
	email string
	code  string
	err   error
}

func (mailer *verificationFakeMailer) SendVerificationCode(email, code string) error {
	mailer.email, mailer.code = email, code
	return mailer.err
}

func identityTestRouter(t *testing.T) (*gin.Engine, *verificationFakeMailer) {
	t.Helper()
	db, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	if err != nil {
		t.Fatal(err)
	}
	if err := db.AutoMigrate(&models.User{}); err != nil {
		t.Fatal(err)
	}
	database.DB = db
	redisServer := miniredis.RunT(t)
	cache.Connect(redisServer.Addr())
	mailer := &verificationFakeMailer{}
	authMailer = mailer
	verificationSecret = []byte("identity-test-secret")
	middleware.InitJWT("identity-test-secret")
	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.POST("/register", registerHandler)
	router.POST("/verify", VerifyEmail)
	return router, mailer
}

func jsonRequest(t *testing.T, router *gin.Engine, method, path string, body any) *httptest.ResponseRecorder {
	t.Helper()
	data, err := json.Marshal(body)
	if err != nil {
		t.Fatal(err)
	}
	request := httptest.NewRequest(method, path, bytes.NewReader(data))
	request.Header.Set("Content-Type", "application/json")
	response := httptest.NewRecorder()
	router.ServeHTTP(response, request)
	return response
}

func TestRegisterCreatesUserAndVerificationAutoLogsIn(t *testing.T) {
	router, mailer := identityTestRouter(t)
	registered := jsonRequest(t, router, http.MethodPost, "/register", map[string]any{
		"email": "Researcher@Example.Test", "password": "strong-pass-123", "username": "Researcher", "real_name": "研究者",
	})
	if registered.Code != http.StatusAccepted {
		t.Fatalf("register = %d %s", registered.Code, registered.Body.String())
	}
	var user models.User
	if err := database.DB.Where("email = ?", "researcher@example.test").First(&user).Error; err != nil {
		t.Fatal(err)
	}
	if user.Role != "user" || !user.IsApproved || user.IsEmailVerified || user.AccountStatus != "active" {
		t.Fatalf("registered user = %#v", user)
	}
	if mailer.email != user.Email || len(mailer.code) != 6 {
		t.Fatalf("mail = %q %q", mailer.email, mailer.code)
	}

	verified := jsonRequest(t, router, http.MethodPost, "/verify", map[string]string{"email": user.Email, "code": mailer.code})
	if verified.Code != http.StatusOK || !bytes.Contains(verified.Body.Bytes(), []byte("access_token")) {
		t.Fatalf("verify = %d %s", verified.Code, verified.Body.String())
	}
	if err := database.DB.First(&user, user.ID).Error; err != nil {
		t.Fatal(err)
	}
	if !user.IsEmailVerified {
		t.Fatal("email should be verified")
	}
	reused := jsonRequest(t, router, http.MethodPost, "/verify", map[string]string{"email": user.Email, "code": mailer.code})
	if reused.Code != http.StatusBadRequest {
		t.Fatalf("reused code = %d", reused.Code)
	}
}

func TestVerificationSendRateLimit(t *testing.T) {
	redisServer := miniredis.RunT(t)
	cache.Connect(redisServer.Addr())
	for attempt := 1; attempt <= 5; attempt++ {
		if retry, err := checkSendLimits("rate@example.test", "192.0.2.1"); err != nil || retry != 0 {
			t.Fatalf("attempt %d = retry %d, error %v", attempt, retry, err)
		}
	}
	if retry, err := checkSendLimits("rate@example.test", "192.0.2.1"); err != nil || retry == 0 {
		t.Fatalf("sixth attempt = retry %d, error %v", retry, err)
	}
}
