package handlers

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"

	"scwiki/server/database"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

// 本文件的测试全部使用真实插入 + 真实读取，不使用 DryRun 断言 SQL 文本。
// 本 Feature 的故障边界正是「SQL 文本看起来正确但表或列不存在」，
// 字符串断言对该类缺陷完全无感（既有 TestPublicQueriesRequireApprovedPapers 即为例证）。

func paperDetailTestDB(t *testing.T) *gorm.DB {
	t.Helper()
	db, err := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	if err != nil {
		t.Fatal(err)
	}
	if err := db.AutoMigrate(
		&models.Paper{},
		&models.PaperFile{},
		&models.PaperChunk{},
		&models.PaperEvidence{},
		&models.ChemicalSystem{},
		&models.Superconductor{},
		&models.MaterialState{},
		&models.MaterialFamily{},
		&models.PaperMaterialFamily{},
		&models.MaterialStateStructureFamily{},
		&models.StructureFamily{},
		&models.TcResult{},
		&models.CalculationContext{},
		&models.StructureModel{},
		&models.SuperconductorProperty{},
		&models.PropertyDefinition{},
		&models.FormDefinition{},
		&models.PropertyModule{},
		&models.PropertyRecord{},
		&models.PropertyRecordEvidence{},
		&models.PropertyRecordDefinitionEvent{},
		&models.User{},
	); err != nil {
		t.Fatal(err)
	}
	database.DB = db
	return db
}

func strPtr(v string) *string   { return &v }
func f64Ptr(v float64) *float64 { return &v }
func i16Ptr(v int16) *int16     { return &v }

