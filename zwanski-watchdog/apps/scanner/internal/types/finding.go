package types

import "time"

// Finding is the canonical scanner emission consumed by the classifier.
type Finding struct {
	ID              string            `json:"id"`
	Source          string            `json:"source"`
	ModuleName      string            `json:"module_name"`
	RawContent      string            `json:"raw_content"`
	ContentHash     string            `json:"content_hash"`
	URL             string            `json:"url"`
	AffectedEntity  string            `json:"affected_entity"`
	Metadata        map[string]string `json:"metadata"`
	DiscoveredAt    time.Time         `json:"discovered_at"`
	ScanSessionID   string            `json:"scan_session_id"`
}

// ScanResult wraps a finding with timing / error context.
type ScanResult struct {
	Finding  Finding       `json:"finding"`
	Error    error         `json:"-"`
	Duration time.Duration `json:"duration"`
}
