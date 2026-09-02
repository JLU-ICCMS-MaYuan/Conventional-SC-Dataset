package handlers

import (
	"crypto/sha256"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strings"

	"scwiki/server/database"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
	"golang.org/x/text/unicode/norm"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

var materialDimensionalities = []gin.H{
	{"value": "zero_dimensional", "name": "零维"},
	{"value": "one_dimensional", "name": "一维"},
	{"value": "two_dimensional", "name": "二维"},
	{"value": "three_dimensional", "name": "三维"},
	{"value": "quasi_one_dimensional", "name": "准一维"},
	{"value": "quasi_two_dimensional", "name": "准二维"},
	{"value": "unknown", "name": "未知"},
}

var (
	errClassificationInvalid      = errors.New("classification selection invalid")
	errClassificationNotFound     = errors.New("classification target not found")
	errClassificationNameConflict = errors.New("classification name conflicts with catalog")
	errLegacyClassificationContract = errors.New("legacy material-state superconductor_kind")
)

type classificationSelection struct {
	ID   uint   `json:"id"`
	Name string `json:"name"`
}

type structureClassificationSelection struct {
	ID        uint   `json:"id"`
	Name      string `json:"name"`
	IsPrimary bool   `json:"is_primary"`
}

type materialClassificationUpdate struct {
	ID                     uint64                             `json:"id"`
	MaterialDimensionality string                             `json:"material_dimensionality"`
	StructureFamilies      []structureClassificationSelection `json:"structure_families"`
}

func (update *materialClassificationUpdate) UnmarshalJSON(data []byte) error {
	var raw map[string]json.RawMessage
	if err := json.Unmarshal(data, &raw); err != nil {
		return err
	}
	if _, exists := raw["superconductor_kind"]; exists {
		return errLegacyClassificationContract
	}
	type decodedMaterialClassificationUpdate materialClassificationUpdate
	var decoded decodedMaterialClassificationUpdate
	if err := json.Unmarshal(data, &decoded); err != nil {
		return err
	}
	*update = materialClassificationUpdate(decoded)
	return nil
}

type classificationSnapshotTerm struct {
	ID        uint   `json:"id"`
	Name      string `json:"name"`
	IsPrimary *bool  `json:"is_primary,omitempty"`
}

type classificationSnapshotState struct {
	ID                     uint64                       `json:"id"`
	MaterialDimensionality string                       `json:"material_dimensionality"`
	CrystalSystem          string                       `json:"crystal_system"`
	StructureFamilies      []classificationSnapshotTerm `json:"structure_families"`
}

type paperClassificationSnapshot struct {
	SuperconductorKind string                       `json:"superconductor_kind"`
	MaterialFamilies []classificationSnapshotTerm  `json:"material_families"`
	MaterialStates   []classificationSnapshotState `json:"material_states"`
}

func normalizeClassificationName(value string) string {
	value = strings.ToLower(strings.TrimSpace(norm.NFKC.String(value)))
	value = strings.NewReplacer("_", " ", "-", " ").Replace(value)
	return strings.Join(strings.Fields(value), " ")
}

func generatedClassificationCode(normalizedName string) string {
	digest := sha256.Sum256([]byte(normalizedName))
	return fmt.Sprintf("custom_%x", digest[:10])
}

func serializeCatalog(items interface{}) []gin.H {
	result := make([]gin.H, 0)
	switch values := items.(type) {
	case []models.MaterialFamily:
		for _, item := range values {
			aliases := make([]string, 0, len(item.Aliases))
			for _, alias := range item.Aliases {
				aliases = append(aliases, alias.Alias)
			}
			result = append(result, gin.H{"id": item.ID, "name": item.NameZH, "name_zh": item.NameZH, "name_en": item.NameEN, "aliases": aliases})
		}
	case []models.StructureFamily:
		for _, item := range values {
			aliases := make([]string, 0, len(item.Aliases))
			for _, alias := range item.Aliases {
				aliases = append(aliases, alias.Alias)
			}
			result = append(result, gin.H{"id": item.ID, "name": item.NameZH, "name_zh": item.NameZH, "name_en": item.NameEN, "aliases": aliases})
		}
	}
	return result
}

// GetClassificationCatalogs 返回数据库目录，不暴露内部编码。
func GetClassificationCatalogs(c *gin.Context) {
	var materialFamilies []models.MaterialFamily
	var structureFamilies []models.StructureFamily
	if err := database.DB.Preload("Aliases").Order("id").Find(&materialFamilies).Error; err != nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"code": "catalog_unavailable", "error": "材料分类目录暂不可用"})
		return
	}
	if err := database.DB.Preload("Aliases").Order("id").Find(&structureFamilies).Error; err != nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"code": "catalog_unavailable", "error": "结构分类目录暂不可用"})
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"material_families":         serializeCatalog(materialFamilies),
		"structure_families":        serializeCatalog(structureFamilies),
		"material_dimensionalities": materialDimensionalities,
	})
}