// seedPaperFour 复刻 papers id=4 的真实入库形态（含压强单臂区间与全 NULL 的计算上下文）。
func seedPaperFour(t *testing.T, db *gorm.DB, reviewStatus string) {
	t.Helper()
	if err := db.Create(&models.Paper{
		ID: 4, DOI: strPtr("10.1073/pnas.1704505114"), Title: strPtr("Potential high-Tc superconducting lanthanum and yttrium hydrides"),
		ReviewStatus: reviewStatus, ContentRevision: 1, SuperconductorKind: "conventional",
	}).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&models.ChemicalSystem{
		ID: 1, PaperID: 4, PaperRevision: 1, SystemKey: "H-La", ElementsList: `["H","La"]`, ElementCount: 2,
	}).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&models.Superconductor{
		ID: 1, PaperID: 4, PaperRevision: 1, ChemicalSystemID: 1,
		ChemicalFormula: "LaH10", FormulaNormalized: "LaH10", CompositionKey: "La1H10",
	}).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&models.MaterialState{
		ID: 1, StateKey: "state-lah10-170gpa", PaperID: 4, PaperRevision: 1, SuperconductorID: 1,
		MaterialDimensionality: "bulk",
		CrystalSystem:          "cubic", StateKind: "theoretical",
		PressureValueGPa: f64Ptr(250), PressureMinGPa: f64Ptr(200), PressureMaxGPa: nil,
		PressureRaw:              strPtr("above 200 GPa"),
		ReportedSpaceGroupSymbol: strPtr("Fm-3m"), ReportedSpaceGroupNumber: i16Ptr(225),
	}).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&models.TcResult{
		ID: 1, PaperID: 4, PaperRevision: 1, MaterialStateID: 1,
		ResultKind: "theoretical", TcMethod: "unknown", TcValueK: f64Ptr(274),
		ValueRaw: "274", UnitRaw: "K", SourceFingerprint: "fp-tc-1",
	}).Error; err != nil {
		t.Fatal(err)
	}
	// 两条计算上下文，其中一条全为 NULL——读取侧必须全部返回，不得擅自筛选。
	if err := db.Create(&models.CalculationContext{
		ID: 1, PaperID: 4, PaperRevision: 1, MaterialStateID: 1, PhononNuclearTreatment: "unknown",
	}).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&models.CalculationContext{
		ID: 2, PaperID: 4, PaperRevision: 1, MaterialStateID: 1, PhononNuclearTreatment: "unknown",
		LambdaEP: f64Ptr(2.56), MuStar: f64Ptr(0.1),
	}).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&models.PropertyDefinition{
		ID: 1, Code: "structural_stability", DisplayName: "thermodynamic stability",
		CanonicalUnit: strPtr("meV/atom"), ValueKind: "number", IsActive: true,
	}).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&models.SuperconductorProperty{
		ID: 1, PaperID: 4, PaperRevision: 1, MaterialStateID: 1, PropertyDefinitionID: 1,
		Material: "LaH10", NameRaw: "thermodynamic stability",
		ValueRaw: strPtr("0"), Unit: strPtr("meV/atom"), ValueNumber: f64Ptr(200),
		CanonicalUnit: strPtr("meV/atom"), SourceFingerprint: "fp-prop-1",
	}).Error; err != nil {
		t.Fatal(err)
	}
	moduleDefinition := models.FormDefinition{
		ID: 1, DefinitionKey: "module.superconductive_properties", Version: 1,
		TargetKind: "property_module", ModuleCode: "superconductive_properties",
		CoreSchemaJSON: json.RawMessage(`{}`), JSONSchemaJSON: json.RawMessage(`{}`), UISchemaJSON: json.RawMessage(`{}`),
		Status: "published", Checksum: "module-definition-checksum",
	}
	recordType, methodCode, propertyCode := "predicted_tc", "allen_dynes", "tc"
	recordDefinition := models.FormDefinition{
		ID: 2, DefinitionKey: "record.superconductive_properties.predicted_tc.allen_dynes", Version: 1,
		TargetKind: "property_record", ModuleCode: "superconductive_properties", RecordType: &recordType,
		MethodCode: &methodCode, PropertyCode: &propertyCode,
		CoreSchemaJSON: json.RawMessage(`{"type":"object"}`), JSONSchemaJSON: json.RawMessage(`{"type":"object"}`), UISchemaJSON: json.RawMessage(`{}`),
		Status: "published", Checksum: "record-definition-checksum",
	}
	if err := db.Create([]models.FormDefinition{moduleDefinition, recordDefinition}).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&models.PropertyModule{
		ID: 1, ModuleKey: "module-superconductive-1", PaperID: 4, PaperRevision: 1, MaterialStateID: 1,
		ModuleCode: "superconductive_properties", DefinitionKey: moduleDefinition.DefinitionKey,
		DefinitionVersion: 1, MetadataJSON: json.RawMessage(`{}`),
	}).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&models.PropertyRecord{
		ID: 1, RecordKey: "record-tc-1", PaperID: 4, PaperRevision: 1, MaterialStateID: 1, ModuleID: 1,
		RecordType: "predicted_tc", PropertyCode: "tc", DefinitionID: 2,
		DefinitionKey: recordDefinition.DefinitionKey, DefinitionVersion: 1,
		NameRaw: "critical temperature", ValueKind: "number", ValueRaw: "274 K", ValueNumber: f64Ptr(274),
		UnitRaw: strPtr("K"), CanonicalUnit: strPtr("K"), MethodCode: strPtr("allen_dynes"), IsRepresentative: true,
		PayloadJSON:       json.RawMessage(`{"calculation_conditions":{"calculation_code":"QE"},"parameters":{"mu_star":{"value_number":0.1,"unit":"1"}}}`),
		SourceFingerprint: "property-record-source", RecordChecksum: "property-record-checksum",
	}).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&models.PaperFile{ID: 1, PaperID: 4, PaperRevision: 1, Role: "main", OriginalFilename: "paper.pdf", StoredPath: "/tmp/paper.pdf", SHA256: "paper-file", Size: 1}).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&models.PaperChunk{ID: 1, PaperID: 4, PaperRevision: 1, PaperFileID: 1, ChunkIndex: 0, Content: "Tc is 274 K"}).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&models.PaperEvidence{ID: 1, PaperID: 4, PaperRevision: 1, PaperChunkID: 1, FieldPath: "material_states[0].property_modules[0].records[0]", Quote: "Tc is 274 K"}).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&models.PropertyRecordEvidence{RecordID: 1, PaperEvidenceID: 1, PaperID: 4, PaperRevision: 1, FieldPath: "value", EvidenceRole: "primary"}).Error; err != nil {
		t.Fatal(err)
	}
}

