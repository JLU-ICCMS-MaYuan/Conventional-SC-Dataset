package handlers

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"scwiki/server/database"
	"scwiki/server/models"

	"github.com/gin-gonic/gin"
)

func requestMaterialStateExport(t *testing.T, paperID, stateKey string) *httptest.ResponseRecorder {
	t.Helper()
	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.GET("/papers/:id/material-states/:stateKey/export", ExportMaterialState)
	response := httptest.NewRecorder()
	router.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/papers/"+paperID+"/material-states/"+stateKey+"/export", nil))
	return response
}

func TestMaterialStateExportIsOfflineComplete(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusApproved)
	if err := db.Create(&models.StructureModel{
		ID: 1, PaperID: 4, PaperRevision: 1, MaterialStateID: 1,
		StructureFormat: "cif", StructureText: "data_LaH10\n_cell_length_a 5.0", StructureHash: "structure-sha256",
		NuclearTreatment: "unknown", SourceLocator: strPtr("/private/storage/LaH10.cif"),
	}).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Model(&models.PropertyRecord{}).Where("id = ?", 1).Update("structure_key", "structure-1").Error; err != nil {
		t.Fatal(err)
	}

	response := requestMaterialStateExport(t, "4", "state-lah10-170gpa")
	if response.Code != http.StatusOK {
		t.Fatalf("status=%d body=%s", response.Code, response.Body.String())
	}
	if disposition := response.Header().Get("Content-Disposition"); disposition == "" {
		t.Fatal("导出响应缺少下载文件名")
	}
	var body map[string]any
	if err := json.Unmarshal(response.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body["export_version"] != float64(1) {
		t.Fatalf("export_version=%#v", body["export_version"])
	}
	definitions := body["form_definitions"].([]any)
	if len(definitions) != 2 {
		t.Fatalf("绑定定义数量=%d，期望 2：%#v", len(definitions), definitions)
	}
	state := body["material_state"].(map[string]any)
	if state["state_key"] != "state-lah10-170gpa" {
		t.Fatalf("state_key=%#v", state["state_key"])
	}
	structures := state["structures"].([]any)
	if structures[0].(map[string]any)["structure_key"] != "structure-1" {
		t.Fatalf("结构键未导出：%#v", structures[0])
	}
	file := structures[0].(map[string]any)["file"].(map[string]any)
	if file["filename"] != "LaH10.cif" || file["content"] != "data_LaH10\n_cell_length_a 5.0" || file["sha256"] != "structure-sha256" {
		t.Fatalf("结构文件未内嵌：%#v", file)
	}
	record := state["property_modules"].([]any)[0].(map[string]any)["records"].([]any)[0].(map[string]any)
	if record["payload"].(map[string]any)["parameters"] == nil {
		t.Fatalf("记录参数缺失：%#v", record)
	}
	if len(record["evidences"].([]any)) != 1 {
		t.Fatalf("记录 Evidence 缺失：%#v", record["evidences"])
	}
}

func TestMaterialStateExportRejectsUnknownStructureKey(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusApproved)
	if err := db.Create(&models.StructureModel{
		ID: 1, PaperID: 4, PaperRevision: 1, MaterialStateID: 1,
		StructureFormat: "cif", StructureText: "data_LaH10", StructureHash: "structure-sha256",
		NuclearTreatment: "unknown",
	}).Error; err != nil {
		t.Fatal(err)
	}
	if err := db.Model(&models.PropertyRecord{}).Where("id = ?", 1).Update("structure_key", "structure-999").Error; err != nil {
		t.Fatal(err)
	}

	response := requestMaterialStateExport(t, "4", "state-lah10-170gpa")
	if response.Code != http.StatusConflict {
		t.Fatalf("status=%d body=%s", response.Code, response.Body.String())
	}
}

func TestMaterialStateExportRejectsMissingEvidence(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusApproved)
	if err := db.Where("record_id = ?", 1).Delete(&models.PropertyRecordEvidence{}).Error; err != nil {
		t.Fatal(err)
	}

	response := requestMaterialStateExport(t, "4", "state-lah10-170gpa")
	if response.Code != http.StatusConflict {
		t.Fatalf("status=%d body=%s", response.Code, response.Body.String())
	}
	var body map[string]any
	_ = json.Unmarshal(response.Body.Bytes(), &body)
	if body["code"] != "export_incomplete" {
		t.Fatalf("code=%#v", body["code"])
	}
}

func TestMaterialStateExportUsesPaperVisibility(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusPending)

	response := requestMaterialStateExport(t, "4", "state-lah10-170gpa")
	if response.Code != http.StatusForbidden {
		t.Fatalf("status=%d body=%s", response.Code, response.Body.String())
	}
}

func TestMaterialStateExportRejectsRevisionChange(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusApproved)
	materialStateExportAfterSnapshot = func() {
		if err := database.DB.Model(&models.Paper{}).Where("id = ?", 4).Update("content_revision", 2).Error; err != nil {
			t.Fatalf("更新 revision 失败: %v", err)
		}
	}
	t.Cleanup(func() { materialStateExportAfterSnapshot = func() {} })

	response := requestMaterialStateExport(t, "4", "state-lah10-170gpa")
	if response.Code != http.StatusConflict {
		t.Fatalf("status=%d body=%s", response.Code, response.Body.String())
	}
	var body map[string]any
	_ = json.Unmarshal(response.Body.Bytes(), &body)
	if body["code"] != "export_revision_conflict" {
		t.Fatalf("code=%#v", body["code"])
	}
}

func TestMaterialStateExportDoesNotTreatDatabaseIDAsStateKey(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusApproved)

	response := requestMaterialStateExport(t, "4", "1")
	if response.Code != http.StatusNotFound {
		t.Fatalf("status=%d body=%s", response.Code, response.Body.String())
	}
}

func TestPropertyModuleKeyIsScopedToMaterialState(t *testing.T) {
	db := paperDetailTestDB(t)
	seedPaperFour(t, db, reviewStatusApproved)
	if err := db.Create(&models.MaterialState{
		ID: 2, StateKey: "state-lah10-200gpa", PaperID: 4, PaperRevision: 1,
		SuperconductorID: 1, MaterialDimensionality: "bulk", CrystalSystem: "cubic", StateKind: "theoretical",
	}).Error; err != nil {
		t.Fatal(err)
	}
	module := models.PropertyModule{
		ModuleKey: "module-superconductive-1", PaperID: 4, PaperRevision: 1, MaterialStateID: 2,
		ModuleCode: "superconductive_properties", DefinitionKey: "module.superconductive_properties",
		DefinitionVersion: 1, MetadataJSON: json.RawMessage(`{}`),
	}
	if err := db.Create(&module).Error; err != nil {
		t.Fatalf("相同 module_key 应允许存在于不同 MaterialState: %v", err)
	}
	duplicateCode := module
	duplicateCode.ID = 0
	duplicateCode.ModuleKey = "module-superconductive-2"
	if err := db.Create(&duplicateCode).Error; err == nil {
		t.Fatal("同一 MaterialState 不应允许重复 module_code")
	}
}
