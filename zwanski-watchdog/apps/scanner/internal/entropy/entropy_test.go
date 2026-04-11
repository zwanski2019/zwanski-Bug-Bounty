package entropy

import "testing"

func TestShannon(t *testing.T) {
	if s := Shannon("aaaa"); s != 0 {
		t.Fatalf("expected 0 got %v", s)
	}
	if s := Shannon("ab"); s != 1 {
		t.Fatalf("expected 1 got %v", s)
	}
}

func TestLikelySecret(t *testing.T) {
	if !LikelySecret("abcdefghijklmnopqrst") {
		t.Fatal("expected likely secret for long varied string")
	}
	if LikelySecret("short") {
		t.Fatal("short should not match")
	}
}
