package handlers

import (
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"strings"
	"time"

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

func normalizeClassificationName(value string) string {
	value = strings.ToLower(strings.TrimSpace(norm.NFKC.String(value)))
	value = strings.NewReplacer("_", " ", "-", " ").Replace(value)
	return strings.Join(strings.Fields(value), " ")
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
			result = append(result, gin.H{"id": item.ID, "name": item.NameZH, "aliases": aliases})
		}
	case []models.StructureFamily:
		for _, item := range values {
			aliases := make([]string, 0, len(item.Aliases))
			for _, alias := range item.Aliases {
				aliases = append(aliases, alias.Alias)
			}
			result = append(result, gin.H{"id": item.ID, "name": item.NameZH, "aliases": aliases})
		}
	}
	return result
}

// GetClassificationCatalogs 返回普通用户可选择的启用目录，不暴露内部编码。
func GetClassificationCatalogs(c *gin.Context) {
	var materialFamilies []models.MaterialFamily
	var structureFamilies []models.StructureFamily
	if err := database.DB.Preload("Aliases").Where("is_active = ?", true).Order("id").Find(&materialFamilies).Error; err != nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"code": "catalog_unavailable", "error": "材料分类目录暂不可用"})
		return
	}
	if err := database.DB.Preload("Aliases").Where("is_active = ?", true).Order("id").Find(&structureFamilies).Error; err != nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"code": "catalog_unavailable", "error": "结构分类目录暂不可用"})
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"material_families":         materialFamiliesToPublic(materialFamilies),
		"structure_families":        structureFamiliesToPublic(structureFamilies),
		"material_dimensionalities": materialDimensionalities,
	})
}

func materialFamiliesToPublic(items []models.MaterialFamily) []gin.H {
	return serializeCatalog(items)
}

func structureFamiliesToPublic(items []models.StructureFamily) []gin.H {
	return serializeCatalog(items)
}

type materialClassificationUpdate struct {
	ID                     uint64 `json:"id"`
	MaterialFamilyID       uint   `json:"material_family_id"`
	MaterialDimensionality string `json:"material_dimensionality"`
	StructureFamilies      []struct {
		ID        uint `json:"id"`
		IsPrimary bool `json:"is_primary"`
	} `json:"structure_families"`
}

