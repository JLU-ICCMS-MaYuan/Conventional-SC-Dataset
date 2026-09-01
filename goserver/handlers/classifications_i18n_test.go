package handlers

import (
	"testing"

	"scwiki/server/models"
)

func TestSerializeCatalogIncludesBilingualNames(t *testing.T) {
	items := []models.MaterialFamily{{NameZH: "氢基超导体", NameEN: "Hydrogen-based superconductor"}}
	rows := serializeCatalog(items)
	if len(rows) != 1 {
		t.Fatalf("len(rows) = %d, want 1", len(rows))
	}
	row := rows[0]
	if row["name"] != row["name_zh"] || row["name_en"] != "Hydrogen-based superconductor" {
		t.Fatalf("unexpected bilingual catalog row: %#v", row)
	}
}
