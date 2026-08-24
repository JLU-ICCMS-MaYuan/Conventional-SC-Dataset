package handlers

import (
	"bytes"
	"encoding/json"
	"errors"
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
	router.POST("/login", loginHandler)
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

func TestRegisterCreatesVerifiedUserWhoCanLoginWithoutEmail(t *testing.T) {
	router, mailer := identityTestRouter(t)
	registered := jsonRequest(t, router, http.MethodPost, "/register", map[string]any{
		"email": "Researcher@Example.Test", "password": "strong-pass-123", "username": "Researcher", "real_name": "研究者",
	})
	if registered.Code != http.StatusCreated {
		t.Fatalf("register = %d %s", registered.Code, registered.Body.String())
	}
	if !bytes.Contains(registered.Body.Bytes(), []byte(`"requires_email_verification":false`)) {
		t.Fatalf("register body = %s", registered.Body.String())
	}
	var user models.User
	if err := database.DB.Where("email = ?", "researcher@example.test").First(&user).Error; err != nil {
		t.Fatal(err)
	}
	if user.Role != "user" || !user.IsApproved || !user.IsEmailVerified || user.AccountStatus != "active" {
		t.Fatalf("registered user = %#v", user)
	}
	if mailer.email != "" || mailer.code != "" {
		t.Fatalf("verification email should not be sent: %q %q", mailer.email, mailer.code)
	}
	loggedIn := jsonRequest(t, router, http.MethodPost, "/login", map[string]string{"email": user.Email, "password": "strong-pass-123"})
	if loggedIn.Code != http.StatusOK || !bytes.Contains(loggedIn.Body.Bytes(), []byte("access_token")) {
		t.Fatalf("login = %d %s", loggedIn.Code, loggedIn.Body.String())
	}
}

func TestRegisterDoesNotReportGenericDatabaseFailureAsDuplicate(t *testing.T) {
	router, _ := identityTestRouter(t)
	if err := database.DB.Callback().Create().Before("gorm:create").Register("test:fail-create", func(tx *gorm.DB) {
		tx.AddError(errors.New("forced create failure"))
	}); err != nil {
		t.Fatal(err)
	}
	response := jsonRequest(t, router, http.MethodPost, "/register", map[string]any{
		"email": "failure@example.test", "password": "strong-pass-123", "username": "FailureUser",
	})
	if response.Code != http.StatusInternalServerError || !bytes.Contains(response.Body.Bytes(), []byte(`"error":"注册失败"`)) {
		t.Fatalf("register = %d %s", response.Code, response.Body.String())
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