// UpdatePaperMaterialClassifications 事务性替换论文当前 revision 的分类选择。
func UpdatePaperMaterialClassifications(c *gin.Context) {
	actor, ok := currentUserFromContext(c)
	if !ok {
		return
	}
	paperID, err := strconv.ParseUint(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "论文 ID 无效"})
		return
	}
	var body struct {
		MaterialStates []materialClassificationUpdate `json:"material_states"`
	}
	if c.ShouldBindJSON(&body) != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "分类请求无效"})
		return
	}
	err = database.DB.Transaction(func(tx *gorm.DB) error {
		var paper models.Paper
		if err := tx.First(&paper, uint(paperID)).Error; err != nil {
			return err
		}
		revision := paper.ContentRevision
		if revision == 0 {
			revision = 1
		}
		for _, update := range body.MaterialStates {
			var state models.MaterialState
			if err := tx.Where("id = ? AND paper_id = ? AND paper_revision = ?", update.ID, paper.ID, revision).First(&state).Error; err != nil {
				return err
			}
			var family models.MaterialFamily
			if err := tx.Where("id = ? AND is_active = ?", update.MaterialFamilyID, true).First(&family).Error; err != nil {
				return err
			}
			if !validMaterialDimensionality(update.MaterialDimensionality) {
				return gorm.ErrInvalidData
			}
			primaryCount := 0
			seen := make(map[uint]bool)
			for _, selection := range update.StructureFamilies {
				if selection.ID == 0 || seen[selection.ID] {
					return gorm.ErrInvalidData
				}
				seen[selection.ID] = true
				if selection.IsPrimary {
					primaryCount++
				}
				var structureFamily models.StructureFamily
				if err := tx.Where("id = ? AND is_active = ?", selection.ID, true).First(&structureFamily).Error; err != nil {
					return err
				}
			}
			if primaryCount > 1 {
				return gorm.ErrInvalidData
			}
			if err := tx.Model(&state).Updates(map[string]interface{}{
				"material_family_id":      update.MaterialFamilyID,
				"material_dimensionality": update.MaterialDimensionality,
			}).Error; err != nil {
				return err
			}
			var proposals []models.ClassificationProposal
			if err := tx.Where(
				"material_state_id = ? AND dimension = ? AND status IN ?",
				state.ID, "material_family", []string{"proposed", "under_review"},
			).Find(&proposals).Error; err != nil {
				return err
			}
			for _, proposal := range proposals {
				now := time.Now()
				note := "管理员在论文审核中映射到现有材料家族"
				updates := map[string]interface{}{
					"status": "resolved", "resolution_kind": "mapped_existing",
					"material_family_id": family.ID, "reviewed_by_user_id": actor.ID,
					"review_note": note, "resolved_at": now,
				}
				if err := tx.Model(&proposal).Updates(updates).Error; err != nil {
					return err
				}
				if err := createReviewedClassificationEvidence(tx, actor.ID, &proposal, family.ID); err != nil {
					return err
				}
				if err := createClassificationAudit(
					tx, actor.ID, "material_family", "proposal", proposal.ID,
					"mapped_existing", note, proposal, updates,
				); err != nil {
					return err
				}
			}
			if err := tx.Where("material_state_id = ?", state.ID).Delete(&models.MaterialStateStructureFamily{}).Error; err != nil {
				return err
			}
			for _, selection := range update.StructureFamilies {
				link := models.MaterialStateStructureFamily{MaterialStateID: state.ID, StructureFamilyID: selection.ID, IsPrimary: selection.IsPrimary}
				if err := tx.Create(&link).Error; err != nil {
					return err
				}
			}
		}
		return nil
	})
	if errors.Is(err, gorm.ErrRecordNotFound) {
		c.JSON(http.StatusNotFound, gin.H{"code": "classification_not_found", "error": "论文、材料状态或目录项不存在"})
		return
	}
	if errors.Is(err, gorm.ErrInvalidData) {
		c.JSON(http.StatusBadRequest, gin.H{"error": "材料分类选择无效"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "材料分类保存失败"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "材料分类已更新"})
}

func validMaterialDimensionality(value string) bool {
	for _, option := range materialDimensionalities {
		if option["value"] == value {
			return true
		}
	}
	return false
}

func ListClassificationProposals(c *gin.Context) {
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "100"))
	if limit < 1 || limit > 200 {
		limit = 100
	}
	offset, _ := strconv.Atoi(c.DefaultQuery("offset", "0"))
	query := database.DB.Model(&models.ClassificationProposal{})
	if status := c.Query("status"); status != "" {
		query = query.Where("status = ?", status)
	}
	if dimension := c.Query("dimension"); dimension != "" {
		query = query.Where("dimension = ?", dimension)
	}
	var total int64
	query.Count(&total)
	var proposals []models.ClassificationProposal
	if err := query.Order("created_at").Limit(limit).Offset(offset).Find(&proposals).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "分类建议加载失败"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"items": proposals, "total": total})
}

