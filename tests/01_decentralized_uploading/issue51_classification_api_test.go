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
	dsn := filepath.Join(t.TempDir(), "issue51.sqlite")
	db, err := gorm.Open(sqlite.Open(dsn), &gorm.Config{DisableForeignKeyConstraintWhenMigrating: true})
	if err != nil {
		t.Fatal(err)
	}
	if err := db.AutoMigrate(
		&models.User{}, &models.Paper{}, &models.PaperReviewEvent{},
		&models.MaterialFamily{}, &models.MaterialFamilyAlias{},
		&models.StructureFamily{}, &models.StructureFamilyAlias{},
		&models.MaterialState{}, &models.MaterialStateStructureFamily{},
		&models.ClassificationProposal{}, &models.ClassificationEvidence{},
		&models.ClassificationAuditEvent{},
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
	admin.GET("/classification-proposals", handlers.ListClassificationProposals)
	admin.POST("/classification-proposals/:id/map", handlers.MapClassificationProposal)
	admin.POST("/papers/:id/review", handlers.ReviewPaper)
	super := router.Group("/api/superadmin", middleware.AuthRequired, middleware.SuperAdminRequired)
	super.POST("/classification-catalogs/:dimension", handlers.CreateClassificationCatalogTerm)
	super.PATCH("/classification-catalogs/:dimension/:id", handlers.UpdateClassificationCatalogTerm)
	super.POST("/classification-catalogs/:dimension/:id/merge", handlers.MergeClassificationCatalogTerm)
	super.POST("/classification-proposals/:id/resolve", handlers.ResolveClassificationProposal)
	super.GET("/classification-audits", handlers.ListClassificationAudits)
	return &apiFixture{db: db, router: router, tokens: tokens}
}

func (fixture *apiFixture) request(t *testing.T, method, path, role string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var payload *bytes.Reader
	if body == nil {
		payload = bytes.NewReader(nil)
	} else {
		encoded, err := json.Marshal(body)
		if err != nil {
			t.Fatal(err)
		}
		payload = bytes.NewReader(encoded)
	}
	request := httptest.NewRequest(method, path, payload)
	request.Header.Set("Content-Type", "application/json")
	if role != "" {
		request.Header.Set("Authorization", "Bearer "+fixture.tokens[role])
	}
	recorder := httptest.NewRecorder()
	fixture.router.ServeHTTP(recorder, request)
	return recorder
}

func seedCatalogs(t *testing.T, db *gorm.DB) (models.MaterialFamily, models.MaterialFamily, models.StructureFamily, models.StructureFamily) {
	t.Helper()
	hydride := models.MaterialFamily{Code: "hydrogen_based", NameZH: "氢基超导体", NameEN: "Hydrogen-based", NormalizedName: "氢基超导体", IsActive: true}
	heavy := models.MaterialFamily{Code: "heavy_fermion", NameZH: "重费米子超导体", NameEN: "Heavy fermion", NormalizedName: "重费米子超导体", IsActive: true}
	clathrate := models.StructureFamily{Code: "clathrate", NameZH: "笼状结构", NameEN: "Clathrate", NormalizedName: "笼状结构", IsActive: true}
	layered := models.StructureFamily{Code: "layered", NameZH: "层状结构", NameEN: "Layered", NormalizedName: "层状结构", IsActive: true}
	if err := db.Create(&hydride).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&heavy).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&clathrate).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&layered).Error; err != nil {
		t.Fatal(err)
	}
	return hydride, heavy, clathrate, layered
}