func validMaterialDimensionality(value string) bool {
	for _, option := range materialDimensionalities {
		if option["value"] == value {
			return true
		}
	}
	return false
}

func validSuperconductorKind(value string) bool {
	switch value {
	case "conventional", "unconventional", "unknown":
		return true
	default:
		return false
	}
}

func resolveMaterialFamily(tx *gorm.DB, actorID uint, selection classificationSelection) (*models.MaterialFamily, error) {
	if selection.ID != 0 {
		var family models.MaterialFamily
		if err := tx.First(&family, selection.ID).Error; err != nil {
			return nil, errClassificationNotFound
		}
		return &family, nil
	}
	name := strings.TrimSpace(selection.Name)
	normalizedName := normalizeClassificationName(name)
	if normalizedName == "" {
		return nil, errClassificationInvalid
	}

	var family models.MaterialFamily
	code := strings.ReplaceAll(normalizedName, " ", "_")
	err := tx.Where("normalized_name = ? OR code = ?", normalizedName, code).First(&family).Error
	if err == nil {
		return &family, nil
	}
	if !errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, err
	}
	var alias models.MaterialFamilyAlias
	if err := tx.Where("normalized_alias = ?", normalizedName).First(&alias).Error; err == nil {
		if err := tx.First(&family, alias.MaterialFamilyID).Error; err != nil {
			return nil, err
		}
		return &family, nil
	} else if !errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, err
	}

	family = models.MaterialFamily{
		Code: generatedClassificationCode(normalizedName), NameZH: name,
		NormalizedName: normalizedName, CreatedByUserID: &actorID,
	}
	result := tx.Clauses(clause.OnConflict{DoNothing: true}).Create(&family)
	if result.Error != nil {
		return nil, result.Error
	}
	if result.RowsAffected == 0 {
		if err := tx.Where("normalized_name = ?", normalizedName).First(&family).Error; err != nil {
			return nil, errClassificationNameConflict
		}
	}
	return &family, nil
}

func resolveStructureFamily(tx *gorm.DB, actorID uint, selection classificationSelection) (*models.StructureFamily, error) {
	if selection.ID != 0 {
		var family models.StructureFamily
		if err := tx.First(&family, selection.ID).Error; err != nil {
			return nil, errClassificationNotFound
		}
		return &family, nil
	}
	name := strings.TrimSpace(selection.Name)
	normalizedName := normalizeClassificationName(name)
	if normalizedName == "" {
		return nil, errClassificationInvalid
	}

	var family models.StructureFamily
	code := strings.ReplaceAll(normalizedName, " ", "_")
	err := tx.Where("normalized_name = ? OR code = ?", normalizedName, code).First(&family).Error
	if err == nil {
		return &family, nil
	}
	if !errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, err
	}
	var alias models.StructureFamilyAlias
	if err := tx.Where("normalized_alias = ?", normalizedName).First(&alias).Error; err == nil {
		if err := tx.First(&family, alias.StructureFamilyID).Error; err != nil {
			return nil, err
		}
		return &family, nil
	} else if !errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, err
	}

	family = models.StructureFamily{
		Code: generatedClassificationCode(normalizedName), NameZH: name,
		NormalizedName: normalizedName, CreatedByUserID: &actorID,
	}
	result := tx.Clauses(clause.OnConflict{DoNothing: true}).Create(&family)
	if result.Error != nil {
		return nil, result.Error
	}
	if result.RowsAffected == 0 {
		if err := tx.Where("normalized_name = ?", normalizedName).First(&family).Error; err != nil {
			return nil, errClassificationNameConflict
		}
	}
	return &family, nil
}

