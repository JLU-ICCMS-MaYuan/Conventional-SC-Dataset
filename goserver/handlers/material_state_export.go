package handlers

import (
	"database/sql"
	"errors"
	"fmt"
	"net/http"
	"path/filepath"
	"sort"
	"strconv"
	"strings"

	"scwiki/server/database"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

var (
	errExportNotFound         = errors.New("export not found")
	errExportForbidden        = errors.New("export forbidden")
	errExportIncomplete       = errors.New("export incomplete")
	errExportRevisionConflict = errors.New("export revision conflict")
)

var materialStateExportAfterSnapshot = func() {}

type definitionIdentity struct {
	Key     string
	Version int
}

// ExportMaterialState 返回无需数据库或定义服务即可解释的 MaterialState JSON 数据包。
func ExportMaterialState(c *gin.Context) {
	paperID, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil || paperID == 0 {
		writeMaterialStateExportError(c, errExportNotFound, "论文不存在")
		return
	}
	stateKey, ok := parseMaterialStateKey(c.Param("stateKey"))
	if !ok {
		writeMaterialStateExportError(c, errExportNotFound, "材料状态不存在")
		return
	}

	user := optionalPaperUser(c)
	var snapshot gin.H
	var snapshotRevision uint
	err = database.DB.Transaction(func(tx *gorm.DB) error {
		var paper models.Paper
		if err := tx.First(&paper, uint(paperID)).Error; err != nil {
			return errExportNotFound
		}
		if !canViewPaper(&paper, user) {
			return errExportForbidden
		}
		snapshotRevision = paper.ContentRevision

		var state models.MaterialState
		if err := targetMaterialStateExportQuery(tx).
			Where("material_states.state_key = ? AND material_states.paper_id = ? AND material_states.paper_revision = ?", stateKey, paper.ID, snapshotRevision).
			First(&state).Error; err != nil {
			if errors.Is(err, gorm.ErrRecordNotFound) {
				return errExportNotFound
			}
			return err
		}
		hydrateExportStateRecords(&state)

		definitions, err := loadBoundDefinitions(tx, state)
		if err != nil {
			return err
		}
		if err := validateExportCompleteness(paper, state, definitions); err != nil {
			return err
		}
		snapshot = materialStateExportPayload(paper, state, definitions)
		return nil
	}, &sql.TxOptions{Isolation: sql.LevelRepeatableRead, ReadOnly: true})
	if err != nil {
		writeMaterialStateExportError(c, err, "导出失败")
		return
	}

	materialStateExportAfterSnapshot()
	var currentRevision uint
	if err := database.DB.Model(&models.Paper{}).Select("content_revision").Where("id = ?", uint(paperID)).Scan(&currentRevision).Error; err != nil || currentRevision != snapshotRevision {
		writeMaterialStateExportError(c, errExportRevisionConflict, "论文版本已变化，请重试")
		return
	}

	c.Header("Content-Disposition", fmt.Sprintf(`attachment; filename="paper-%d-%s.json"`, paperID, exportFilenameSegment(stateKey)))
	c.JSON(http.StatusOK, snapshot)
}

func parseMaterialStateKey(raw string) (string, bool) {
	value := strings.TrimSpace(raw)
	return value, value != "" && len(value) <= 96
}

func exportFilenameSegment(stateKey string) string {
	return strings.Map(func(r rune) rune {
		if r >= 'a' && r <= 'z' || r >= 'A' && r <= 'Z' || r >= '0' && r <= '9' || r == '-' || r == '_' {
			return r
		}
		return '_'
	}, stateKey)
}

func targetMaterialStateExportQuery(db *gorm.DB) *gorm.DB {
	return db.
		Preload("Superconductor.ChemicalSystem").
		Preload("StructureFamilyLinks.StructureFamily").
		Preload("Structures", func(query *gorm.DB) *gorm.DB { return query.Order("id ASC") }).
		Preload("PropertyModules", func(query *gorm.DB) *gorm.DB { return query.Order("display_order ASC, id ASC") }).
		Preload("PropertyModules.Records", func(query *gorm.DB) *gorm.DB { return query.Order("id ASC") }).
		Preload("PropertyModules.Records.Definition").
		Preload("PropertyModules.Records.Evidences.Evidence")
}

func hydrateExportStateRecords(state *models.MaterialState) {
	for moduleIndex := range state.PropertyModules {
		module := &state.PropertyModules[moduleIndex]
		if module.Records == nil {
			module.Records = make([]models.PropertyRecord, 0)
		}
		for recordIndex := range module.Records {
			module.Records[recordIndex].ModuleCode = module.ModuleCode
			if module.Records[recordIndex].Evidences == nil {
				module.Records[recordIndex].Evidences = make([]models.PropertyRecordEvidence, 0)
			}
		}
	}
}

func loadBoundDefinitions(tx *gorm.DB, state models.MaterialState) ([]models.FormDefinition, error) {
	identities := make(map[definitionIdentity]struct{})
	for _, module := range state.PropertyModules {
		identities[definitionIdentity{Key: module.DefinitionKey, Version: module.DefinitionVersion}] = struct{}{}
		for _, record := range module.Records {
			identities[definitionIdentity{Key: record.DefinitionKey, Version: record.DefinitionVersion}] = struct{}{}
		}
	}
	if len(identities) == 0 {
		return []models.FormDefinition{}, nil
	}

	query := tx.Model(&models.FormDefinition{}).Where("1 = 0")
	for identity := range identities {
		query = query.Or("definition_key = ? AND version = ?", identity.Key, identity.Version)
	}
	var definitions []models.FormDefinition
	if err := query.Find(&definitions).Error; err != nil {
		return nil, err
	}
	found := make(map[definitionIdentity]struct{}, len(definitions))
	for _, definition := range definitions {
		found[definitionIdentity{Key: definition.DefinitionKey, Version: definition.Version}] = struct{}{}
	}
	for identity := range identities {
		if _, ok := found[identity]; !ok {
			return nil, fmt.Errorf("%w: definition %s@%d", errExportIncomplete, identity.Key, identity.Version)
		}
	}
	sort.Slice(definitions, func(i, j int) bool {
		if definitions[i].DefinitionKey == definitions[j].DefinitionKey {
			return definitions[i].Version < definitions[j].Version
		}
		return definitions[i].DefinitionKey < definitions[j].DefinitionKey
	})
	return definitions, nil
}

func validateExportCompleteness(paper models.Paper, state models.MaterialState, definitions []models.FormDefinition) error {
	if state.Superconductor.ID == 0 || state.Superconductor.ChemicalSystem.ID == 0 {
		return fmt.Errorf("%w: material ownership", errExportIncomplete)
	}
	if len(state.PropertyModules) > 0 && len(definitions) == 0 {
		return fmt.Errorf("%w: definitions", errExportIncomplete)
	}
	for _, module := range state.PropertyModules {
		for _, record := range module.Records {
			if paper.ReviewStatus == reviewStatusApproved && len(record.Evidences) == 0 {
				return fmt.Errorf("%w: evidence for %s", errExportIncomplete, record.RecordKey)
			}
			for _, link := range record.Evidences {
				if link.Evidence.ID == 0 || link.Evidence.PaperID != paper.ID || link.Evidence.PaperRevision != paper.ContentRevision {
					return fmt.Errorf("%w: evidence for %s", errExportIncomplete, record.RecordKey)
				}
			}
			if record.StructureKey != nil && len(state.Structures) == 0 {
				return fmt.Errorf("%w: structure for %s", errExportIncomplete, record.RecordKey)
			}
		}
	}
	return nil
}

func materialStateExportPayload(paper models.Paper, state models.MaterialState, definitions []models.FormDefinition) gin.H {
	statePayload := materialStatesToDict([]models.MaterialState{state})[0]
	statePayload["state_key"] = state.StateKey
	statePayload["structures"] = exportStructures(state.Structures)

	return gin.H{
		"export_version": 1,
		"paper": gin.H{
			"id": paper.ID, "revision": paper.ContentRevision, "doi": paper.DOI,
			"title": paper.Title, "year": paper.Year,
		},
		"material": gin.H{
			"chemical_system": state.Superconductor.ChemicalSystem,
			"superconductor":  state.Superconductor,
		},
		"material_state":   statePayload,
		"form_definitions": definitions,
	}
}

func exportStructures(structures []models.StructureModel) []gin.H {
	output := make([]gin.H, 0, len(structures))
	for _, structure := range structures {
		filename := fmt.Sprintf("structure-%d.%s", structure.ID, strings.ToLower(structure.StructureFormat))
		if structure.SourceLocator != nil && strings.TrimSpace(*structure.SourceLocator) != "" {
			filename = filepath.Base(*structure.SourceLocator)
		}
		mediaType := "text/plain"
		if strings.EqualFold(structure.StructureFormat, "cif") {
			mediaType = "chemical/x-cif"
		}
		output = append(output, gin.H{
			"structure_key":      fmt.Sprintf("structure-%d", structure.ID),
			"structure_format":   structure.StructureFormat,
			"structure_hash":     structure.StructureHash,
			"space_group_symbol": structure.SpaceGroupSymbol,
			"space_group_number": structure.SpaceGroupNumber,
			"cell_parameters":    structure.CellParameters,
			"volume_angstrom3":   structure.VolumeAngstrom3,
			"atom_count":         structure.AtomCount,
			"geometry_method":    structure.GeometryMethod,
			"calculation_code":   structure.CalculationCode,
			"file": gin.H{
				"filename": filename, "media_type": mediaType,
				"sha256": structure.StructureHash, "content": structure.StructureText,
			},
		})
	}
	return output
}

func writeMaterialStateExportError(c *gin.Context, err error, message string) {
	switch {
	case errors.Is(err, errExportNotFound):
		c.JSON(http.StatusNotFound, gin.H{"code": "export_not_found", "error": message})
	case errors.Is(err, errExportForbidden):
		c.JSON(http.StatusForbidden, gin.H{"code": "export_forbidden", "error": "无权导出该论文"})
	case errors.Is(err, errExportRevisionConflict):
		c.JSON(http.StatusConflict, gin.H{"code": "export_revision_conflict", "error": message})
	case errors.Is(err, errExportIncomplete):
		c.JSON(http.StatusConflict, gin.H{"code": "export_incomplete", "error": err.Error()})
	default:
		c.JSON(http.StatusInternalServerError, gin.H{"code": "export_failed", "error": message})
	}
}