func TestCatalogOnlyReturnsActivePublicTermsAndRoleBoundaries(t *testing.T) {
	fixture := newAPIFixture(t)
	hydride, _, clathrate, _ := seedCatalogs(t, fixture.db)
	inactive := models.MaterialFamily{Code: "inactive", NameZH: "停用项", NameEN: "Inactive", NormalizedName: "停用项", IsActive: false}
	if err := fixture.db.Create(&inactive).Error; err != nil {
		t.Fatal(err)
	}
	if err := fixture.db.Model(&inactive).Update("is_active", false).Error; err != nil {
		t.Fatal(err)
	}
	if err := fixture.db.Create(&models.MaterialFamilyAlias{MaterialFamilyID: hydride.ID, Alias: "hydride", NormalizedAlias: "hydride", Language: "en"}).Error; err != nil {
		t.Fatal(err)
	}
	if err := fixture.db.Create(&models.StructureFamilyAlias{StructureFamilyID: clathrate.ID, Alias: "clathrate", NormalizedAlias: "clathrate", Language: "en"}).Error; err != nil {
		t.Fatal(err)
	}

	response := fixture.request(t, http.MethodGet, "/api/classification-catalogs", "", nil)
	if response.Code != http.StatusOK {
		t.Fatalf("status=%d body=%s", response.Code, response.Body.String())
	}
	var catalog map[string]any
	if err := json.Unmarshal(response.Body.Bytes(), &catalog); err != nil {
		t.Fatal(err)
	}
	materialItems := catalog["material_families"].([]any)
	if len(materialItems) != 2 {
		t.Fatalf("active material count=%d want 2", len(materialItems))
	}
	for _, raw := range materialItems {
		item := raw.(map[string]any)
		if _, exists := item["code"]; exists {
			t.Fatal("public catalog exposed internal code")
		}
		if item["name"] == "停用项" {
			t.Fatal("inactive term appeared in public catalog")
		}
	}

	if got := fixture.request(t, http.MethodGet, "/api/admin/classification-proposals", "user", nil).Code; got != http.StatusForbidden {
		t.Fatalf("user admin status=%d want 403", got)
	}
	createBody := map[string]any{"code": "new_term", "name": "新目录", "name_en": "New term", "reason": "test"}
	if got := fixture.request(t, http.MethodPost, "/api/superadmin/classification-catalogs/material_family", "admin", createBody).Code; got != http.StatusForbidden {
		t.Fatalf("admin superadmin status=%d want 403", got)
	}
	if got := fixture.request(t, http.MethodPost, "/api/superadmin/classification-catalogs/material_family", "superadmin", createBody).Code; got != http.StatusOK {
		t.Fatalf("superadmin create status=%d want 200", got)
	}
}

func TestAliasCannotShadowAnotherCanonicalName(t *testing.T) {
	fixture := newAPIFixture(t)
	hydride, heavy, _, _ := seedCatalogs(t, fixture.db)
	state := models.MaterialState{ID: 1, PaperID: 1, PaperRevision: 1, SuperconductorID: 1, MaterialDimensionality: "unknown", StateKind: "unknown"}
	if err := fixture.db.Create(&state).Error; err != nil {
		t.Fatal(err)
	}
	proposal := models.ClassificationProposal{MaterialStateID: state.ID, Dimension: "material_family", RawName: heavy.NameZH, NormalizedName: heavy.NormalizedName, Status: "proposed", SourceKind: "ai"}
	if err := fixture.db.Create(&proposal).Error; err != nil {
		t.Fatal(err)
	}

	response := fixture.request(t, http.MethodPost, fmt.Sprintf("/api/superadmin/classification-proposals/%d/resolve", proposal.ID), "superadmin", map[string]any{
		"resolution_kind": "alias_created", "target_id": hydride.ID, "reason": "conflict test",
	})
	if response.Code != http.StatusConflict {
		t.Fatalf("status=%d want 409 body=%s", response.Code, response.Body.String())
	}
	var body map[string]any
	_ = json.Unmarshal(response.Body.Bytes(), &body)
	if body["code"] != "alias_conflict" {
		t.Fatalf("code=%v want alias_conflict", body["code"])
	}
	var aliasCount, auditCount int64
	fixture.db.Model(&models.MaterialFamilyAlias{}).Count(&aliasCount)
	fixture.db.Model(&models.ClassificationAuditEvent{}).Count(&auditCount)
	fixture.db.First(&proposal, proposal.ID)
	if aliasCount != 0 || auditCount != 0 || proposal.Status != "proposed" {
		t.Fatal("conflicting alias produced partial writes")
	}
}