func MapClassificationProposal(c *gin.Context) {
	actor, ok := currentUserFromContext(c)
	if !ok {
		return
	}
	var body struct {
		TargetID uint   `json:"target_id"`
		Reason   string `json:"reason"`
	}
	if c.ShouldBindJSON(&body) != nil || body.TargetID == 0 || strings.TrimSpace(body.Reason) == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "目标目录项和审核理由必填"})
		return
	}
	err := database.DB.Transaction(func(tx *gorm.DB) error {
		var proposal models.ClassificationProposal
		if err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).First(&proposal, c.Param("id")).Error; err != nil {
			return err
		}
		if proposal.Status == "resolved" || proposal.Status == "rejected" {
			return errProposalResolved
		}
		updates := map[string]interface{}{"status": "resolved", "resolution_kind": "mapped_existing", "reviewed_by_user_id": actor.ID, "review_note": strings.TrimSpace(body.Reason), "resolved_at": time.Now()}
		if proposal.Dimension == "material_family" {
			var term models.MaterialFamily
			if err := tx.Where("id = ? AND is_active = ?", body.TargetID, true).First(&term).Error; err != nil {
				return err
			}
			updates["material_family_id"] = term.ID
			if err := tx.Model(&models.MaterialState{}).Where("id = ?", proposal.MaterialStateID).Update("material_family_id", term.ID).Error; err != nil {
				return err
			}
		} else {
			var term models.StructureFamily
			if err := tx.Where("id = ? AND is_active = ?", body.TargetID, true).First(&term).Error; err != nil {
				return err
			}
			updates["structure_family_id"] = term.ID
			link := models.MaterialStateStructureFamily{MaterialStateID: proposal.MaterialStateID, StructureFamilyID: term.ID}
			if err := tx.Clauses(clause.OnConflict{DoNothing: true}).Create(&link).Error; err != nil {
				return err
			}
		}
		if err := tx.Model(&proposal).Updates(updates).Error; err != nil {
			return err
		}
		if err := createReviewedClassificationEvidence(tx, actor.ID, &proposal, body.TargetID); err != nil {
			return err
		}
		return createClassificationAudit(tx, actor.ID, proposal.Dimension, "proposal", proposal.ID, "mapped_existing", body.Reason, nil, updates)
	})
	classificationProposalResponse(c, err)
}

func RecommendClassificationProposal(c *gin.Context) {
	actor, ok := currentUserFromContext(c)
	if !ok {
		return
	}
	var body struct {
		ResolutionKind string `json:"resolution_kind"`
		TargetID       *uint  `json:"target_id"`
		Reason         string `json:"reason"`
	}
	if c.ShouldBindJSON(&body) != nil || strings.TrimSpace(body.Reason) == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "审核建议和理由必填"})
		return
	}
	if body.ResolutionKind != "mapped_existing" && body.ResolutionKind != "alias_created" && body.ResolutionKind != "formal_created" && body.ResolutionKind != "rejected" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "分类建议处理方式无效"})
		return
	}
	err := database.DB.Transaction(func(tx *gorm.DB) error {
		var proposal models.ClassificationProposal
		if err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).First(&proposal, c.Param("id")).Error; err != nil {
			return err
		}
		if proposal.Status == "resolved" || proposal.Status == "rejected" {
			return errProposalResolved
		}
		updates := map[string]interface{}{"status": "under_review", "reviewed_by_user_id": actor.ID, "review_note": strings.TrimSpace(body.Reason)}
		if body.ResolutionKind != "" {
			updates["resolution_kind"] = body.ResolutionKind
		}
		if body.TargetID != nil {
			if proposal.Dimension == "material_family" {
				updates["material_family_id"] = *body.TargetID
			} else {
				updates["structure_family_id"] = *body.TargetID
			}
		}
		return tx.Model(&proposal).Updates(updates).Error
	})
	classificationProposalResponse(c, err)
}

var (
	errProposalResolved = errors.New("classification proposal already resolved")
	errAliasConflict    = errors.New("classification alias conflicts with an existing canonical name or alias")
)

