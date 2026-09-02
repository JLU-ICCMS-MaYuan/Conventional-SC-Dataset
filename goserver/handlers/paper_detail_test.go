package handlers

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
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
		&models.Superconductor{},
		&models.MaterialState{},
		&models.MaterialFamily{},
		&models.MaterialStateStructureFamily{},
		&models.StructureFamily{},
		&models.TcResult{},
		&models.CalculationContext{},
		&models.StructureModel{},
		&models.SuperconductorProperty{},
		&models.PropertyDefinition{},
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
		ReviewStatus: reviewStatus, ContentRevision: 1,
	}).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&models.Superconductor{
		ID: 1, ChemicalFormula: "LaH10", FormulaNormalized: "LaH10", CompositionKey: "La1H10",
	}).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&models.MaterialState{
		ID: 1, PaperID: 4, PaperRevision: 1, SuperconductorID: 1,
		MaterialDimensionality: "bulk", SuperconductorKind: "unknown",
		CrystalSystem: "cubic", StateKind: "theoretical",
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

// FR-001、FR-002：Tc 结果与计算上下文必须随详情返回。
func TestPaperDetailReturnsTcResultsAndCalculationContexts(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusApproved)

	code, body := getPaperDetail(t, "4")
	if code != http.StatusOK {
		t.Fatalf("状态码 = %d，响应 = %#v", code, body)
	}
	state := firstMaterialState(t, body)

	tcResults, ok := state["tc_results"].([]any)
	if !ok || len(tcResults) != 1 {
		t.Fatalf("tc_results = %#v，期望 1 条", state["tc_results"])
	}
	tc := tcResults[0].(map[string]any)
	if tc["tc_value_k"] != float64(274) {
		t.Fatalf("tc_value_k = %#v，期望 274", tc["tc_value_k"])
	}
	if tc["result_kind"] != "theoretical" || tc["unit_raw"] != "K" {
		t.Fatalf("Tc 结果元数据异常：%#v", tc)
	}

	contexts, ok := state["calculation_contexts"].([]any)
	if !ok || len(contexts) != 2 {
		t.Fatalf("calculation_contexts = %#v，期望 2 条（含全 NULL 的一条）", state["calculation_contexts"])
	}
	var foundLambda bool
	for _, item := range contexts {
		ctx := item.(map[string]any)
		if ctx["lambda_ep"] == float64(2.56) && ctx["mu_star"] == float64(0.1) {
			foundLambda = true
		}
	}
	if !foundLambda {
		t.Fatalf("未找到 lambda_ep=2.56 且 mu_star=0.1 的计算上下文：%#v", contexts)
	}

	// tc_max 需由 tc_results 聚合，而非已迁移走的普通物性表。
	if body["tc_max"] != float64(274) {
		t.Fatalf("tc_max = %#v，期望 274", body["tc_max"])
	}
}

// FR-003、FR-004：材料状态的压强区间、空间群等字段必须完整返回，单臂区间的缺失侧保持 null。
func TestPaperDetailReturnsFullMaterialStateFields(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusApproved)

	_, body := getPaperDetail(t, "4")
	state := firstMaterialState(t, body)

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

// FR-005：物性名称取规范定义的展示名。
func TestPaperDetailPropertyNameComesFromDefinition(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusApproved)

	_, body := getPaperDetail(t, "4")
	properties, ok := body["key_properties"].([]any)
	if !ok || len(properties) != 1 {
		t.Fatalf("key_properties = %#v，期望 1 条", body["key_properties"])
	}
	property := properties[0].(map[string]any)
	if property["name"] != "thermodynamic stability" {
		t.Fatalf("name = %#v，期望 thermodynamic stability", property["name"])
	}
	if property["value_number"] != float64(200) || property["unit"] != "meV/atom" {
		t.Fatalf("物性数值或单位异常：%#v", property)
	}
	// 原文值与解析值可能不一致（真实数据即为 "0" 与 200），两者都需返回，由展示层裁决优先级。
	if property["value_raw"] != "0" {
		t.Fatalf("value_raw = %#v，期望 \"0\"", property["value_raw"])
	}
}

// FR-005 回退分支：规范定义的展示名缺失时回退原文名，不得返回空字符串。
func TestPaperDetailPropertyNameFallsBackToNameRaw(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusApproved)
	if err := db.Model(&models.PropertyDefinition{}).Where("id = ?", 1).
		Update("display_name", "").Error; err != nil {
		t.Fatal(err)
	}

	_, body := getPaperDetail(t, "4")
	property := body["key_properties"].([]any)[0].(map[string]any)
	if property["name"] != "thermodynamic stability" {
		t.Fatalf("name = %#v，期望回退到 name_raw", property["name"])
	}
}

// FR-006：响应不得包含永不读库的兼容字段。
func TestPaperDetailOmitsPhantomProperties(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusApproved)

	_, body := getPaperDetail(t, "4")
	property := body["key_properties"].([]any)[0].(map[string]any)

	for _, field := range []string{
		"superconductor_id", "name_note", "pressure_gpa", "temperature_k", "condition_json",
		"is_primary", "superconductor_type", "article_type", "source_label",
		"structure_text", "structure_format",
	} {
		if _, exists := property[field]; exists {
			t.Fatalf("物性仍输出恒零值字段 %s：%#v", field, property)
		}
	}
}