func TestResolvedProposalCannotBeRewritten(t *testing.T) {
	fixture := newAPIFixture(t)
	hydride, _, _, _ := seedCatalogs(t, fixture.db)
	state := models.MaterialState{ID: 1, PaperID: 1, PaperRevision: 1, SuperconductorID: 1, MaterialDimensionality: "unknown", StateKind: "unknown"}
	fixture.db.Create(&state)
	resolved := "mapped_existing"
	proposal := models.ClassificationProposal{MaterialStateID: state.ID, Dimension: "material_family", RawName: "hydride", NormalizedName: "hydride", Status: "resolved", SourceKind: "ai", ResolutionKind: &resolved, MaterialFamilyID: &hydride.ID}
	fixture.db.Create(&proposal)

	response := fixture.request(t, http.MethodPost, fmt.Sprintf("/api/admin/classification-proposals/%d/map", proposal.ID), "admin", map[string]any{"target_id": hydride.ID, "reason": "retry"})
	if response.Code != http.StatusConflict {
		t.Fatalf("status=%d want 409", response.Code)
	}
	var audits int64
	fixture.db.Model(&models.ClassificationAuditEvent{}).Count(&audits)
	if audits != 0 {
		t.Fatal("terminal retry wrote an audit")
	}
}

func TestMergeMigratesMaterialAndStructureRelationshipsAndAliases(t *testing.T) {
	fixture := newAPIFixture(t)
	hydride, heavy, clathrate, layered := seedCatalogs(t, fixture.db)
	state := models.MaterialState{ID: 1, PaperID: 1, PaperRevision: 1, SuperconductorID: 1, MaterialFamilyID: &hydride.ID, MaterialDimensionality: "unknown", StateKind: "unknown"}
	fixture.db.Create(&state)
	fixture.db.Create(&models.MaterialFamilyAlias{MaterialFamilyID: hydride.ID, Alias: "hydride", NormalizedAlias: "hydride", Language: "en"})
	fixture.db.Create(&models.StructureFamilyAlias{StructureFamilyID: clathrate.ID, Alias: "clathrate", NormalizedAlias: "clathrate", Language: "en"})
	fixture.db.Create(&models.MaterialStateStructureFamily{MaterialStateID: state.ID, StructureFamilyID: clathrate.ID, IsPrimary: true})
	fixture.db.Create(&models.MaterialStateStructureFamily{MaterialStateID: state.ID, StructureFamilyID: layered.ID, IsPrimary: false})
	materialProposal := models.ClassificationProposal{MaterialStateID: state.ID, Dimension: "material_family", RawName: "hydride", NormalizedName: "hydride", Status: "resolved", SourceKind: "ai", MaterialFamilyID: &hydride.ID}
	structureProposal := models.ClassificationProposal{MaterialStateID: state.ID, Dimension: "structure_family", RawName: "clathrate", NormalizedName: "clathrate", Status: "resolved", SourceKind: "ai", StructureFamilyID: &clathrate.ID}
	fixture.db.Create(&materialProposal)
	fixture.db.Create(&structureProposal)
	fixture.db.Create(&models.ClassificationEvidence{PaperID: 1, PaperRevision: 1, MaterialStateID: state.ID, Dimension: "material_family", MaterialFamilyID: &hydride.ID, SourceKind: "reported", Scope: "current_paper"})
	fixture.db.Create(&models.ClassificationEvidence{PaperID: 1, PaperRevision: 1, MaterialStateID: state.ID, Dimension: "structure_family", StructureFamilyID: &clathrate.ID, SourceKind: "reported", Scope: "current_paper"})

	materialResponse := fixture.request(t, http.MethodPost, fmt.Sprintf("/api/superadmin/classification-catalogs/material_family/%d/merge", hydride.ID), "superadmin", map[string]any{"target_id": heavy.ID, "reason": "deduplicate"})
	if materialResponse.Code != http.StatusOK {
		t.Fatalf("material merge status=%d body=%s", materialResponse.Code, materialResponse.Body.String())
	}
	structureResponse := fixture.request(t, http.MethodPost, fmt.Sprintf("/api/superadmin/classification-catalogs/structure_family/%d/merge", clathrate.ID), "superadmin", map[string]any{"target_id": layered.ID, "reason": "deduplicate"})
	if structureResponse.Code != http.StatusOK {
		t.Fatalf("structure merge status=%d body=%s", structureResponse.Code, structureResponse.Body.String())
	}

	fixture.db.First(&state, state.ID)
	fixture.db.First(&materialProposal, materialProposal.ID)
	fixture.db.First(&structureProposal, structureProposal.ID)
	var materialAlias models.MaterialFamilyAlias
	var structureAlias models.StructureFamilyAlias
	fixture.db.First(&materialAlias)
	fixture.db.First(&structureAlias)
	var links []models.MaterialStateStructureFamily
	fixture.db.Where("material_state_id = ?", state.ID).Find(&links)
	if state.MaterialFamilyID == nil || *state.MaterialFamilyID != heavy.ID || materialAlias.MaterialFamilyID != heavy.ID || materialProposal.MaterialFamilyID == nil || *materialProposal.MaterialFamilyID != heavy.ID {
		t.Fatal("material merge did not migrate every relationship")
	}
	if len(links) != 1 || links[0].StructureFamilyID != layered.ID || !links[0].IsPrimary || structureAlias.StructureFamilyID != layered.ID || structureProposal.StructureFamilyID == nil || *structureProposal.StructureFamilyID != layered.ID {
		t.Fatalf("structure merge result links=%#v alias=%#v proposal=%#v", links, structureAlias, structureProposal)
	}
	var auditCount int64
	fixture.db.Model(&models.ClassificationAuditEvent{}).Count(&auditCount)
	if auditCount != 2 {
		t.Fatalf("audit count=%d want 2", auditCount)
	}
}