func getPaperDetail(t *testing.T, paperID string) (int, map[string]any) {
	t.Helper()
	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.GET("/papers/:id", GetPaper)
	response := httptest.NewRecorder()
	router.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/papers/"+paperID, nil))
	var body map[string]any
	if response.Body.Len() > 0 {
		if err := json.Unmarshal(response.Body.Bytes(), &body); err != nil {
			t.Fatalf("响应不是 JSON：%s", response.Body.String())
		}
	}
	return response.Code, body
}

func firstMaterialState(t *testing.T, body map[string]any) map[string]any {
	t.Helper()
	states, ok := body["material_states"].([]any)
	if !ok || len(states) == 0 {
		t.Fatalf("material_states 缺失或为空：%#v", body["material_states"])
	}
	state, ok := states[0].(map[string]any)
	if !ok {
		t.Fatalf("material_states[0] 类型异常：%#v", states[0])
	}
	return state
}

// #90 FR-027：详情直接返回绑定定义与 Evidence 的模块化记录。
func TestPaperDetailReturnsTargetPropertyModules(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusApproved)

	code, body := getPaperDetail(t, "4")
	if code != http.StatusOK {
		t.Fatalf("状态码 = %d，响应 = %#v", code, body)
	}
	state := firstMaterialState(t, body)

	modules, ok := state["property_modules"].([]any)
	if !ok || len(modules) != 1 {
		t.Fatalf("property_modules = %#v，期望 1 个", state["property_modules"])
	}
	records := modules[0].(map[string]any)["records"].([]any)
	if len(records) != 1 {
		t.Fatalf("records = %#v，期望 1 条", records)
	}
	tc := records[0].(map[string]any)
	if tc["record_type"] != "predicted_tc" || tc["value_number"] != float64(274) || tc["module_code"] != "superconductive_properties" {
		t.Fatalf("统一 Tc 记录异常：%#v", tc)
	}
	if tc["definition"].(map[string]any)["checksum"] != "record-definition-checksum" {
		t.Fatalf("未返回绑定定义：%#v", tc["definition"])
	}
	if evidences := tc["evidences"].([]any); len(evidences) != 1 || evidences[0].(map[string]any)["evidence"].(map[string]any)["quote"] != "Tc is 274 K" {
		t.Fatalf("Evidence 未完整返回：%#v", tc["evidences"])
	}
	payload := tc["payload"].(map[string]any)
	if payload["calculation_conditions"] == nil || payload["parameters"] == nil {
		t.Fatalf("Conditions/参数未完整返回：%#v", payload)
	}

	if body["tc_max"] != float64(274) {
		t.Fatalf("tc_max = %#v，期望 274", body["tc_max"])
	}
}

