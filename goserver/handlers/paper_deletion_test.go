package handlers

import (
	"testing"

	"scwiki/server/database"
	"scwiki/server/models"

	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

// newDeletionTestDB 建内存库并接管全局 DB；用 Cleanup 还原，避免污染同包其他测试。
//
// 必须开启 foreign_keys：SQLite 默认不强制外键，关闭时删除顺序写错也能通过，
// 曾因此漏掉线上 Error 1451（superconductor_properties 排在 calculation_contexts 之后）。
func newDeletionTestDB(t *testing.T) *gorm.DB {
	t.Helper()
	db, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	if err != nil {
		t.Fatalf("打开内存库失败: %v", err)
	}
	if err := db.Exec("PRAGMA foreign_keys = ON").Error; err != nil {
		t.Fatalf("开启外键强制失败: %v", err)
	}
	var fkOn int
	if err := db.Raw("PRAGMA foreign_keys").Scan(&fkOn).Error; err != nil || fkOn != 1 {
		t.Fatalf("外键强制未生效（fkOn=%d, err=%v），测试无法覆盖顺序错误", fkOn, err)
	}

	if err := db.AutoMigrate(
		&models.Paper{},
		&models.KeyProperty{},
		&models.MaterialState{},
		&models.TcResult{},
		&models.CalculationContext{},
		&models.ExperimentalContext{},
		&models.StructureModel{},
		&models.PaperChunk{},
		&models.PaperEvidence{},
		&models.PaperHistoryEvent{},
		&models.Superconductor{},
		&models.PropertyDefinition{},
		// 以下 5 张表曾被 spec 漏掉，导致真实库删除失败
		&models.PaperFile{},
		&models.TcResultEvidence{},
		&models.StructureModelEvidence{},
		&models.SuperconductorPropertyEvidence{},
		&models.MaterialStateStructureFamily{},
		&models.PaperReferenceExtraction{},
		&models.PaperReference{},
		&models.PaperGraphMark{},
		&models.PaperMaterialFamily{},
	); err != nil {
		t.Fatalf("迁移失败: %v", err)
	}

	prev := database.DB
	database.DB = db
	t.Cleanup(func() { database.DB = prev })
	return db
}

// seedPaperGraph 造一篇带完整关联数据的论文，返回 paperID 与共享的 superconductorID。
func seedPaperGraph(t *testing.T, db *gorm.DB, doi string) (uint, uint) {
	t.Helper()

	sc := models.Superconductor{
		ChemicalFormula:   "H3S",
		FormulaNormalized: "H3S-" + doi,
		CompositionKey:    "H3S-" + doi,
		DisplayName:       "H3S",
		ElementsList:      `["H","S"]`,
		Composition:       `{"H":3,"S":1}`,
		ElementRatio:      `{"H":0.75,"S":0.25}`,
	}
	if err := db.Create(&sc).Error; err != nil {
		t.Fatalf("创建 superconductor 失败: %v", err)
	}

	// property_definitions 是 superconductor_properties 的外键父表，必须先建。
	propDef := models.PropertyDefinition{
		Code: "tc-" + doi, DisplayName: "Tc", ValueKind: "number", IsActive: true,
	}
	if err := db.Create(&propDef).Error; err != nil {
		t.Fatalf("创建 property_definition 失败: %v", err)
	}

	paper := models.Paper{DOI: strPtr(doi), Title: strPtr("Test " + doi), ReviewStatus: "pending"}
	if err := db.Create(&paper).Error; err != nil {
		t.Fatalf("创建 paper 失败: %v", err)
	}

	state := models.MaterialState{PaperID: paper.ID, PaperRevision: 1, SuperconductorID: sc.ID}
	if err := db.Create(&state).Error; err != nil {
		t.Fatalf("创建 material_state 失败: %v", err)
	}

	// paper_chunks 外键指向 paper_files，必须先建父行。
	file := models.PaperFile{PaperID: paper.ID, PaperRevision: 1}
	if err := db.Create(&file).Error; err != nil {
		t.Fatalf("创建 paper_file 失败: %v", err)
	}

	// chunk_index 带唯一约束，按 paper.ID 错开避免多篇论文互撞。
	chunk := models.PaperChunk{
		PaperID: paper.ID, PaperRevision: 1,
		PaperFileID: file.ID, ChunkIndex: int(paper.ID),
	}
	if err := db.Create(&chunk).Error; err != nil {
		t.Fatalf("创建 paper_chunk 失败: %v", err)
	}

	evidence := models.PaperEvidence{
		PaperID: paper.ID, PaperRevision: 1, PaperChunkID: chunk.ID,
		FieldPath: "abstract", Quote: "q",
	}
	if err := db.Create(&evidence).Error; err != nil {
		t.Fatalf("创建 paper_evidence 失败: %v", err)
	}

	structure := models.StructureModel{PaperID: paper.ID, PaperRevision: 1, MaterialStateID: state.ID}
	if err := db.Create(&structure).Error; err != nil {
		t.Fatalf("创建 structure_model 失败: %v", err)
	}

	calcCtx := models.CalculationContext{PaperID: paper.ID, PaperRevision: 1, MaterialStateID: state.ID}
	if err := db.Create(&calcCtx).Error; err != nil {
		t.Fatalf("创建 calculation_context 失败: %v", err)
	}

	tcResult := models.TcResult{
		PaperID: paper.ID, PaperRevision: 1, MaterialStateID: state.ID,
		CalculationContextID: &calcCtx.ID,
		ResultKind:           "theoretical", TcMethod: "eliashberg", ValueRaw: "200 K",
	}
	if err := db.Create(&tcResult).Error; err != nil {
		t.Fatalf("创建 tc_result 失败: %v", err)
	}

	// superconductor_properties 同时引用 calculation_contexts / structure_models /
	// material_states——正是它让「先删 contexts」的错误顺序触发 Error 1451。
	prop := models.KeyProperty{
		PaperID: paper.ID, PaperRevision: 1, MaterialStateID: state.ID,
		CalculationContextID: &calcCtx.ID, StructureID: &structure.ID,
		PropertyDefinitionID: propDef.ID, Material: "H3S", NameRaw: "Tc",
		ValueRaw: strPtr("200"), SourceFingerprint: "fp-" + doi,
	}
	if err := db.Create(&prop).Error; err != nil {
		t.Fatalf("创建 superconductor_property 失败: %v", err)
	}

	rows := []any{
		&models.ExperimentalContext{PaperID: paper.ID, PaperRevision: 1, MaterialStateID: state.ID, TcCriterion: "onset"},
		&models.PaperHistoryEvent{PaperID: paper.ID, PaperRevision: 1, EventType: paperHistoryUploaded},
		// 证据连接表：引用 tc_results / structure_models / paper_evidences
		&models.TcResultEvidence{TcResultID: tcResult.ID, PaperEvidenceID: evidence.ID, PaperID: paper.ID, PaperRevision: 1},
		&models.StructureModelEvidence{StructureID: structure.ID, PaperEvidenceID: evidence.ID, PaperID: paper.ID, PaperRevision: 1},
		&models.SuperconductorPropertyEvidence{SuperconductorPropertyID: prop.ID, PaperEvidenceID: evidence.ID, PaperID: paper.ID, PaperRevision: 1},
	}
	for _, row := range rows {
		if err := db.Create(row).Error; err != nil {
			t.Fatalf("创建关联数据 %T 失败: %v", row, err)
		}
	}

	if err := db.Create(&models.PaperReferenceExtraction{
		PaperID: paper.ID, PaperRevision: 1, Status: "succeeded", ParserName: "grobid",
	}).Error; err != nil {
		t.Fatalf("创建引用解析状态失败: %v", err)
	}
	if err := db.Create(&models.PaperReference{
		PaperID: paper.ID, PaperRevision: 1, ReferenceIndex: 0,
		RawCitation: "self reference", CitedPaperID: &paper.ID,
		MatchStatus: "matched",
	}).Error; err != nil {
		t.Fatalf("创建引用记录失败: %v", err)
	}
	if err := db.Create(&models.PaperGraphMark{
		PaperID: paper.ID, MarkType: "origin", CreatedByUserID: 1,
	}).Error; err != nil {
		t.Fatalf("创建图谱里程碑失败: %v", err)
	}

	return paper.ID, sc.ID
}

// countBy 返回某张表下指定 paper 的残留行数。
func countBy(t *testing.T, db *gorm.DB, model any, paperID uint) int64 {
	t.Helper()
	var n int64
	if err := db.Model(model).Where("paper_id = ?", paperID).Count(&n).Error; err != nil {
		t.Fatalf("统计 %T 失败: %v", model, err)
	}
	return n
}

// TestCascadeDeleteInDBRemovesEveryRelation 覆盖 FR-001：9 张关联表全部清空。
func TestCascadeDeleteInDBRemovesEveryRelation(t *testing.T) {
	db := newDeletionTestDB(t)
	paperID, scID := seedPaperGraph(t, db, "10.1021/cascade.1")

	if err := cascadeDeleteInDB(db, paperID); err != nil {
		t.Fatalf("级联删除失败: %v", err)
	}

	relations := []struct {
		name  string
		model any
	}{
		{"superconductor_properties", &models.KeyProperty{}},
		{"material_states", &models.MaterialState{}},
		{"tc_results", &models.TcResult{}},
		{"calculation_contexts", &models.CalculationContext{}},
		{"experimental_contexts", &models.ExperimentalContext{}},
		{"structure_models", &models.StructureModel{}},
		{"paper_chunks", &models.PaperChunk{}},
		{"paper_evidences", &models.PaperEvidence{}},
		{"paper_history_events", &models.PaperHistoryEvent{}},
		{"paper_files", &models.PaperFile{}},
		{"tc_result_evidences", &models.TcResultEvidence{}},
		{"structure_model_evidences", &models.StructureModelEvidence{}},
		{"superconductor_property_evidences", &models.SuperconductorPropertyEvidence{}},
		{"paper_reference_extractions", &models.PaperReferenceExtraction{}},
		{"paper_references", &models.PaperReference{}},
		{"paper_graph_marks", &models.PaperGraphMark{}},
	}
	for _, rel := range relations {
		if n := countBy(t, db, rel.model, paperID); n != 0 {
			t.Errorf("%s 应清空，实际残留 %d 行", rel.name, n)
		}
	}

	var papers int64
	db.Model(&models.Paper{}).Where("id = ?", paperID).Count(&papers)
	if papers != 0 {
		t.Errorf("papers 应删除，实际残留 %d 行", papers)
	}

	// FR-005：superconductors 可被多篇论文共享，不得随论文删除。
	var scCount int64
	db.Model(&models.Superconductor{}).Where("id = ?", scID).Count(&scCount)
	if scCount != 1 {
		t.Errorf("superconductors 记录应保留，实际 %d 行", scCount)
	}
}

// TestCascadeDeleteOnlyTargetsRequestedPaper 确认删除不越界影响其他论文。
func TestCascadeDeleteOnlyTargetsRequestedPaper(t *testing.T) {
	db := newDeletionTestDB(t)
	target, _ := seedPaperGraph(t, db, "10.1021/cascade.target")
	bystander, _ := seedPaperGraph(t, db, "10.1021/cascade.bystander")

	if err := cascadeDeleteInDB(db, target); err != nil {
		t.Fatalf("级联删除失败: %v", err)
	}

	if n := countBy(t, db, &models.TcResult{}, bystander); n != 1 {
		t.Errorf("无关论文的 tc_results 应保留 1 行，实际 %d 行", n)
	}
	var papers int64
	db.Model(&models.Paper{}).Where("id = ?", bystander).Count(&papers)
	if papers != 1 {
		t.Errorf("无关论文应保留，实际 %d 行", papers)
	}
}

// TestCascadeDeleteRollsBackOnFailure 覆盖 FR-006：中途失败必须整体回滚。
// 手法：删掉 papers 表使最后一步必然失败，验证先删的关联数据被还原。
func TestCascadeDeleteRollsBackOnFailure(t *testing.T) {
	db := newDeletionTestDB(t)
	paperID, _ := seedPaperGraph(t, db, "10.1021/cascade.rollback")

	if err := db.Migrator().DropTable(&models.Paper{}); err != nil {
		t.Fatalf("删除 papers 表失败: %v", err)
	}

	err := db.Transaction(func(tx *gorm.DB) error {
		return cascadeDeleteInDB(tx, paperID)
	})
	if err == nil {
		t.Fatal("papers 表缺失时应返回错误")
	}

	// 事务回滚后，先删掉的关联数据必须复原。
	if n := countBy(t, db, &models.TcResult{}, paperID); n != 1 {
		t.Errorf("回滚后 tc_results 应恢复为 1 行，实际 %d 行", n)
	}
	if n := countBy(t, db, &models.MaterialState{}, paperID); n != 1 {
		t.Errorf("回滚后 material_states 应恢复为 1 行，实际 %d 行", n)
	}
}

// TestCascadeDeletePaperMissingReturnsSentinel 覆盖 FR-009：不存在时返回可判定的哨兵错误。
func TestCascadeDeletePaperMissingReturnsSentinel(t *testing.T) {
	newDeletionTestDB(t)

	err := CascadeDeletePaper(99999, "")
	if err == nil {
		t.Fatal("删除不存在的论文应返回错误")
	}
	if !errorsIsPaperNotFound(err) {
		t.Errorf("应返回 ErrPaperNotFound，实际: %v", err)
	}
}

func errorsIsPaperNotFound(err error) bool {
	return err == ErrPaperNotFound
}