func TestCatalogMutationRollsBackWhenAuditInsertFails(t *testing.T) {
	fixture := newAPIFixture(t)
	hydride, _, _, _ := seedCatalogs(t, fixture.db)
	if err := fixture.db.Exec(`CREATE TRIGGER fail_classification_audit BEFORE INSERT ON classification_audit_events BEGIN SELECT RAISE(ABORT, 'audit failure'); END`).Error; err != nil {
		t.Fatal(err)
	}
	response := fixture.request(t, http.MethodPatch, fmt.Sprintf("/api/superadmin/classification-catalogs/material_family/%d", hydride.ID), "superadmin", map[string]any{"name": "新氢基名称", "reason": "rename"})
	if response.Code == http.StatusOK {
		t.Fatal("mutation succeeded despite audit failure")
	}
	fixture.db.First(&hydride, hydride.ID)
	if hydride.NameZH != "氢基超导体" {
		t.Fatalf("term changed without audit: %s", hydride.NameZH)
	}
}

func TestPaperApprovalRejectsIncompleteClassificationWithoutChangingStatus(t *testing.T) {
	fixture := newAPIFixture(t)
	paperType := "experimental"
	uploader := uint(99)
	title := "Incomplete classification"
	paper := models.Paper{Title: &title, PaperType: &paperType, ReviewStatus: "pending", ContentRevision: 1, UploadedBy: &uploader}
	if err := fixture.db.Create(&paper).Error; err != nil {
		t.Fatal(err)
	}

	response := fixture.request(t, http.MethodPost, fmt.Sprintf("/api/admin/papers/%d/review", paper.ID), "admin", map[string]any{"status": "approved", "comment": "approve"})
	if response.Code != http.StatusConflict {
		t.Fatalf("status=%d want 409 body=%s", response.Code, response.Body.String())
	}
	var body map[string]any
	_ = json.Unmarshal(response.Body.Bytes(), &body)
	if body["code"] != "classification_incomplete" {
		t.Fatalf("code=%v", body["code"])
	}
	fixture.db.First(&paper, paper.ID)
	if paper.ReviewStatus != "pending" || paper.ApprovedRevision != nil {
		t.Fatal("incomplete approval changed paper")
	}
	var events int64
	fixture.db.Model(&models.PaperReviewEvent{}).Count(&events)
	if events != 0 {
		t.Fatal("incomplete approval wrote review event")
	}
}