func TestPaperDetailTargetPreloadsHaveBoundedQueryCount(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusApproved)

	var queries int64
	if err := db.Callback().Query().Before("gorm:query").Register("issue90:count-queries", func(*gorm.DB) {
		atomic.AddInt64(&queries, 1)
	}); err != nil {
		t.Fatal(err)
	}
	getPaperDetail(t, "4")
	oneStateQueries := atomic.LoadInt64(&queries)

	if err := db.Create(&models.MaterialState{
		ID: 2, StateKey: "state-lah10-200gpa", PaperID: 4, PaperRevision: 1, SuperconductorID: 1,
		MaterialDimensionality: "bulk", CrystalSystem: "cubic", StateKind: "theoretical",
	}).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&models.PropertyModule{
		ID: 2, ModuleKey: "module-superconductive-2", PaperID: 4, PaperRevision: 1, MaterialStateID: 2,
		ModuleCode: "superconductive_properties", DefinitionKey: "module.superconductive_properties",
		DefinitionVersion: 1, MetadataJSON: json.RawMessage(`{}`),
	}).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&models.PropertyRecord{
		ID: 2, RecordKey: "record-tc-2", PaperID: 4, PaperRevision: 1, MaterialStateID: 2, ModuleID: 2,
		RecordType: "predicted_tc", PropertyCode: "tc", DefinitionID: 2,
		DefinitionKey: "record.superconductive_properties.predicted_tc.allen_dynes", DefinitionVersion: 1,
		NameRaw: "critical temperature", ValueKind: "number", ValueRaw: "200 K", ValueNumber: f64Ptr(200),
		MethodCode: strPtr("allen_dynes"), PayloadJSON: json.RawMessage(`{"calculation_conditions":{}}`),
		SourceFingerprint: "property-record-source-2", RecordChecksum: "property-record-checksum-2",
	}).Error; err != nil {
		t.Fatal(err)
	}

	atomic.StoreInt64(&queries, 0)
	getPaperDetail(t, "4")
	twoStateQueries := atomic.LoadInt64(&queries)
	if twoStateQueries != oneStateQueries {
		t.Fatalf("详情查询数随状态/记录数量增长：1 state=%d, 2 states=%d", oneStateQueries, twoStateQueries)
	}
}

// FR-003、FR-004：材料状态的压强区间、空间群等字段必须完整返回，单臂区间的缺失侧保持 null。
func TestPaperDetailReturnsFullMaterialStateFields(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusApproved)

	_, body := getPaperDetail(t, "4")
	state := firstMaterialState(t, body)
	if body["superconductor_kind"] != "conventional" {
		t.Fatalf("论文级 superconductor_kind = %#v，期望 conventional", body["superconductor_kind"])
	}
	if _, exists := state["superconductor_kind"]; exists {
		t.Fatal("material_states 不得返回 superconductor_kind")
	}

	for field, want := range map[string]any{
		"pressure_value_gpa":          float64(250),
		"pressure_min_gpa":            float64(200),
		"pressure_raw":                "above 200 GPa",
		"reported_space_group_symbol": "Fm-3m",
		"reported_space_group_number": float64(225),
		"crystal_system":              "cubic",
		"state_kind":                  "theoretical",
	} {
		if got := state[field]; got != want {
			t.Fatalf("%s = %#v，期望 %#v", field, got, want)
		}
	}

	// 单臂区间：无上限必须是 null，不能是 0——否则「无上限」与「上限为 0」无法区分。
	value, exists := state["pressure_max_gpa"]
	if !exists {
		t.Fatal("pressure_max_gpa 键缺失")
	}
	if value != nil {
		t.Fatalf("pressure_max_gpa = %#v，期望 null", value)
	}

	for _, field := range []string{"pressure_unit_raw", "temperature_value_k", "temperature_raw", "magnetic_field_t", "note"} {
		if _, exists := state[field]; !exists {
			t.Fatalf("%s 键缺失", field)
		}
	}
}

func TestPaperDetailUsesOnlyTargetPropertyRecords(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusApproved)

	_, body := getPaperDetail(t, "4")
	if _, exists := body["key_properties"]; exists {
		t.Fatalf("详情不应输出已退役 key_properties: %#v", body["key_properties"])
	}
	state := firstMaterialState(t, body)
	modules := state["property_modules"].([]any)
	record := modules[0].(map[string]any)["records"].([]any)[0].(map[string]any)
	if record["record_key"] != "record-tc-1" || record["definition_version"] != float64(1) {
		t.Fatalf("目标物性记录异常: %#v", record)
	}
	if record["value_number"] != float64(274) || record["canonical_unit"] != "K" {
		t.Fatalf("目标物性值或单位异常: %#v", record)
	}
}

