package issue51tests

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"testing"

	"scwiki/server/database"
	"scwiki/server/handlers"
	"scwiki/server/middleware"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

type apiFixture struct {
	db     *gorm.DB
	router *gin.Engine
	tokens map[string]string
}

func newAPIFixture(t *testing.T) *apiFixture {
	t.Helper()
	db, err := gorm.Open(sqlite.Open(filepath.Join(t.TempDir(), "issue51.sqlite")), &gorm.Config{
		DisableForeignKeyConstraintWhenMigrating: true,
	})
	if err != nil {
		t.Fatal(err)
	}
	if err := db.AutoMigrate(
		&models.User{}, &models.Paper{}, &models.PaperHistoryEvent{},
		&models.MaterialFamily{}, &models.MaterialFamilyAlias{},
		&models.PaperMaterialFamily{},
		&models.StructureFamily{}, &models.StructureFamilyAlias{},
		&models.MaterialState{}, &models.MaterialStateStructureFamily{},
	); err != nil {
		t.Fatal(err)
	}
	previousDB := database.DB
	database.DB = db
	t.Cleanup(func() {
		database.DB = previousDB
		sqlDB, _ := db.DB()
		_ = sqlDB.Close()
	})

	python := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"ok":true}`))
	}))
	t.Setenv("PYTHON_BACKEND_URL", python.URL)
	t.Cleanup(python.Close)

	middleware.InitJWT("issue51-test-secret")
	tokens := make(map[string]string)
	for index, role := range []string{"user", "admin", "superadmin"} {
		user := models.User{
			Email: fmt.Sprintf("%s@example.com", role), Username: fmt.Sprintf("issue51_%d", index),
			Role: role, IsApproved: true, IsEmailVerified: true, AccountStatus: "active",
		}
		if err := db.Create(&user).Error; err != nil {
			t.Fatal(err)
		}
		token, err := middleware.GenerateTokenForUser(user)
		if err != nil {
			t.Fatal(err)
		}
		tokens[role] = token
	}

	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.GET("/api/classification-catalogs", handlers.GetClassificationCatalogs)
	admin := router.Group("/api/admin", middleware.AuthRequired, middleware.AdminRequired)
	admin.POST("/papers/:id/review", handlers.ReviewPaper)
	return &apiFixture{db: db, router: router, tokens: tokens}
}

func (fixture *apiFixture) request(t *testing.T, method, path, role string, body any) *httptest.ResponseRecorder {
	t.Helper()
	encoded, err := json.Marshal(body)
	if err != nil {
		t.Fatal(err)
	}
	request := httptest.NewRequest(method, path, bytes.NewReader(encoded))
	request.Header.Set("Content-Type", "application/json")
	if role != "" {
		request.Header.Set("Authorization", "Bearer "+fixture.tokens[role])
	}
	recorder := httptest.NewRecorder()
	fixture.router.ServeHTTP(recorder, request)
	return recorder
}

func seedCatalogs(t *testing.T, db *gorm.DB) (models.MaterialFamily, models.MaterialFamily, models.StructureFamily) {
	t.Helper()
	hydride := models.MaterialFamily{Code: "hydrogen_based", NameZH: "氢基超导体", NormalizedName: "氢基超导体"}
	heavy := models.MaterialFamily{Code: "heavy_fermion", NameZH: "重费米子超导体", NormalizedName: "重费米子超导体"}
	clathrate := models.StructureFamily{Code: "clathrate", NameZH: "笼状结构", NormalizedName: "笼状结构"}
	if err := db.Create(&hydride).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&heavy).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&clathrate).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&models.MaterialFamilyAlias{
		MaterialFamilyID: hydride.ID, Alias: "高压氢化物", NormalizedAlias: "高压氢化物", Language: "zh",
	}).Error; err != nil {
		t.Fatal(err)
	}
	return hydride, heavy, clathrate
}

func seedPaperState(t *testing.T, db *gorm.DB, paperID uint, revision uint, elementCount int16) models.MaterialState {
	t.Helper()
	paperType := "experimental"
	uploader := uint(99)
	title := fmt.Sprintf("Paper %d", paperID)
	paper := models.Paper{
		ID: paperID, Title: &title, PaperType: &paperType, ReviewStatus: "pending",
		ContentRevision: revision, UploadedBy: &uploader,
	}
	if err := db.Create(&paper).Error; err != nil {
		t.Fatal(err)
	}
	state := models.MaterialState{
		PaperID: paperID, PaperRevision: revision, SuperconductorID: uint(paperID),
		ElementCount: &elementCount, MaterialDimensionality: "unknown", StateKind: "experimental",
	}
	if err := db.Create(&state).Error; err != nil {
		t.Fatal(err)
	}
	return state
}

func approvedBody(requestID string, states []map[string]any) map[string]any {
	families := make([]any, 0)
	for _, state := range states {
		if family, ok := state["material_family"]; ok {
			families = append(families, family)
			delete(state, "material_family")
		}
	}
	return map[string]any{
		"status": "approved", "comment": "证据充分", "review_request_id": requestID,
		"material_families": families,
		"material_states": states,
		"classification_context": map[string]any{
			"classification_scope": []map[string]any{
				{"raw_name": "LaH10", "scope": "current_paper"},
				{"raw_name": "H3S", "scope": "referenced_work"},
			},
		},
	}
}

func TestCatalogReturnsChineseNamesAndSeedAliasesWithoutInternalCodes(t *testing.T) {
	fixture := newAPIFixture(t)
	hydride, _, _ := seedCatalogs(t, fixture.db)

	response := fixture.request(t, http.MethodGet, "/api/classification-catalogs", "", nil)
	if response.Code != http.StatusOK {
		t.Fatalf("status=%d body=%s", response.Code, response.Body.String())
	}
	var body map[string]any
	if err := json.Unmarshal(response.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	items := body["material_families"].([]any)
	first := items[0].(map[string]any)
	if first["id"] != float64(hydride.ID) || first["name"] != "氢基超导体" {
		t.Fatalf("unexpected catalog item: %#v", first)
	}
	if _, exists := first["code"]; exists {
		t.Fatal("public catalog exposed internal code")
	}
}

func TestApprovalMapsAliasesCreatesNewTermsAndStoresVerifiedSnapshot(t *testing.T) {
	fixture := newAPIFixture(t)
	hydride, _, clathrate := seedCatalogs(t, fixture.db)
	state := seedPaperState(t, fixture.db, 41, 1, 2)

	response := fixture.request(t, http.MethodPost, "/api/admin/papers/41/review", "admin", approvedBody(
		"issue51-approve-1",
		[]map[string]any{{
			"id":                      state.ID,
			"material_family":         map[string]any{"name": "高压氢化物"},
			"material_dimensionality": "three_dimensional",
			"structure_families": []map[string]any{
				{"id": clathrate.ID, "name": "ignored client label", "is_primary": true},
				{"name": "层状结构", "is_primary": false},
			},
		}},
	))
	if response.Code != http.StatusOK {
		t.Fatalf("status=%d body=%s", response.Code, response.Body.String())
	}

	fixture.db.First(&state, state.ID)
	var paperFamily models.PaperMaterialFamily
	if err := fixture.db.Where("paper_id = ? AND material_family_id = ?", 41, hydride.ID).First(&paperFamily).Error; err != nil || state.MaterialDimensionality != "three_dimensional" {
		t.Fatalf("unexpected final state: %#v", state)
	}
	var layered models.StructureFamily
	if err := fixture.db.Where("normalized_name = ?", "层状结构").First(&layered).Error; err != nil {
		t.Fatal("new structure family was not created")
	}
	var links []models.MaterialStateStructureFamily
	fixture.db.Where("material_state_id = ?", state.ID).Order("structure_family_id").Find(&links)
	if len(links) != 2 || !links[0].IsPrimary {
		t.Fatalf("unexpected structure links: %#v", links)
	}

	var event models.PaperHistoryEvent
	if err := fixture.db.Where("paper_id = ?", 41).First(&event).Error; err != nil {
		t.Fatal(err)
	}
	var snapshot map[string]any
	if err := json.Unmarshal(event.ClassificationSnapshot, &snapshot); err != nil {
		t.Fatal(err)
	}
	encoded, _ := json.Marshal(snapshot)
	text := string(encoded)
	for _, expected := range []string{"AI 建议与人工复核", "referenced_work", "氢基超导体", "笼状结构", "层状结构"} {
		if !bytes.Contains(encoded, []byte(expected)) {
			t.Fatalf("snapshot missing %s: %s", expected, text)
		}
	}
}

func TestApprovalRollsBackCreatedTermsAndStateChangesOnLaterInvalidSelection(t *testing.T) {
	fixture := newAPIFixture(t)
	seedCatalogs(t, fixture.db)
	first := seedPaperState(t, fixture.db, 42, 1, 2)
	secondCount := int16(3)
	second := models.MaterialState{
		PaperID: 42, PaperRevision: 1, SuperconductorID: 4202,
		ElementCount: &secondCount, MaterialDimensionality: "unknown", StateKind: "experimental",
	}
	if err := fixture.db.Create(&second).Error; err != nil {
		t.Fatal(err)
	}

	response := fixture.request(t, http.MethodPost, "/api/admin/papers/42/review", "admin", approvedBody(
		"issue51-rollback",
		[]map[string]any{
			{"id": first.ID, "material_family": map[string]any{"name": "应回滚的新家族"}, "material_dimensionality": "unknown"},
			{"id": second.ID, "material_family": map[string]any{"name": "另一个新家族"}, "material_dimensionality": "invalid"},
		},
	))
	if response.Code != http.StatusBadRequest {
		t.Fatalf("status=%d body=%s", response.Code, response.Body.String())
	}
	var count int64
	fixture.db.Model(&models.MaterialFamily{}).Where("name_zh IN ?", []string{"应回滚的新家族", "另一个新家族"}).Count(&count)
	if count != 0 {
		t.Fatalf("rollback left %d catalog terms", count)
	}
	var linkCount int64
	fixture.db.Model(&models.PaperMaterialFamily{}).Where("paper_id = ?", 42).Count(&linkCount)
	if linkCount != 0 {
		t.Fatalf("rollback left %d paper family links", linkCount)
	}
	var events int64
	fixture.db.Model(&models.PaperHistoryEvent{}).Where("paper_id = ?", 42).Count(&events)
	if events != 0 {
		t.Fatal("rollback left review event")
	}
}

func TestRejectedReviewDoesNotCreateOrOverwriteClassification(t *testing.T) {
	fixture := newAPIFixture(t)
	state := seedPaperState(t, fixture.db, 43, 1, 2)
	body := approvedBody("issue51-reject", []map[string]any{{
		"id": state.ID, "material_family": map[string]any{"name": "不得创建的家族"}, "material_dimensionality": "unknown",
	}})
	body["status"] = "rejected"

	response := fixture.request(t, http.MethodPost, "/api/admin/papers/43/review", "admin", body)
	if response.Code != http.StatusOK {
		t.Fatalf("status=%d body=%s", response.Code, response.Body.String())
	}
	var count int64
	fixture.db.Model(&models.MaterialFamily{}).Where("name_zh = ?", "不得创建的家族").Count(&count)
	if count != 0 {
		t.Fatal("rejected review created a catalog term")
	}
	var rejectedLinkCount int64
	fixture.db.Model(&models.PaperMaterialFamily{}).Where("paper_id = ?", 43).Count(&rejectedLinkCount)
	if rejectedLinkCount != 0 {
		t.Fatal("rejected review changed classification")
	}
}

func TestReviewRequestIDIsIdempotentBeforeCatalogCreation(t *testing.T) {
	fixture := newAPIFixture(t)
	state := seedPaperState(t, fixture.db, 44, 1, 2)
	body := approvedBody("issue51-idempotent", []map[string]any{{
		"id": state.ID, "material_family": map[string]any{"name": "幂等新家族"}, "material_dimensionality": "unknown",
	}})

	for attempt := 0; attempt < 2; attempt++ {
		response := fixture.request(t, http.MethodPost, "/api/admin/papers/44/review", "admin", body)
		if response.Code != http.StatusOK {
			t.Fatalf("attempt=%d status=%d body=%s", attempt, response.Code, response.Body.String())
		}
	}
	var terms, events int64
	fixture.db.Model(&models.MaterialFamily{}).Where("name_zh = ?", "幂等新家族").Count(&terms)
	fixture.db.Model(&models.PaperHistoryEvent{}).Where("operation_id = ?", "issue51-idempotent").Count(&events)
	if terms != 1 || events != 1 {
		t.Fatalf("terms=%d events=%d want 1/1", terms, events)
	}
}

func TestApprovalRejectsStateFromOldRevisionWithoutPartialWrites(t *testing.T) {
	fixture := newAPIFixture(t)
	seedCatalogs(t, fixture.db)
	state := seedPaperState(t, fixture.db, 45, 1, 2)
	if err := fixture.db.Model(&models.Paper{}).Where("id = ?", 45).Update("content_revision", 2).Error; err != nil {
		t.Fatal(err)
	}

	response := fixture.request(t, http.MethodPost, "/api/admin/papers/45/review", "admin", approvedBody(
		"issue51-old-revision",
		[]map[string]any{{
			"id": state.ID, "material_family": map[string]any{"name": "旧版本新家族"}, "material_dimensionality": "unknown",
		}},
	))
	if response.Code != http.StatusNotFound {
		t.Fatalf("status=%d body=%s", response.Code, response.Body.String())
	}
	var count int64
	fixture.db.Model(&models.MaterialFamily{}).Where("name_zh = ?", "旧版本新家族").Count(&count)
	if count != 0 {
		t.Fatal("old revision request created a catalog term")
	}
}
