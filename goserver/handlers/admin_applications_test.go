package handlers

import (
	"net/http"
	"testing"

	"scwiki/server/database"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

func adminApplicationTestDB(t *testing.T) *gorm.DB {
	t.Helper()
	db, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	if err != nil {
		t.Fatal(err)
	}
	if err := db.AutoMigrate(&models.User{}, &models.AdminApplication{}, &models.UserGovernanceAuditEvent{}); err != nil {
		t.Fatal(err)
	}
	database.DB = db
	return db
}

func applicationRouter(user *models.User) *gin.Engine {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.Use(func(c *gin.Context) { c.Set("current_user", user); c.Set("user_email", user.Email); c.Next() })
	router.POST("/applications", SubmitAdminApplication)
	router.POST("/applications/:id/withdraw", WithdrawAdminApplication)
	router.POST("/applications/:id/approve", ApproveAdminApplication)
	router.POST("/applications/:id/reject", RejectAdminApplication)
	return router
}

func TestAdminApplicationAllowsOnePendingAndCanWithdraw(t *testing.T) {
	db := adminApplicationTestDB(t)
	affiliation := "吉林大学"
	user := models.User{Email: "applicant@example.test", Username: "Applicant", PasswordHash: "unused", RealName: "申请人", Affiliation: &affiliation, Role: "user", AccountStatus: "active", IsApproved: true, IsEmailVerified: true}
	if err := db.Create(&user).Error; err != nil {
		t.Fatal(err)
	}
	router := applicationRouter(&user)
	first := jsonRequest(t, router, http.MethodPost, "/applications", map[string]any{})
	if first.Code != http.StatusCreated {
		t.Fatalf("first = %d %s", first.Code, first.Body.String())
	}
	second := jsonRequest(t, router, http.MethodPost, "/applications", map[string]any{})
	if second.Code != http.StatusConflict {
		t.Fatalf("second = %d", second.Code)
	}
	var application models.AdminApplication
	if err := db.First(&application).Error; err != nil {
		t.Fatal(err)
	}
	withdrawn := jsonRequest(t, router, http.MethodPost, "/applications/1/withdraw", map[string]any{})
	if withdrawn.Code != http.StatusOK {
		t.Fatalf("withdraw = %d %s", withdrawn.Code, withdrawn.Body.String())
	}
	third := jsonRequest(t, router, http.MethodPost, "/applications", map[string]any{})
	if third.Code != http.StatusCreated {
		t.Fatalf("reapply = %d %s", third.Code, third.Body.String())
	}
}

func TestApproveAdminApplicationChangesRoleAndWritesAudit(t *testing.T) {
	db := adminApplicationTestDB(t)
	affiliation := "吉林大学"
	target := models.User{Email: "target@example.test", Username: "TargetUser", PasswordHash: "unused", RealName: "申请人", Affiliation: &affiliation, Role: "user", AccountStatus: "active", IsApproved: true, IsEmailVerified: true}
	actor := models.User{Email: "root@example.test", Username: "RootAdmin", PasswordHash: "unused", Role: "superadmin", AccountStatus: "active", IsApproved: true, IsEmailVerified: true}
	if err := db.Create(&target).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&actor).Error; err != nil {
		t.Fatal(err)
	}
	guard := true
	application := models.AdminApplication{UserID: target.ID, RealNameSnapshot: target.RealName, AffiliationSnapshot: affiliation, Status: "pending", PendingGuard: &guard}
	if err := db.Create(&application).Error; err != nil {
		t.Fatal(err)
	}
	router := applicationRouter(&actor)
	approved := jsonRequest(t, router, http.MethodPost, "/applications/1/approve", map[string]any{})
	if approved.Code != http.StatusOK {
		t.Fatalf("approve = %d %s", approved.Code, approved.Body.String())
	}
	if err := db.First(&target, target.ID).Error; err != nil {
		t.Fatal(err)
	}
	if target.Role != "admin" || target.SessionVersion != 1 {
		t.Fatalf("target = %#v", target)
	}
	if err := db.First(&application, application.ID).Error; err != nil {
		t.Fatal(err)
	}
	if application.Status != "approved" || application.PendingGuard != nil {
		t.Fatalf("application = %#v", application)
	}
	var auditCount int64
	db.Model(&models.UserGovernanceAuditEvent{}).Where("target_user_id = ? AND event_type = ?", target.ID, "role_promoted").Count(&auditCount)
	if auditCount != 1 {
		t.Fatalf("audit count = %d", auditCount)
	}
}

func TestRejectAdminApplicationRequiresReason(t *testing.T) {
	db := adminApplicationTestDB(t)
	actor := models.User{Email: "root@example.test", Username: "RootAdmin", PasswordHash: "unused", Role: "superadmin", AccountStatus: "active", IsApproved: true, IsEmailVerified: true}
	if err := db.Create(&actor).Error; err != nil {
		t.Fatal(err)
	}
	response := jsonRequest(t, applicationRouter(&actor), http.MethodPost, "/applications/1/reject", map[string]string{"reason": ""})
	if response.Code != http.StatusBadRequest {
		t.Fatalf("status = %d", response.Code)
	}
}