// 边界：无 Tc 结果与计算上下文时返回空数组，而非缺失键或 null。
func TestPaperDetailUsesEmptyArraysWhenNoScientificData(t *testing.T) {
	db := paperDetailTestDB(t)
	if err := db.Create(&models.Paper{
		ID: 7, Title: strPtr("无科学数据"), ReviewStatus: reviewStatusApproved, ContentRevision: 1,
	}).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&models.Superconductor{
		ID: 2, ChemicalFormula: "H3S", FormulaNormalized: "H3S", CompositionKey: "H3S1",
	}).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&models.MaterialState{
		ID: 9, StateKey: "state-h3s", PaperID: 7, PaperRevision: 1, SuperconductorID: 2,
		MaterialDimensionality: "bulk",
		CrystalSystem:          "unknown", StateKind: "unknown",
	}).Error; err != nil {
		t.Fatal(err)
	}

	_, body := getPaperDetail(t, "7")
	state := firstMaterialState(t, body)
	for _, field := range []string{"property_modules", "structures"} {
		value, exists := state[field]
		if !exists {
			t.Fatalf("%s 键缺失，应为空数组", field)
		}
		items, ok := value.([]any)
		if !ok {
			t.Fatalf("%s = %#v，应为数组而非 null", field, value)
		}
		if len(items) != 0 {
			t.Fatalf("%s 应为空，实际 %#v", field, items)
		}
	}
}

// FR-007：记录搜索必须查询真实存在的表，能返回已批准论文的记录。
func TestApprovedRecordSearchReturnsRealRows(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusApproved)

	var rows []recordSearchRow
	if err := approvedRecordSearchQuery(db).Find(&rows).Error; err != nil {
		t.Fatalf("搜索查询执行失败（修复前为表不存在）：%v", err)
	}
	if len(rows) != 1 {
		t.Fatalf("返回 %d 行，期望 1 行", len(rows))
	}
	item := flatRecordToDict(rows[0])
	if item["tc"] != "274.0 K" {
		t.Fatalf("tc = %#v，期望 274.0 K", item["tc"])
	}
	if item["pressure"] != "250 GPa" {
		t.Fatalf("pressure = %#v，期望 250 GPa", item["pressure"])
	}
	if item["type"] != "theoretical" {
		t.Fatalf("type = %#v，期望 theoretical", item["type"])
	}
	// 修复前 space_group 恒为硬编码 "-"。
	if item["space_group"] != "Fm-3m" {
		t.Fatalf("space_group = %#v，期望 Fm-3m", item["space_group"])
	}
	if item["formula"] != "LaH10" {
		t.Fatalf("formula = %#v，期望 LaH10", item["formula"])
	}
}

// FR-008：压强与类型筛选必须基于材料状态的真实列求值。
func TestApprovedRecordSearchFiltersUseRealColumns(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusApproved)

	var rows []recordSearchRow
	if err := approvedRecordSearchQuery(db).
		Where("material_states.pressure_value_gpa >= ?", 300).
		Find(&rows).Error; err != nil {
		t.Fatal(err)
	}
	if len(rows) != 0 {
		t.Fatalf("压强下限 300 应排除 250 GPa 的记录，实际返回 %d 行", len(rows))
	}

	rows = nil
	if err := approvedRecordSearchQuery(db).
		Where("material_states.pressure_value_gpa >= ?", 200).
		Where("material_states.state_kind = ?", "theoretical").
		Find(&rows).Error; err != nil {
		t.Fatal(err)
	}
	if len(rows) != 1 {
		t.Fatalf("压强与类型均匹配时应返回 1 行，实际 %d 行", len(rows))
	}

	rows = nil
	if err := approvedRecordSearchQuery(db).
		Where(searchTcValueExpr+" >= ?", 300).
		Find(&rows).Error; err != nil {
		t.Fatal(err)
	}
	if len(rows) != 0 {
		t.Fatalf("Tc 下限 300 应排除 274 K 的记录，实际返回 %d 行", len(rows))
	}
}

