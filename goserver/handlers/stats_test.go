package handlers

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"scwiki/server/models"

	"github.com/gin-gonic/gin"
)

func statsStringPointer(value string) *string { return &value }

func TestChartFamilyIDsSupportsPaperLevelMultipleLabels(t *testing.T) {
	ids := chartFamilyIDs(statsStringPointer("1,8,13"))
	if len(ids) != 3 || ids[0] != 1 || ids[1] != 8 || ids[2] != 13 {
		t.Fatalf("chartFamilyIDs = %#v", ids)
	}
	if !strings.Contains(chartFamilyIDsExpr(), "paper_material_families") ||
		strings.Contains(chartApprovedJoin, "paper_material_families") {
		t.Fatal("family 必须通过论文级相关子查询读取，基础结果集不得 JOIN 多标签关系")
	}
}

func TestResolveChartTcField(t *testing.T) {
	tests := []struct {
		input string
		field string
		ok    bool
	}{
		{"", "experimental_tc", true},
		{"  ", "experimental_tc", true},
		{"experimental_tc", "experimental_tc", true},
		{"anisotropic_eliashberg_tc", "anisotropic_eliashberg_tc", true},
		{"isotropic_eliashberg_tc", "isotropic_eliashberg_tc", true},
		{"allen_dynes_tc", "allen_dynes_tc", true},
		{"mcmillan_tc", "mcmillan_tc", true},
		{"experimental_tc; DROP TABLE papers", "", false},
	}
	for _, tt := range tests {
		field, column, ok := resolveChartTcField(tt.input)
		if ok != tt.ok || field != tt.field {
			t.Fatalf("resolveChartTcField(%q) = (%q, %q, %v)", tt.input, field, column, ok)
		}
		if ok && column == "" {
			t.Fatalf("合法字段 %q 缺少数据库列映射", field)
		}
	}
}

func TestTcPressureChartRejectsUnsupportedField(t *testing.T) {
	gin.SetMode(gin.TestMode)
	recorder := httptest.NewRecorder()
	context, _ := gin.CreateTestContext(recorder)
	context.Request = httptest.NewRequest(http.MethodGet, "/api/papers/stats/tc-pressure?tc_field=drop_table", nil)
	TcPressureChart(context)
	if recorder.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want %d", recorder.Code, http.StatusBadRequest)
	}
}

func TestChartCacheKeySeparatesChartAndField(t *testing.T) {
	pressure := chartCacheKey("tc_pressure", "experimental_tc")
	year := chartCacheKey("tc_year", "experimental_tc")
	theory := chartCacheKey("tc_pressure", "mcmillan_tc")
	if pressure == year || pressure == theory || year == theory {
		t.Fatalf("图表与字段缓存键必须隔离: %q %q %q", pressure, year, theory)
	}
}

func TestTcChartsReadRepresentativeUnifiedRecords(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusApproved)
	if err := db.Create(&models.PropertyRecord{
		ID: 2, RecordKey: "record-nonrepresentative", PaperID: 4, PaperRevision: 1,
		MaterialStateID: 1, ModuleID: 1, RecordType: "predicted_tc", PropertyCode: "tc",
		DefinitionID: 2, DefinitionKey: "record.superconductive_properties.predicted_tc.allen_dynes", DefinitionVersion: 1,
		NameRaw: "critical temperature", ValueKind: "number", ValueRaw: "499 K", ValueNumber: f64Ptr(499),
		MethodCode: strPtr("allen_dynes"), IsRepresentative: false,
		PayloadJSON: json.RawMessage(`{"calculation_conditions":{}}`), SourceFingerprint: "nonrepresentative", RecordChecksum: "nonrepresentative",
	}).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Create(&models.PropertyRecord{
		ID: 3, RecordKey: "record-measured", PaperID: 4, PaperRevision: 1,
		MaterialStateID: 1, ModuleID: 1, RecordType: "measured_tc", PropertyCode: "tc",
		DefinitionID: 2, DefinitionKey: "record.superconductive_properties.predicted_tc.allen_dynes", DefinitionVersion: 1,
		NameRaw: "critical temperature", ValueKind: "number", ValueRaw: "260 K", ValueNumber: f64Ptr(260),
		MethodCode: strPtr("resistivity"), IsRepresentative: true,
		PayloadJSON: json.RawMessage(`{"experimental_conditions":{}}`), SourceFingerprint: "measured", RecordChecksum: "measured",
	}).Error; err != nil {
		t.Fatal(err)
	}

	assertChart := func(path, wantType string, wantY float64) {
		t.Helper()
		gin.SetMode(gin.TestMode)
		recorder := httptest.NewRecorder()
		context, _ := gin.CreateTestContext(recorder)
		context.Request = httptest.NewRequest(http.MethodGet, path, nil)
		TcPressureChart(context)
		if recorder.Code != http.StatusOK {
			t.Fatalf("%s status=%d body=%s", path, recorder.Code, recorder.Body.String())
		}
		var body []map[string]any
		if err := json.Unmarshal(recorder.Body.Bytes(), &body); err != nil {
			t.Fatal(err)
		}
		if len(body) != 1 || body[0]["type"] != wantType || body[0]["y"] != wantY {
			t.Fatalf("%s 图表数据异常：%#v", path, body)
		}
	}

	assertChart("/api/papers/stats/tc-pressure?tc_field=allen_dynes_tc", "theoretical", 274)
	assertChart("/api/papers/stats/tc-pressure?tc_field=experimental_tc", "experimental", 260)
}