func classificationProposalResponse(c *gin.Context, err error) {
	if errors.Is(err, gorm.ErrRecordNotFound) {
		c.JSON(http.StatusNotFound, gin.H{"code": "classification_not_found", "error": "分类建议或目录项不存在"})
		return
	}
	if errors.Is(err, errProposalResolved) {
		c.JSON(http.StatusConflict, gin.H{"code": "proposal_already_resolved", "error": "该建议已进入终态"})
		return
	}
	if errors.Is(err, errAliasConflict) {
		c.JSON(http.StatusConflict, gin.H{"code": "alias_conflict", "error": "分类名称或别名与现有目录冲突"})
		return
	}
	if errors.Is(err, gorm.ErrInvalidData) {
		c.JSON(http.StatusBadRequest, gin.H{"error": "分类建议处理参数无效"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "分类建议处理失败"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "分类建议已处理"})
}

type catalogMutationBody struct {
	Code     string `json:"code"`
	NameZH   string `json:"name"`
	NameEN   string `json:"name_en"`
	IsActive *bool  `json:"is_active"`
	Reason   string `json:"reason"`
}

func CreateClassificationCatalogTerm(c *gin.Context) {
	actor, ok := currentUserFromContext(c)
	if !ok {
		return
	}
	var body catalogMutationBody
	if c.ShouldBindJSON(&body) != nil || strings.TrimSpace(body.Code) == "" || strings.TrimSpace(body.NameZH) == "" || strings.TrimSpace(body.NameEN) == "" || strings.TrimSpace(body.Reason) == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "编码、中英文名称和原因必填"})
		return
	}
	err := database.DB.Transaction(func(tx *gorm.DB) error {
		if c.Param("dimension") == "material_family" {
			normalizedName := normalizeClassificationName(body.NameZH)
			if err := ensureCanonicalNameAvailable(tx, "material_family", normalizedName, 0); err != nil {
				return err
			}
			term := models.MaterialFamily{Code: strings.TrimSpace(body.Code), NameZH: strings.TrimSpace(body.NameZH), NameEN: strings.TrimSpace(body.NameEN), NormalizedName: normalizedName, IsActive: true, CreatedByUserID: &actor.ID}
			if err := tx.Create(&term).Error; err != nil {
				return err
			}
			return createClassificationAudit(tx, actor.ID, "material_family", "term", uint64(term.ID), "created", body.Reason, nil, term)
		}
		if c.Param("dimension") == "structure_family" {
			normalizedName := normalizeClassificationName(body.NameZH)
			if err := ensureCanonicalNameAvailable(tx, "structure_family", normalizedName, 0); err != nil {
				return err
			}
			term := models.StructureFamily{Code: strings.TrimSpace(body.Code), NameZH: strings.TrimSpace(body.NameZH), NameEN: strings.TrimSpace(body.NameEN), NormalizedName: normalizedName, IsActive: true, CreatedByUserID: &actor.ID}
			if err := tx.Create(&term).Error; err != nil {
				return err
			}
			return createClassificationAudit(tx, actor.ID, "structure_family", "term", uint64(term.ID), "created", body.Reason, nil, term)
		}
		return gorm.ErrInvalidData
	})
	catalogMutationResponse(c, err)
}

func UpdateClassificationCatalogTerm(c *gin.Context) {
	actor, ok := currentUserFromContext(c)
	if !ok {
		return
	}
	var body catalogMutationBody
	if c.ShouldBindJSON(&body) != nil || strings.TrimSpace(body.Reason) == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "修改原因必填"})
		return
	}
	updates := make(map[string]interface{})
	if strings.TrimSpace(body.NameZH) != "" {
		updates["name_zh"] = strings.TrimSpace(body.NameZH)
		updates["normalized_name"] = normalizeClassificationName(body.NameZH)
	}
	if strings.TrimSpace(body.NameEN) != "" {
		updates["name_en"] = strings.TrimSpace(body.NameEN)
	}
	if body.IsActive != nil {
		updates["is_active"] = *body.IsActive
	}
	err := updateCatalogTerm(c.Param("dimension"), c.Param("id"), actor.ID, body.Reason, updates)
	catalogMutationResponse(c, err)
}

func updateCatalogTerm(dimension, id string, actorID uint, reason string, updates map[string]interface{}) error {
	if len(updates) == 0 {
		return gorm.ErrInvalidData
	}
	return database.DB.Transaction(func(tx *gorm.DB) error {
		if dimension == "material_family" {
			var term models.MaterialFamily
			if err := tx.First(&term, id).Error; err != nil {
				return err
			}
			before := term
			if normalizedName, ok := updates["normalized_name"].(string); ok {
				if err := ensureCanonicalNameAvailable(tx, dimension, normalizedName, term.ID); err != nil {
					return err
				}
			}
			if err := tx.Model(&term).Updates(updates).Error; err != nil {
				return err
			}
			return createClassificationAudit(tx, actorID, dimension, "term", uint64(term.ID), "updated", reason, before, updates)
		}
		if dimension == "structure_family" {
			var term models.StructureFamily
			if err := tx.First(&term, id).Error; err != nil {
				return err
			}
			before := term
			if normalizedName, ok := updates["normalized_name"].(string); ok {
				if err := ensureCanonicalNameAvailable(tx, dimension, normalizedName, term.ID); err != nil {
					return err
				}
			}
			if err := tx.Model(&term).Updates(updates).Error; err != nil {
				return err
			}
			return createClassificationAudit(tx, actorID, dimension, "term", uint64(term.ID), "updated", reason, before, updates)
		}
		return gorm.ErrInvalidData
	})
}