// 既有公开数据边界不得放宽：未批准论文不进入搜索结果。
func TestApprovedRecordSearchExcludesUnapprovedPapers(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, "pending")

	var rows []recordSearchRow
	if err := approvedRecordSearchQuery(db).Find(&rows).Error; err != nil {
		t.Fatal(err)
	}
	if len(rows) != 0 {
		t.Fatalf("pending 论文不应出现在搜索结果中，实际返回 %d 行", len(rows))
	}
}

// #90：管理详情与公开详情使用同一目标模块图。
func TestAdminPaperDetailPreloadsScientificData(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusPending)

	if err := db.Create(&models.StructureModel{
		ID: 1, PaperID: 4, PaperRevision: 1, MaterialStateID: 1,
		StructureFormat: "cif", StructureText: "data_LaH10\n_cell_length_a 5.0",
		StructureHash: "hash-structure-1", NuclearTreatment: "unknown",
	}).Error; err != nil {
		t.Fatal(err)
	}

	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.GET("/admin/papers/:id", GetPaperDetail)
	response := httptest.NewRecorder()
	router.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/admin/papers/4", nil))
	if response.Code != http.StatusOK {
		t.Fatalf("状态码 = %d，响应 = %s", response.Code, response.Body.String())
	}
	var body map[string]any
	if err := json.Unmarshal(response.Body.Bytes(), &body); err != nil {
		t.Fatalf("响应不是 JSON：%s", response.Body.String())
	}
	if body["superconductor_kind"] != "conventional" {
		t.Fatalf("管理端论文级 superconductor_kind = %#v，期望 conventional", body["superconductor_kind"])
	}
	state := firstMaterialState(t, body)
	if _, exists := state["superconductor_kind"]; exists {
		t.Fatal("管理端 material_states 不得返回 superconductor_kind")
	}

	if modules, ok := state["property_modules"].([]any); !ok || len(modules) == 0 {
		t.Fatalf("property_modules 未预加载：%#v", state["property_modules"])
	}
	if structures, ok := state["structures"].([]any); !ok || len(structures) == 0 {
		t.Fatalf("structures 未预加载：%#v", state["structures"])
	}
}

// Issue #79：详情响应（管理端与公开）的论文级 material_families 必须返回
// name_en——英文界面据此显示规范英文名（如「单质超导体」→ Elemental superconductor）。
// 修复前：管理端详情走模型序列化，NameEN 是 json:"-"；公开详情 materialStatesToDict
// 只回 name。两者都会让英文界面拿不到英文名而回退中文。
func TestPaperDetailReturnsFamilyNameEn(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusApproved)

	if err := db.Create(&models.MaterialFamily{
		ID: 8, Code: "custom_elemental", NameZH: "单质超导体", NameEN: "Elemental superconductor",
		NormalizedName: "单质超导体",
	}).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&models.PaperMaterialFamily{
		PaperID: 4, PaperRevision: 1, MaterialFamilyID: 8,
	}).Error; err != nil {
		t.Fatal(err)
	}

	assertFamilyNameEn := func(t *testing.T, label string, body map[string]any) {
		t.Helper()
		families, ok := body["material_families"].([]any)
		if !ok || len(families) != 1 {
			t.Fatalf("%s material_families 缺失或类型异常：%#v", label, body["material_families"])
		}
		family := families[0].(map[string]any)
		if family["name"] != "单质超导体" || family["name_en"] != "Elemental superconductor" {
			t.Fatalf("%s material_families = %#v，期望 name=单质超导体 且 name_en=Elemental superconductor", label, family)
		}
	}

	// 公开详情（materialStatesToDict）
	_, body := getPaperDetail(t, "4")
	assertFamilyNameEn(t, "公开详情", body)

	// 管理端详情（模型序列化）
	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.GET("/admin/papers/:id", GetPaperDetail)
	response := httptest.NewRecorder()
	router.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/admin/papers/4", nil))
	if response.Code != http.StatusOK {
		t.Fatalf("管理端详情状态码 = %d，响应 = %s", response.Code, response.Body.String())
	}
	var adminBody map[string]any
	if err := json.Unmarshal(response.Body.Bytes(), &adminBody); err != nil {
		t.Fatalf("管理端详情响应不是 JSON：%s", response.Body.String())
	}
	assertFamilyNameEn(t, "管理端详情", adminBody)
}

