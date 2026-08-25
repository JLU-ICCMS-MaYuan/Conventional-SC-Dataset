package handlers

import (
	"testing"

	"scwiki/server/models"

	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

func TestNormalizeClassificationName(t *testing.T) {
	for input, expected := range map[string]string{
		" Hydrogen_Based ": "hydrogen based",
		"HEAVY-FERMION":    "heavy fermion",
		"高压氢化物":            "高压氢化物",
	} {
		if actual := normalizeClassificationName(input); actual != expected {
			t.Fatalf("normalizeClassificationName(%q) = %q, want %q", input, actual, expected)
		}
	}
}

func TestValidMaterialDimensionality(t *testing.T) {
	for _, value := range []string{
		"zero_dimensional", "one_dimensional", "two_dimensional", "three_dimensional",
		"quasi_one_dimensional", "quasi_two_dimensional", "unknown",
	} {
		if !validMaterialDimensionality(value) {
			t.Fatalf("%q should be valid", value)
		}
	}
	if validMaterialDimensionality("high_pressure") {
		t.Fatal("pressure must not be accepted as material dimensionality")
	}
}

func TestMaterialFamiliesToPublicOmitsInternalCode(t *testing.T) {
	items := materialFamiliesToPublic([]models.MaterialFamily{{
		ID: 1, Code: "hydrogen_based", NameZH: "氢基超导体",
		Aliases: []models.MaterialFamilyAlias{{Alias: "hydride"}},
	}})

	if len(items) != 1 || items[0]["name"] != "氢基超导体" {
		t.Fatalf("unexpected public catalog: %#v", items)
	}
	if _, exists := items[0]["code"]; exists {
		t.Fatal("public catalog must not expose internal code")
	}
}

func TestCreateReviewedClassificationEvidence(t *testing.T) {
	db, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{DisableForeignKeyConstraintWhenMigrating: true})
	if err != nil {
		t.Fatal(err)
	}
	if err := db.AutoMigrate(&models.MaterialState{}, &models.ClassificationProposal{}, &models.ClassificationEvidence{}); err != nil {
		t.Fatal(err)
	}
	state := models.MaterialState{ID: 9, PaperID: 3, PaperRevision: 2, SuperconductorID: 4, MaterialDimensionality: "unknown", StateKind: "unknown"}
	if err := db.Create(&state).Error; err != nil {
		t.Fatal(err)
	}
	proposal := models.ClassificationProposal{ID: 7, MaterialStateID: state.ID, Dimension: "material_family", RawName: "hydride", NormalizedName: "hydride", SourceKind: "ai"}
	if err := db.Create(&proposal).Error; err != nil {
		t.Fatal(err)
	}
	if err := createReviewedClassificationEvidence(db, 11, &proposal, 5); err != nil {
		t.Fatal(err)
	}

	var evidence models.ClassificationEvidence
	if err := db.First(&evidence).Error; err != nil {
		t.Fatal(err)
	}
	if evidence.PaperID != 3 || evidence.PaperRevision != 2 || evidence.SourceKind != "reviewed" || evidence.Scope != "current_paper" {
		t.Fatalf("unexpected reviewed evidence: %#v", evidence)
	}
	if evidence.MaterialFamilyID == nil || *evidence.MaterialFamilyID != 5 || evidence.ReviewedByUserID == nil || *evidence.ReviewedByUserID != 11 {
		t.Fatalf("review target was not persisted: %#v", evidence)
	}
}

func TestValidatePaperClassificationComplete(t *testing.T) {
	db, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{DisableForeignKeyConstraintWhenMigrating: true})
	if err != nil {
		t.Fatal(err)
	}
	if err := db.AutoMigrate(&models.MaterialState{}, &models.ClassificationProposal{}); err != nil {
		t.Fatal(err)
	}
	paperType := "theoretical"
	paper := models.Paper{ID: 3, ContentRevision: 2, PaperType: &paperType}
	if err := validatePaperClassificationComplete(db, &paper); err == nil {
		t.Fatal("non-review paper without material states must be incomplete")
	}

	state := models.MaterialState{ID: 9, PaperID: paper.ID, PaperRevision: paper.ContentRevision, SuperconductorID: 4, MaterialDimensionality: "unknown", StateKind: "unknown"}
	if err := db.Create(&state).Error; err != nil {
		t.Fatal(err)
	}
	if err := validatePaperClassificationComplete(db, &paper); err == nil {
		t.Fatal("state without family and element count must be incomplete")
	}

	familyID := uint(5)
	elementCount := int16(2)
	if err := db.Model(&state).Updates(map[string]interface{}{"material_family_id": familyID, "element_count": elementCount}).Error; err != nil {
		t.Fatal(err)
	}
	proposal := models.ClassificationProposal{MaterialStateID: state.ID, Dimension: "material_family", RawName: "hydride", NormalizedName: "hydride", Status: "proposed", SourceKind: "ai"}
	if err := db.Create(&proposal).Error; err != nil {
		t.Fatal(err)
	}
	if err := validatePaperClassificationComplete(db, &paper); err == nil {
		t.Fatal("unresolved material-family proposal must block approval")
	}
	if err := db.Model(&proposal).Update("status", "resolved").Error; err != nil {
		t.Fatal(err)
	}
	if err := validatePaperClassificationComplete(db, &paper); err != nil {
		t.Fatalf("complete classification should pass: %v", err)
	}
}