func MergeClassificationCatalogTerm(c *gin.Context) {
	actor, ok := currentUserFromContext(c)
	if !ok {
		return
	}
	var body struct {
		TargetID uint   `json:"target_id"`
		Reason   string `json:"reason"`
	}
	if c.ShouldBindJSON(&body) != nil || body.TargetID == 0 || strings.TrimSpace(body.Reason) == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "合并目标和原因必填"})
		return
	}
	sourceID, err := strconv.ParseUint(c.Param("id"), 10, 64)
	if err != nil || uint(sourceID) == body.TargetID {
		c.JSON(http.StatusBadRequest, gin.H{"error": "合并目标无效"})
		return
	}
	err = database.DB.Transaction(func(tx *gorm.DB) error {
		if c.Param("dimension") == "material_family" {
			var source, target models.MaterialFamily
			if err := tx.First(&source, uint(sourceID)).Error; err != nil {
				return err
			}
			if err := tx.Where("id = ? AND is_active = ?", body.TargetID, true).First(&target).Error; err != nil {
				return err
			}
			if err := tx.Model(&models.MaterialState{}).Where("material_family_id = ?", source.ID).Update("material_family_id", target.ID).Error; err != nil {
				return err
			}
			if err := tx.Model(&models.MaterialFamilyAlias{}).Where("material_family_id = ?", source.ID).Update("material_family_id", target.ID).Error; err != nil {
				return err
			}
			if err := tx.Model(&models.ClassificationProposal{}).Where("material_family_id = ?", source.ID).Update("material_family_id", target.ID).Error; err != nil {
				return err
			}
			if err := tx.Model(&models.ClassificationEvidence{}).Where("material_family_id = ?", source.ID).Update("material_family_id", target.ID).Error; err != nil {
				return err
			}
			if err := tx.Model(&source).Updates(map[string]interface{}{"is_active": false, "merged_into_id": target.ID}).Error; err != nil {
				return err
			}
			return createClassificationAudit(tx, actor.ID, "material_family", "term", sourceID, "merged", body.Reason, source, target)
		}
		if c.Param("dimension") == "structure_family" {
			var source, target models.StructureFamily
			if err := tx.First(&source, uint(sourceID)).Error; err != nil {
				return err
			}
			if err := tx.Where("id = ? AND is_active = ?", body.TargetID, true).First(&target).Error; err != nil {
				return err
			}
			if err := mergeStructureFamilyLinks(tx, source.ID, target.ID); err != nil {
				return err
			}
			if err := tx.Model(&models.StructureFamilyAlias{}).Where("structure_family_id = ?", source.ID).Update("structure_family_id", target.ID).Error; err != nil {
				return err
			}
			if err := tx.Model(&models.ClassificationProposal{}).Where("structure_family_id = ?", source.ID).Update("structure_family_id", target.ID).Error; err != nil {
				return err
			}
			if err := tx.Model(&models.ClassificationEvidence{}).Where("structure_family_id = ?", source.ID).Update("structure_family_id", target.ID).Error; err != nil {
				return err
			}
			if err := tx.Model(&source).Updates(map[string]interface{}{"is_active": false, "merged_into_id": target.ID}).Error; err != nil {
				return err
			}
			return createClassificationAudit(tx, actor.ID, "structure_family", "term", sourceID, "merged", body.Reason, source, target)
		}
		return gorm.ErrInvalidData
	})
	catalogMutationResponse(c, err)
}