// #87：上传者只在管理端论文列表展示；详情接口不得重复返回该字段或物性记录统计。
func TestAdminPaperDetailOmitsUploaderAndRecordCount(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusPending)
	if err := db.Create(&models.User{ID: 9, Email: "author@example.test", Username: "author"}).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Model(&models.Paper{}).Where("id = ?", 4).Update("uploaded_by_user_id", 9).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&models.SuperconductorProperty{
		PaperID: 4, PaperRevision: 2, MaterialStateID: 1, PropertyDefinitionID: 1,
		Material: "LaH10", NameRaw: "legacy", ValueRaw: strPtr("1"), SourceFingerprint: "legacy-property",
	}).Error; err != nil {
		t.Fatal(err)
	}

	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.GET("/admin/papers/:id", GetPaperDetail)
	response := httptest.NewRecorder()
	router.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/admin/papers/4", nil))
	if response.Code != http.StatusOK {
		t.Fatalf("状态码 = %d，响应 = %s", response.Code, response.Body.String())
	}
	var body map[string]any
	if err := json.Unmarshal(response.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if _, exists := body["uploader_name"]; exists {
		t.Fatalf("详情响应不应包含 uploader_name：%#v", body["uploader_name"])
	}
	if _, exists := body["record_count"]; exists {
		t.Fatalf("响应不应包含 record_count：%#v", body["record_count"])
	}
}

