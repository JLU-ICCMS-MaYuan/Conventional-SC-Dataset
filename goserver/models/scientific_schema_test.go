package models

import (
	"reflect"
	"testing"
)

func TestScientificModelTableNames(t *testing.T) {
	tests := []struct {
		model any
		table string
	}{
		{&MaterialState{}, "material_states"},
		{&StructureModel{}, "structure_models"},
		{&CalculationContext{}, "calculation_contexts"},
		{&ExperimentalContext{}, "experimental_contexts"},
		{&TcResult{}, "tc_results"},
		{&PropertyDefinition{}, "property_definitions"},
		{&SuperconductorProperty{}, "superconductor_properties"},
		{&TcResultEvidence{}, "tc_result_evidences"},
		{&StructureModelEvidence{}, "structure_model_evidences"},
		{&SuperconductorPropertyEvidence{}, "superconductor_property_evidences"},
	}
	for _, test := range tests {
		parsed := parseModel(t, test.model)
		if parsed.Table != test.table {
			t.Fatalf("%T table = %q, want %q", test.model, parsed.Table, test.table)
		}
	}
}

func TestScientificModelsHaveNoIndependentReviewStatus(t *testing.T) {
	models := []any{
		&MaterialState{}, &StructureModel{}, &CalculationContext{},
		&ExperimentalContext{}, &TcResult{}, &SuperconductorProperty{},
	}
	for _, model := range models {
		parsed := parseModel(t, model)
		if field := parsed.LookUpField("ReviewStatus"); field != nil && field.DBName != "" {
			t.Fatalf("%T must not map an independent review status", model)
		}
		requireDBField(t, parsed, "PaperRevision", "paper_revision")
	}
}

func TestPropertyModelUsesRawFirstTargetColumns(t *testing.T) {
	parsed := parseModel(t, &SuperconductorProperty{})
	requireDBField(t, parsed, "Material", "material_raw")
	requireDBField(t, parsed, "NameRaw", "name_raw")
	requireDBField(t, parsed, "ValueRaw", "value_raw")
	requireDBField(t, parsed, "Unit", "unit_raw")

	if reflect.TypeOf(KeyProperty{}) != reflect.TypeOf(SuperconductorProperty{}) {
		t.Fatal("KeyProperty must remain only a temporary alias")
	}
	if parsed.Table != "superconductor_properties" {
		t.Fatalf("legacy alias resolved to %q", parsed.Table)
	}
}

func TestIdentityFieldsLiveAtOneScientificLevel(t *testing.T) {
	paper := parseModel(t, &Paper{})
	superconductor := parseModel(t, &Superconductor{})
	state := parseModel(t, &MaterialState{})
	structure := parseModel(t, &StructureModel{})

	requireDBField(t, paper, "SuperconductorKind", "superconductor_kind")
	if field := state.LookUpField("SuperconductorKind"); field != nil && field.DBName != "" {
		t.Fatal("MaterialState must not expose superconductor_kind")
	}
	requireDBField(t, superconductor, "IsotopeSignature", "isotope_signature")
	if field := state.LookUpField("PhaseLabel"); field != nil && field.DBName != "" {
		t.Fatal("MaterialState must not expose phase_label")
	}
	if field := state.LookUpField("IsotopeSignature"); field != nil && field.DBName != "" {
		t.Fatal("MaterialState must not duplicate isotope identity")
	}
	if field := structure.LookUpField("PhaseLabel"); field != nil && field.DBName != "" {
		t.Fatal("StructureModel must not duplicate phase_label")
	}
}