func mergeStructureFamilyLinks(tx *gorm.DB, sourceID, targetID uint) error {
	var sourceLinks []models.MaterialStateStructureFamily
	if err := tx.Where("structure_family_id = ?", sourceID).Find(&sourceLinks).Error; err != nil {
		return err
	}
	for _, sourceLink := range sourceLinks {
		var targetLink models.MaterialStateStructureFamily
		err := tx.Where(
			"material_state_id = ? AND structure_family_id = ?",
			sourceLink.MaterialStateID, targetID,
		).First(&targetLink).Error
		if errors.Is(err, gorm.ErrRecordNotFound) {
			if err := tx.Model(&sourceLink).Update("structure_family_id", targetID).Error; err != nil {
				return err
			}
			continue
		}
		if err != nil {
			return err
		}
		if err := tx.Delete(&sourceLink).Error; err != nil {
			return err
		}
		if sourceLink.IsPrimary && !targetLink.IsPrimary {
			if err := tx.Model(&targetLink).Update("is_primary", true).Error; err != nil {
				return err
			}
		}
	}
	return nil
}

func ResolveClassificationProposal(c *gin.Context) {
	actor, ok := currentUserFromContext(c)
	if !ok {
		return
	}
	var body struct {
		ResolutionKind string `json:"resolution_kind"`
		TargetID       uint   `json:"target_id"`
		Code           string `json:"code"`
		Name           string `json:"name"`
		NameEN         string `json:"name_en"`
		Reason         string `json:"reason"`
	}
	if c.ShouldBindJSON(&body) != nil || strings.TrimSpace(body.Reason) == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "处理方式和原因必填"})
		return
	}
	if body.ResolutionKind != "mapped_existing" && body.ResolutionKind != "alias_created" && body.ResolutionKind != "formal_created" && body.ResolutionKind != "rejected" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "分类建议处理方式无效"})
		return
	}
	err := database.DB.Transaction(func(tx *gorm.DB) error {
		var proposal models.ClassificationProposal
		if err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).First(&proposal, c.Param("id")).Error; err != nil {
			return err
		}
		if proposal.Status == "resolved" || proposal.Status == "rejected" {
			return errProposalResolved
		}
		now := time.Now()
		updates := map[string]interface{}{
			"reviewed_by_user_id": actor.ID, "review_note": strings.TrimSpace(body.Reason),
			"resolved_at": now,
		}
		if body.ResolutionKind == "rejected" {
			updates["status"] = "rejected"
			updates["resolution_kind"] = "rejected"
		} else {
			updates["status"] = "resolved"
			updates["resolution_kind"] = body.ResolutionKind
			if err := resolveProposalTarget(tx, actor.ID, &proposal, &body, updates); err != nil {
				return err
			}
		}
		if err := tx.Model(&proposal).Updates(updates).Error; err != nil {
			return err
		}
		if body.ResolutionKind != "rejected" {
			if err := createReviewedClassificationEvidence(tx, actor.ID, &proposal, body.TargetID); err != nil {
				return err
			}
		}
		return createClassificationAudit(
			tx, actor.ID, proposal.Dimension, "proposal", proposal.ID,
			body.ResolutionKind, body.Reason, proposal, updates,
		)
	})
	classificationProposalResponse(c, err)
}

func createReviewedClassificationEvidence(tx *gorm.DB, actorID uint, proposal *models.ClassificationProposal, targetID uint) error {
	var state models.MaterialState
	if err := tx.Select("id", "paper_id", "paper_revision").First(&state, proposal.MaterialStateID).Error; err != nil {
		return err
	}
	rawValue := proposal.RawName
	evidence := models.ClassificationEvidence{
		PaperID: state.PaperID, PaperRevision: state.PaperRevision,
		MaterialStateID: state.ID, Dimension: proposal.Dimension,
		ProposalID: &proposal.ID, SourceKind: "reviewed", Scope: "current_paper",
		RawValue: &rawValue, ReviewedByUserID: &actorID,
	}
	if proposal.Dimension == "material_family" {
		evidence.MaterialFamilyID = &targetID
	} else {
		evidence.StructureFamilyID = &targetID
	}
	return tx.Create(&evidence).Error
}

