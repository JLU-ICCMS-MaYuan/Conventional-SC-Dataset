package handlers

import (
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"scwiki/server/models"

	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

func TestPaperToDictIncludesTheoreticalSubtype(t *testing.T) {
	subtype := "calculation"
	result := paperToDict(models.Paper{TheoreticalSubtype: &subtype})
	if got := result["theoretical_subtype"]; got != &subtype {
		t.Fatalf("theoretical_subtype = %#v, want pointer to %q", got, subtype)
	}
}

func TestPaperToDictIncludesPaperLevelSuperconductorKind(t *testing.T) {
	result := paperToDict(models.Paper{SuperconductorKind: "conventional"})
	if got := result["superconductor_kind"]; got != "conventional" {
		t.Fatalf("superconductor_kind = %#v, want conventional", got)
	}
}

func TestPaperClassificationSnapshotPlacesSuperconductorKindAtPaperLevel(t *testing.T) {
	snapshot := paperClassificationSnapshot{
		SuperconductorKind: "unconventional",
		MaterialStates: []classificationSnapshotState{{
			ID: 1, MaterialDimensionality: "three_dimensional", CrystalSystem: "cubic",
		}},
	}
	if snapshot.SuperconductorKind != "unconventional" {
		t.Fatalf("snapshot superconductor_kind = %q", snapshot.SuperconductorKind)
	}
	if len(snapshot.MaterialStates) != 1 || snapshot.MaterialStates[0].CrystalSystem != "cubic" {
		t.Fatalf("状态分类快照异常：%#v", snapshot.MaterialStates)
	}
	encoded, err := json.Marshal(snapshot)
	if err != nil {
		t.Fatal(err)
	}
	var payload map[string]any
	if err := json.Unmarshal(encoded, &payload); err != nil {
		t.Fatal(err)
	}
	if got := payload["superconductor_kind"]; got != "unconventional" {
		t.Fatalf("快照顶层 superconductor_kind = %#v", got)
	}
	states, ok := payload["material_states"].([]any)
	if !ok || len(states) != 1 {
		t.Fatalf("快照 material_states = %#v", payload["material_states"])
	}
	if _, exists := states[0].(map[string]any)["superconductor_kind"]; exists {
		t.Fatal("审核快照的 material_states 不得包含 superconductor_kind")
	}
}

func TestValidSuperconductorKind(t *testing.T) {
	for _, value := range []string{"conventional", "unconventional", "unknown"} {
		if !validSuperconductorKind(value) {
			t.Fatalf("%q 应为有效 superconductor_kind", value)
		}
	}
	for _, value := range []string{"", "mixed", "conventional "} {
		if validSuperconductorKind(value) {
			t.Fatalf("%q 不应为有效 superconductor_kind", value)
		}
	}
}

func TestMaterialClassificationUpdateRejectsLegacySuperconductorKind(t *testing.T) {
	var update materialClassificationUpdate
	err := json.Unmarshal([]byte(`{"id":1,"superconductor_kind":"conventional"}`), &update)
	if !errors.Is(err, errLegacyClassificationContract) {
		t.Fatalf("旧状态级 superconductor_kind 应被拒绝，实际错误：%v", err)
	}
}

func TestPaperUpdateFieldsExcludeReviewState(t *testing.T) {
	fields := make(map[string]bool, len(paperUpdateFields))
	for _, field := range paperUpdateFields {
		fields[field] = true
	}
	if fields["review_status"] || fields["review_comment"] {
		t.Fatal("普通论文更新不得修改审核状态或审核意见")
	}
	if !fields["theoretical_subtype"] {
		t.Fatal("论文更新必须支持 theoretical_subtype")
	}
	if !fields["superconductor_kind"] {
		t.Fatal("论文更新必须支持论文级 superconductor_kind")
	}
	if !fields["knowledge_graph_title"] {
		t.Fatal("管理员论文更新必须支持 knowledge_graph_title")
	}
}

func TestPatchPaperAllowsKnowledgeGraphTitle(t *testing.T) {
	if !paperPatchFieldAllowed("knowledge_graph_title") {
		t.Fatal("普通论文更新必须支持 knowledge_graph_title")
	}
}

// T042：PUT /api/admin/papers/:id 的更新集必须接受并携带 knowledge_graph_title，
// 且白名单外字段（review_status）不得混入。
func TestUpdatePaperExtractsKnowledgeGraphTitle(t *testing.T) {
	body := map[string]interface{}{
		"knowledge_graph_title": "Discovery of Superconductivity in Mercury",
		"summary":               "summary text",
		"review_status":         "approved",
	}
	updates := paperUpdatesFromBody(body)
	if got := updates["knowledge_graph_title"]; got != "Discovery of Superconductivity in Mercury" {
		t.Fatalf("knowledge_graph_title = %#v, want the submitted value", got)
	}
	if got := updates["summary"]; got != "summary text" {
		t.Fatalf("summary = %#v, want the submitted value", got)
	}
	if _, ok := updates["review_status"]; ok {
		t.Fatal("审核状态不得通过普通编辑进入更新集")
	}
}

// T042：PATCH /api/papers/:id 的更新集必须接受 knowledge_graph_title，
// 且白名单外字段被丢弃。
func TestPatchPaperExtractsKnowledgeGraphTitle(t *testing.T) {
	body := map[string]interface{}{
		"knowledge_graph_title": "Graph title",
		"review_status":         "approved",
		"unknown_field":         "value",
	}
	updates := paperPatchUpdatesFromBody(body)
	if got := updates["knowledge_graph_title"]; got != "Graph title" {
		t.Fatalf("knowledge_graph_title = %#v, want the submitted value", got)
	}
	if _, ok := updates["review_status"]; ok {
		t.Fatal("PATCH 不得接受 review_status")
	}
	if _, ok := updates["unknown_field"]; ok {
		t.Fatal("PATCH 不得接受白名单外字段")
	}
}

func TestReviewStatusWhitelist(t *testing.T) {
	for _, status := range []string{"pending", "approved", "rejected"} {
		if !isValidReviewStatus(status) {
			t.Fatalf("expected %q to be valid", status)
		}
	}
	for _, status := range []string{"", "draft", "reviewed", "needs_revision", "invalid"} {
		if isValidReviewStatus(status) {
			t.Fatalf("expected %q to be invalid", status)
		}
	}
}

func TestReviewArtifactCleanupOnlyForTerminalStates(t *testing.T) {
	tests := map[string]bool{
		"approved":       true,
		"rejected":       true,
		"pending":        false,
		"needs_revision": false,
	}
	for status, want := range tests {
		if got := shouldCleanupReviewArtifact(status); got != want {
			t.Fatalf("shouldCleanupReviewArtifact(%q) = %v, want %v", status, got, want)
		}
	}
}

func TestKeyPropertyValidationRunsBeforeWrites(t *testing.T) {
	body := map[string]interface{}{
		"key_properties": []interface{}{
			map[string]interface{}{
				"material": "LaH10", "name": "critical_temperature",
				"value_min": 250.0, "value_max": 200.0,
			},
		},
	}
	if _, err := parseAndValidateKeyProperties(body); err == nil || !strings.Contains(err.Error(), "value_min") {
		t.Fatalf("expected range validation error, got %v", err)
	}
}

func TestGetFloatAsUintRejectsFractionalAndNegativeIDs(t *testing.T) {
	for _, value := range []interface{}{-1, int64(-1), -1.0, 1.5} {
		if _, ok := getFloatAsUint(value); ok {
			t.Fatalf("expected %#v to be rejected", value)
		}
	}
	if got, ok := getFloatAsUint(2.0); !ok || got != 2 {
		t.Fatalf("got (%d, %v), want (2, true)", got, ok)
	}
}

func TestPublicQueriesRequireApprovedPapers(t *testing.T) {
	db, err := gorm.Open(mysql.New(mysql.Config{
		DSN:                       "user:pass@tcp(127.0.0.1:3306)/test",
		SkipInitializeWithVersion: true,
	}), &gorm.Config{DryRun: true, DisableAutomaticPing: true})
	if err != nil {
		t.Fatal(err)
	}

	var paper models.Paper
	detail := approvedPaperDetailQuery(db).First(&paper, 1).Statement
	if sql := detail.SQL.String(); !strings.Contains(sql, "review_status") {
		t.Fatalf("public detail query lacks approved filter: %s", sql)
	}

	var rows []struct {
		models.KeyProperty
		models.Paper
	}
	search := approvedRecordSearchQuery(db).Find(&rows).Statement
	if sql := search.SQL.String(); !strings.Contains(sql, "papers.review_status") {
		t.Fatalf("public search query lacks approved filter: %s", sql)
	}
}

func TestCleanupReviewArtifactForwardsAuthorization(t *testing.T) {
	var method, path, authorization string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		method = r.Method
		path = r.URL.Path
		authorization = r.Header.Get("Authorization")
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()

	if err := cleanupReviewArtifactAt(server.URL, "42", "Bearer token"); err != nil {
		t.Fatal(err)
	}
	if method != http.MethodDelete || path != "/api/rag/papers/42/review-artifact" {
		t.Fatalf("unexpected request: %s %s", method, path)
	}
	if authorization != "Bearer token" {
		t.Fatalf("Authorization = %q", authorization)
	}
}

func TestPublishApprovedPaperForwardsAuthorization(t *testing.T) {
	var method, path, authorization string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		method = r.Method
		path = r.URL.Path
		authorization = r.Header.Get("Authorization")
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()

	if err := publishApprovedPaperAt(server.URL, "42", "Bearer token"); err != nil {
		t.Fatal(err)
	}
	if method != http.MethodPost || path != "/api/rag/papers/42/publish" {
		t.Fatalf("unexpected request: %s %s", method, path)
	}
	if authorization != "Bearer token" {
		t.Fatalf("Authorization = %q", authorization)
	}
}

func TestPublishApprovedPaperRejectsBackendFailure(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusConflict)
	}))
	defer server.Close()
	if err := publishApprovedPaperAt(server.URL, "42", ""); err == nil {
		t.Fatal("expected publish failure")
	}
}

func TestCleanupReviewArtifactTreatsMissingArtifactAsSuccess(t *testing.T) {
	server := httptest.NewServer(http.NotFoundHandler())
	defer server.Close()
	if err := cleanupReviewArtifactAt(server.URL, "42", ""); err != nil {
		t.Fatalf("404 should be idempotent, got %v", err)
	}
}