func applyPaperClassifications(
	tx *gorm.DB,
	paper *models.Paper,
	actorID uint,
	superconductorKind string,
	materialFamilies []classificationSelection,
	updates []materialClassificationUpdate,
) (paperClassificationSnapshot, error) {
	revision := paper.ContentRevision
	if revision == 0 {
		revision = 1
	}
	if !validSuperconductorKind(superconductorKind) || len(materialFamilies) == 0 {
		return paperClassificationSnapshot{}, errClassificationInvalid
	}
	if err := tx.Model(paper).Update("superconductor_kind", superconductorKind).Error; err != nil {
		return paperClassificationSnapshot{}, err
	}
	paper.SuperconductorKind = superconductorKind
	seenFamilies := make(map[uint]bool, len(materialFamilies))
	familySnapshots := make([]classificationSnapshotTerm, 0, len(materialFamilies))
	for _, selection := range materialFamilies {
		family, err := resolveMaterialFamily(tx, actorID, selection)
		if err != nil {
			return paperClassificationSnapshot{}, err
		}
		if seenFamilies[family.ID] {
			continue
		}
		seenFamilies[family.ID] = true
		familySnapshots = append(familySnapshots, classificationSnapshotTerm{
			ID: family.ID, Name: family.NameZH,
		})
	}
	if err := tx.Where("paper_id = ? AND paper_revision = ?", paper.ID, revision).
		Delete(&models.PaperMaterialFamily{}).Error; err != nil {
		return paperClassificationSnapshot{}, err
	}
	for _, family := range familySnapshots {
		if err := tx.Create(&models.PaperMaterialFamily{
			PaperID: paper.ID, PaperRevision: revision, MaterialFamilyID: family.ID,
		}).Error; err != nil {
			return paperClassificationSnapshot{}, err
		}
	}

	seenStates := make(map[uint64]bool, len(updates))
	snapshots := make([]classificationSnapshotState, 0, len(updates))
	for _, update := range updates {
		if update.ID == 0 || seenStates[update.ID] || !validMaterialDimensionality(update.MaterialDimensionality) {
			return paperClassificationSnapshot{}, errClassificationInvalid
		}
		seenStates[update.ID] = true

		var state models.MaterialState
		if err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).
			Where("id = ? AND paper_id = ? AND paper_revision = ?", update.ID, paper.ID, revision).
			First(&state).Error; err != nil {
			return paperClassificationSnapshot{}, errClassificationNotFound
		}

		primaryCount := 0
		seenStructures := make(map[uint]bool, len(update.StructureFamilies))
		resolvedStructures := make([]struct {
			Family    *models.StructureFamily
			IsPrimary bool
		}, 0, len(update.StructureFamilies))
		for _, selection := range update.StructureFamilies {
			family, err := resolveStructureFamily(tx, actorID, classificationSelection{
				ID: selection.ID, Name: selection.Name,
			})
			if err != nil {
				return paperClassificationSnapshot{}, err
			}
			if seenStructures[family.ID] {
				return paperClassificationSnapshot{}, errClassificationInvalid
			}
			seenStructures[family.ID] = true
			if selection.IsPrimary {
				primaryCount++
			}
			resolvedStructures = append(resolvedStructures, struct {
				Family    *models.StructureFamily
				IsPrimary bool
			}{Family: family, IsPrimary: selection.IsPrimary})
		}
		if primaryCount > 1 {
			return paperClassificationSnapshot{}, errClassificationInvalid
		}

		if err := tx.Model(&state).Updates(map[string]interface{}{
			"material_dimensionality": update.MaterialDimensionality,
		}).Error; err != nil {
			return paperClassificationSnapshot{}, err
		}
		if err := tx.Where("material_state_id = ?", state.ID).
			Delete(&models.MaterialStateStructureFamily{}).Error; err != nil {
			return paperClassificationSnapshot{}, err
		}

		structureSnapshot := make([]classificationSnapshotTerm, 0, len(resolvedStructures))
		for _, resolved := range resolvedStructures {
			link := models.MaterialStateStructureFamily{
				MaterialStateID: state.ID, StructureFamilyID: resolved.Family.ID,
				IsPrimary: resolved.IsPrimary,
			}
			if err := tx.Create(&link).Error; err != nil {
				return paperClassificationSnapshot{}, err
			}
			isPrimary := resolved.IsPrimary
			structureSnapshot = append(structureSnapshot, classificationSnapshotTerm{
				ID: resolved.Family.ID, Name: resolved.Family.NameZH, IsPrimary: &isPrimary,
			})
		}

		snapshots = append(snapshots, classificationSnapshotState{
			ID:                     state.ID,
			MaterialDimensionality: update.MaterialDimensionality,
			CrystalSystem:          state.CrystalSystem,
			StructureFamilies:      structureSnapshot,
		})
	}
	return paperClassificationSnapshot{
		SuperconductorKind: superconductorKind,
		MaterialFamilies: familySnapshots,
		MaterialStates: snapshots,
	}, nil
}