func resolveProposalTarget(tx *gorm.DB, actorID uint, proposal *models.ClassificationProposal, body *struct {
	ResolutionKind string `json:"resolution_kind"`
	TargetID       uint   `json:"target_id"`
	Code           string `json:"code"`
	Name           string `json:"name"`
	NameEN         string `json:"name_en"`
	Reason         string `json:"reason"`
}, updates map[string]interface{}) error {
	if body.ResolutionKind == "formal_created" {
		if strings.TrimSpace(body.Code) == "" || strings.TrimSpace(body.Name) == "" || strings.TrimSpace(body.NameEN) == "" {
			return gorm.ErrInvalidData
		}
		if proposal.Dimension == "material_family" {
			normalizedName := normalizeClassificationName(body.Name)
			if err := ensureCanonicalNameAvailable(tx, "material_family", normalizedName, 0); err != nil {
				return err
			}
			term := models.MaterialFamily{Code: strings.TrimSpace(body.Code), NameZH: strings.TrimSpace(body.Name), NameEN: strings.TrimSpace(body.NameEN), NormalizedName: normalizedName, IsActive: true, CreatedByUserID: &actorID}
			if err := tx.Create(&term).Error; err != nil {
				return err
			}
			body.TargetID = term.ID
		} else {
			normalizedName := normalizeClassificationName(body.Name)
			if err := ensureCanonicalNameAvailable(tx, "structure_family", normalizedName, 0); err != nil {
				return err
			}
			term := models.StructureFamily{Code: strings.TrimSpace(body.Code), NameZH: strings.TrimSpace(body.Name), NameEN: strings.TrimSpace(body.NameEN), NormalizedName: normalizedName, IsActive: true, CreatedByUserID: &actorID}
			if err := tx.Create(&term).Error; err != nil {
				return err
			}
			body.TargetID = term.ID
		}
	}
	if body.TargetID == 0 {
		return gorm.ErrInvalidData
	}
	if proposal.Dimension == "material_family" {
		var term models.MaterialFamily
		if err := tx.Where("id = ? AND is_active = ?", body.TargetID, true).First(&term).Error; err != nil {
			return err
		}
		if body.ResolutionKind == "alias_created" {
			normalizedAlias := normalizeClassificationName(proposal.RawName)
			if err := ensureAliasAvailable(tx, "material_family", normalizedAlias, term.ID); err != nil {
				return err
			}
			alias := models.MaterialFamilyAlias{MaterialFamilyID: term.ID, Alias: proposal.RawName, NormalizedAlias: normalizedAlias, Language: "other", CreatedByUserID: &actorID}
			if err := tx.Create(&alias).Error; err != nil {
				return err
			}
		}
		updates["material_family_id"] = term.ID
		return tx.Model(&models.MaterialState{}).Where("id = ?", proposal.MaterialStateID).Update("material_family_id", term.ID).Error
	}
	var term models.StructureFamily
	if err := tx.Where("id = ? AND is_active = ?", body.TargetID, true).First(&term).Error; err != nil {
		return err
	}
	if body.ResolutionKind == "alias_created" {
		normalizedAlias := normalizeClassificationName(proposal.RawName)
		if err := ensureAliasAvailable(tx, "structure_family", normalizedAlias, term.ID); err != nil {
			return err
		}
		alias := models.StructureFamilyAlias{StructureFamilyID: term.ID, Alias: proposal.RawName, NormalizedAlias: normalizedAlias, Language: "other", CreatedByUserID: &actorID}
		if err := tx.Create(&alias).Error; err != nil {
			return err
		}
	}
	updates["structure_family_id"] = term.ID
	link := models.MaterialStateStructureFamily{MaterialStateID: proposal.MaterialStateID, StructureFamilyID: term.ID}
	return tx.Clauses(clause.OnConflict{DoNothing: true}).Create(&link).Error
}

