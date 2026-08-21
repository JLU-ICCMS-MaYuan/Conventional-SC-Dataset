package models

import (
	"sync"
	"testing"

	"gorm.io/gorm/schema"
)

func parseModel(t *testing.T, model any) *schema.Schema {
	t.Helper()
	parsed, err := schema.Parse(model, &sync.Map{}, schema.NamingStrategy{})
	if err != nil {
		t.Fatalf("parse model: %v", err)
	}
	return parsed
}

func requireDBField(t *testing.T, parsed *schema.Schema, fieldName, dbName string) {
	t.Helper()
	field := parsed.LookUpField(fieldName)
	if field == nil {
		t.Fatalf("%s.%s is missing", parsed.Name, fieldName)
	}
	if field.DBName != dbName {
		t.Fatalf("%s.%s DBName = %q, want %q", parsed.Name, fieldName, field.DBName, dbName)
	}
}

func TestPaperLineageModelTablesAndRevisionFields(t *testing.T) {
	tests := []struct {
		model any
		table string
	}{
		{&Paper{}, "papers"},
		{&PaperFile{}, "paper_files"},
		{&PaperChunk{}, "paper_chunks"},
		{&PaperEvidence{}, "paper_evidences"},
		{&PaperReviewEvent{}, "paper_review_events"},
	}
	for _, test := range tests {
		parsed := parseModel(t, test.model)
		if parsed.Table != test.table {
			t.Fatalf("%T table = %q, want %q", test.model, parsed.Table, test.table)
		}
		if test.table == "papers" {
			requireDBField(t, parsed, "ContentRevision", "content_revision")
		} else {
			requireDBField(t, parsed, "PaperRevision", "paper_revision")
		}
	}
}

func TestPaperHasNoLegacySourcePath(t *testing.T) {
	parsed := parseModel(t, &Paper{})
	if field := parsed.LookUpField("SourceFilePath"); field != nil && field.DBName != "" {
		t.Fatalf("Paper must not map source_file_path: %#v", field)
	}
	requireDBField(t, parsed, "ContentRevision", "content_revision")
	requireDBField(t, parsed, "ApprovedRevision", "approved_revision")
}

func TestEvidenceUsesDirectChunkAnchor(t *testing.T) {
	parsed := parseModel(t, &PaperEvidence{})
	requireDBField(t, parsed, "PaperChunkID", "paper_chunk_id")
	for _, legacy := range []string{"PaperFileID", "ChunkIndex"} {
		if field := parsed.LookUpField(legacy); field != nil && field.DBName != "" {
			t.Fatalf("PaperEvidence must not map legacy field %s", legacy)
		}
	}
}
