package handlers

import "testing"

func TestNormalizeORCID(t *testing.T) {
	for _, value := range []string{"0000-0002-1825-0097", "0000-0002-9079-593X"} {
		got, valid := normalizeORCID(value)
		if !valid || got != value {
			t.Fatalf("normalizeORCID(%q) = %q, %v", value, got, valid)
		}
	}
	for _, value := range []string{"0000-0002-1825-0098", "0000000218250097", "0000-0002-9079-5930"} {
		if _, valid := normalizeORCID(value); valid {
			t.Fatalf("normalizeORCID(%q) should fail", value)
		}
	}
	if got, valid := normalizeORCID(" "); !valid || got != "" {
		t.Fatalf("empty ORCID = %q, %v", got, valid)
	}
}

func TestNormalizeInterests(t *testing.T) {
	got, valid := normalizeInterests([]string{" 超导 ", "机器学习", "超导"})
	if !valid || len(got) != 2 || got[0] != "超导" || got[1] != "机器学习" {
		t.Fatalf("interests = %#v, %v", got, valid)
	}
	tooMany := make([]string, 11)
	for index := range tooMany {
		tooMany[index] = "方向"
	}
	if _, valid := normalizeInterests(tooMany); valid {
		t.Fatal("more than 10 interests should fail")
	}
	if _, valid := normalizeInterests([]string{""}); valid {
		t.Fatal("empty interest should fail")
	}
	if _, valid := normalizeInterests([]string{"1234567890123456789012345678901"}); valid {
		t.Fatal("interest longer than 30 runes should fail")
	}
}