func ensureCanonicalNameAvailable(tx *gorm.DB, dimension, normalizedName string, excludeID uint) error {
	if normalizedName == "" {
		return gorm.ErrInvalidData
	}
	var canonicalCount, aliasCount int64
	if dimension == "material_family" {
		query := tx.Model(&models.MaterialFamily{}).Where("normalized_name = ?", normalizedName)
		if excludeID != 0 {
			query = query.Where("id <> ?", excludeID)
		}
		if err := query.Count(&canonicalCount).Error; err != nil {
			return err
		}
		if err := tx.Model(&models.MaterialFamilyAlias{}).Where("normalized_alias = ?", normalizedName).Count(&aliasCount).Error; err != nil {
			return err
		}
	} else if dimension == "structure_family" {
		query := tx.Model(&models.StructureFamily{}).Where("normalized_name = ?", normalizedName)
		if excludeID != 0 {
			query = query.Where("id <> ?", excludeID)
		}
		if err := query.Count(&canonicalCount).Error; err != nil {
			return err
		}
		if err := tx.Model(&models.StructureFamilyAlias{}).Where("normalized_alias = ?", normalizedName).Count(&aliasCount).Error; err != nil {
			return err
		}
	} else {
		return gorm.ErrInvalidData
	}
	if canonicalCount > 0 || aliasCount > 0 {
		return errAliasConflict
	}
	return nil
}

func ensureAliasAvailable(tx *gorm.DB, dimension, normalizedAlias string, targetID uint) error {
	if normalizedAlias == "" || targetID == 0 {
		return gorm.ErrInvalidData
	}
	var canonicalCount, aliasCount int64
	if dimension == "material_family" {
		if err := tx.Model(&models.MaterialFamily{}).Where("normalized_name = ? AND id <> ?", normalizedAlias, targetID).Count(&canonicalCount).Error; err != nil {
			return err
		}
		if err := tx.Model(&models.MaterialFamilyAlias{}).Where("normalized_alias = ?", normalizedAlias).Count(&aliasCount).Error; err != nil {
			return err
		}
	} else if dimension == "structure_family" {
		if err := tx.Model(&models.StructureFamily{}).Where("normalized_name = ? AND id <> ?", normalizedAlias, targetID).Count(&canonicalCount).Error; err != nil {
			return err
		}
		if err := tx.Model(&models.StructureFamilyAlias{}).Where("normalized_alias = ?", normalizedAlias).Count(&aliasCount).Error; err != nil {
			return err
		}
	} else {
		return gorm.ErrInvalidData
	}
	if canonicalCount > 0 || aliasCount > 0 {
		return errAliasConflict
	}
	return nil
}

func ListClassificationAudits(c *gin.Context) {
	var audits []models.ClassificationAuditEvent
	query := database.DB.Order("created_at DESC").Limit(200)
	if dimension := c.Query("dimension"); dimension != "" {
		query = query.Where("dimension = ?", dimension)
	}
	if err := query.Find(&audits).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "分类审计加载失败"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"items": audits})
}

func createClassificationAudit(tx *gorm.DB, actorID uint, dimension, entityKind string, entityID uint64, action, reason string, before, after interface{}) error {
	beforeJSON, _ := json.Marshal(before)
	afterJSON, _ := json.Marshal(after)
	event := models.ClassificationAuditEvent{ActorUserID: actorID, Dimension: dimension, EntityKind: entityKind, EntityID: entityID, Action: action, Reason: strings.TrimSpace(reason), BeforeJSON: beforeJSON, AfterJSON: afterJSON}
	return tx.Create(&event).Error
}

func catalogMutationResponse(c *gin.Context, err error) {
	if errors.Is(err, gorm.ErrRecordNotFound) {
		c.JSON(http.StatusNotFound, gin.H{"code": "classification_not_found", "error": "分类目录项不存在"})
		return
	}
	if errors.Is(err, gorm.ErrInvalidData) {
		c.JSON(http.StatusBadRequest, gin.H{"error": "分类目录请求无效"})
		return
	}
	if errors.Is(err, errAliasConflict) {
		c.JSON(http.StatusConflict, gin.H{"code": "alias_conflict", "error": "分类名称或别名与现有目录冲突"})
		return
	}
	if err != nil {
		c.JSON(http.StatusConflict, gin.H{"code": "alias_conflict", "error": "分类名称或别名与现有目录冲突"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "分类目录已更新"})
}