// FR-006 的判定依据：字段值必须随库内容变化，否则即为恒零值字段。
func TestPaperDetailPropertyNameTracksDatabase(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusApproved)

	if err := db.Model(&models.PropertyDefinition{}).Where("id = ?", 1).
		Update("display_name", "formation enthalpy").Error; err != nil {
		t.Fatal(err)
	}
	_, body := getPaperDetail(t, "4")
	property := body["key_properties"].([]any)[0].(map[string]any)
	if property["name"] != "formation enthalpy" {
		t.Fatalf("name = %#v，未随数据库变化", property["name"])
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
		ID: 9, PaperID: 7, PaperRevision: 1, SuperconductorID: 2,
		MaterialDimensionality: "bulk", SuperconductorKind: "unknown",
		CrystalSystem: "unknown", StateKind: "unknown",
	}).Error; err != nil {
		t.Fatal(err)
	}

	_, body := getPaperDetail(t, "7")
	state := firstMaterialState(t, body)
	for _, field := range []string{"tc_results", "calculation_contexts"} {
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
		Where("tc_results.tc_value_k >= ?", 300).
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

// FR-009：管理员物性更新写入真实列并可读回；无对应列的字段不被接受。
func TestUpdateKeyPropertiesWritesRealColumns(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusApproved)

	err := updateKeyProperties(db, 4, []map[string]interface{}{{
		"id":             float64(1),
		"name_raw":       "formation enthalpy",
		"value_number":   float64(150),
		"unit":           "meV/atom",
		"condition_note": "复核后修正",
		// 以下字段在当前数据模型中没有对应列，必须不被接受（而非静默丢弃）。
		"pressure_gpa":   float64(300),
		"is_primary":     true,
		"structure_text": "POSCAR...",
		"article_type":   "theoretical",
	}})
	if err != nil {
		t.Fatalf("更新失败：%v", err)
	}

	var property models.SuperconductorProperty
	if err := db.First(&property, 1).Error; err != nil {
		t.Fatal(err)
	}
	if property.NameRaw != "formation enthalpy" {
		t.Fatalf("name_raw = %q，未落库", property.NameRaw)
	}
	if property.ValueNumber == nil || *property.ValueNumber != 150 {
		t.Fatalf("value_number = %#v，未落库", property.ValueNumber)
	}
	if property.ConditionNote == nil || *property.ConditionNote != "复核后修正" {
		t.Fatalf("condition_note = %#v，未落库", property.ConditionNote)
	}
}

// FR-009 新建路径：只写入真实列，不再经 gorm:"-" 静默丢弃。
func TestNewKeyPropertyOnlyAcceptsRealColumns(t *testing.T) {
	kp := newKeyProperty(4, map[string]interface{}{
		"material":       "YH9",
		"name_raw":       "bulk modulus",
		"value_raw":      "180",
		"value_number":   float64(180),
		"unit":           "GPa",
		"canonical_unit": "GPa",
		"pressure_gpa":   float64(250),
		"is_primary":     true,
	})
	if kp.Material != "YH9" || kp.NameRaw != "bulk modulus" {
		t.Fatalf("真实列未赋值：%#v", kp)
	}
	if kp.ValueNumber == nil || *kp.ValueNumber != 180 {
		t.Fatalf("value_number 未赋值：%#v", kp.ValueNumber)
	}
	if kp.CanonicalUnit == nil || *kp.CanonicalUnit != "GPa" {
		t.Fatalf("canonical_unit 未赋值：%#v", kp.CanonicalUnit)
	}
}

// T012（Issue #76）：GET /api/admin/papers/:id 的材料状态必须预加载
// tc_results、properties、structures——缺预加载时这些关联序列化为空数组，
// 编辑页拿不到任何科学数据（契约 docs/specs/76-.../contracts/scientific-draft-api.md C3）。
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
	state := firstMaterialState(t, body)

	if tcResults, ok := state["tc_results"].([]any); !ok || len(tcResults) == 0 {
		t.Fatalf("tc_results 未预加载：%#v", state["tc_results"])
	}
	if properties, ok := state["properties"].([]any); !ok || len(properties) == 0 {
		t.Fatalf("properties 未预加载：%#v", state["properties"])
	}
	if structures, ok := state["structures"].([]any); !ok || len(structures) == 0 {
		t.Fatalf("structures 未预加载：%#v", state["structures"])
	}
}

// T054（Issue #76，FR-024）：详情响应（管理端与公开）的 material_family 必须返回
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
	if err := db.Model(&models.MaterialState{}).Where("id = ?", 1).
		Update("material_family_id", 8).Error; err != nil {
		t.Fatal(err)
	}

	assertFamilyNameEn := func(t *testing.T, label string, body map[string]any) {
		t.Helper()
		state := firstMaterialState(t, body)
		family, ok := state["material_family"].(map[string]any)
		if !ok {
			t.Fatalf("%s material_family 缺失或类型异常：%#v", label, state["material_family"])
		}
		if family["name"] != "单质超导体" || family["name_en"] != "Elemental superconductor" {
			t.Fatalf("%s material_family = %#v，期望 name=单质超导体 且 name_en=Elemental superconductor", label, family)
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
