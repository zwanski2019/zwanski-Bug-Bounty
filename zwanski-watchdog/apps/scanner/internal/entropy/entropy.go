package entropy

import (
	"math"
	"regexp"
	"strings"
)

var uuidRe = regexp.MustCompile(`(?i)[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}`)

// Shannon entropy for ASCII-ish strings.
func Shannon(s string) float64 {
	if s == "" {
		return 0
	}
	freq := map[rune]int{}
	for _, r := range s {
		freq[r]++
	}
	var ent float64
	l := float64(len(s))
	for _, c := range freq {
		p := float64(c) / l
		ent -= p * math.Log2(p)
	}
	return ent
}

// LikelySecret combines entropy and heuristics.
func LikelySecret(s string) bool {
	t := strings.TrimSpace(s)
	if len(t) < 20 {
		return false
	}
	if uuidRe.MatchString(t) {
		return false
	}
	return Shannon(t) > 4.5
}