func TestAdminPaperDetailOmitsUploaderAndRecordCountForImportedPaper(t *testing.T) {
	db := paperDetailTestDB(t)
	if err := db.Create(&models.Paper{ID: 8, Title: strPtr("历史导入"), ReviewStatus: reviewStatusPending, ContentRevision: 1}).Error; err != nil {
		t.Fatal(err)
	}
	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.GET("/admin/papers/:id", GetPaperDetail)
	response := httptest.NewRecorder()
	router.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/admin/papers/8", nil))
	if response.Code != http.StatusOK {
		t.Fatalf("状态码 = %d，响应 = %s", response.Code, response.Body.String())
	}
	var body map[string]any
	if err := json.Unmarshal(response.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if _, exists := body["uploader_name"]; exists {
		t.Fatalf("详情响应不应包含 uploader_name：%#v", body["uploader_name"])
	}
	if _, exists := body["record_count"]; exists {
		t.Fatalf("响应不应包含 record_count：%#v", body["record_count"])
	}
}

func TestAdminPaperListReturnsUploaderWithoutRecordCount(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusPending)
	if err := db.Create(&models.User{ID: 9, Email: "author@example.test", Username: "author"}).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Model(&models.Paper{}).Where("id = ?", 4).Update("uploaded_by_user_id", 9).Error; err != nil {
		t.Fatal(err)
	}

	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.GET("/admin/papers/all", GetPapers)
	response := httptest.NewRecorder()
	router.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/admin/papers/all", nil))
	if response.Code != http.StatusOK {
		t.Fatalf("状态码 = %d，响应 = %s", response.Code, response.Body.String())
	}
	var body struct {
		Items []map[string]any `json:"items"`
	}
	if err := json.Unmarshal(response.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if len(body.Items) != 1 {
		t.Fatalf("items = %#v，期望 1 条", body.Items)
	}
	if body.Items[0]["uploader_name"] != "author" {
		t.Fatalf("uploader_name = %#v，期望 author", body.Items[0]["uploader_name"])
	}
	if _, exists := body.Items[0]["record_count"]; exists {
		t.Fatalf("列表响应不应包含 record_count：%#v", body.Items[0]["record_count"])
	}
}

func TestCorePaperHandlersWorkAfterLegacyPropertyContract(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusApproved)
	if err := db.Create(&models.User{ID: 9, Email: "author@example.test", Username: "author"}).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Model(&models.Paper{}).Where("id = ?", 4).Update("uploaded_by_user_id", 9).Error; err != nil {
		t.Fatal(err)
	}
	for _, legacy := range []any{
		&models.TcResult{}, &models.SuperconductorProperty{},
		&models.CalculationContext{}, &models.ExperimentalContext{},
	} {
		if db.Migrator().HasTable(legacy) {
			if err := db.Migrator().DropTable(legacy); err != nil {
				t.Fatalf("退役 %T 失败: %v", legacy, err)
			}
		}
	}

	gin.SetMode(gin.TestMode)
	tests := []struct {
		name      string
		route     string
		path      string
		run       gin.HandlerFunc
		wantTotal bool
	}{
		{name: "公开详情", route: "/papers/:id", path: "/papers/4", run: GetPaper},
		{name: "公开列表", route: "/papers", path: "/papers", run: ListPapers, wantTotal: true},
		{name: "管理详情", route: "/admin/papers/:id", path: "/admin/papers/4", run: GetPaperDetail},
		{name: "管理材料筛选", route: "/admin/papers/all", path: "/admin/papers/all?material=LaH10", run: GetPapers, wantTotal: true},
		{name: "我的上传", route: "/papers/my-uploads", path: "/papers/my-uploads", run: func(c *gin.Context) {
			c.Set("user_email", "author@example.test")
			GetMyUploads(c)
		}, wantTotal: true},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			router := gin.New()
			router.GET(test.route, test.run)
			response := httptest.NewRecorder()
			router.ServeHTTP(response, httptest.NewRequest(http.MethodGet, test.path, nil))
			if response.Code != http.StatusOK {
				t.Fatalf("status=%d body=%s", response.Code, response.Body.String())
			}
			if strings.Contains(response.Body.String(), "key_properties") {
				t.Fatalf("响应仍暴露旧契约: %s", response.Body.String())
			}
			if test.wantTotal {
				var body map[string]any
				if err := json.Unmarshal(response.Body.Bytes(), &body); err != nil {
					t.Fatal(err)
				}
				if body["total"] != float64(1) {
					t.Fatalf("total=%#v body=%s", body["total"], response.Body.String())
				}
			}
		})
	}
}

func TestUpdatePaperRejectsLegacyPropertyContractWithoutQueryingLegacyTable(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusApproved)
	if err := db.Migrator().DropTable(&models.SuperconductorProperty{}); err != nil {
		t.Fatal(err)
	}

	router := gin.New()
	router.PUT("/admin/papers/:id", UpdatePaper)
	request := httptest.NewRequest(http.MethodPut, "/admin/papers/4", strings.NewReader(`{"key_properties":[]}`))
	request.Header.Set("Content-Type", "application/json")
	response := httptest.NewRecorder()
	router.ServeHTTP(response, request)
	if response.Code != http.StatusBadRequest {
		t.Fatalf("status=%d body=%s", response.Code, response.Body.String())
	}
	var body map[string]any
	if err := json.Unmarshal(response.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body["code"] != "legacy_property_contract" {
		t.Fatalf("code=%#v", body["code"])
	}
}
