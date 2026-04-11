package s3

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/zwanski/watchdog/scanner/internal/metrics"
	"github.com/zwanski/watchdog/scanner/internal/ratelimit"
	"github.com/zwanski/watchdog/scanner/internal/types"
)

// Scanner probes heuristic public bucket URLs (read-only HEAD).
type Scanner struct {
	limiter *ratelimit.TokenBucket
	client  *http.Client
}

func New() *Scanner {
	return &Scanner{
		limiter: ratelimit.New(60),
		client:  &http.Client{Timeout: 12 * time.Second},
	}
}

func (s *Scanner) Name() string { return "s3_public_bucket" }

type Config struct {
	RateLimit     int
	Concurrency   int
	Timeout       time.Duration
	RetryAttempts int
}

func (s *Scanner) Config() Config {
	return Config{RateLimit: 60, Concurrency: 8, Timeout: 12 * time.Second, RetryAttempts: 2}
}

// Run emits synthetic findings for buckets that respond publicly to HEAD.
func (s *Scanner) Run(ctx context.Context, results chan<- types.ScanResult) error {
	prefixes := []string{"backup", "prod", "data", "assets", "dev", "staging"}
	companies := []string{"example-corp", "demo-co"}
	for _, co := range companies {
		for _, p := range prefixes {
			select {
			case <-ctx.Done():
				return ctx.Err()
			default:
			}
			if !s.limiter.Allow() {
				time.Sleep(200 * time.Millisecond)
			}
			host := fmt.Sprintf("%s-%s.s3.amazonaws.com", co, p)
			url := "https://" + host
			start := time.Now()
			req, _ := http.NewRequestWithContext(ctx, http.MethodHead, url, nil)
			resp, err := s.client.Do(req)
			dur := time.Since(start)
			metrics.ScanDuration.WithLabelValues(s.Name()).Observe(dur.Seconds())
			if err != nil {
				metrics.ErrorsTotal.WithLabelValues(s.Name()).Inc()
				continue
			}
			_ = resp.Body.Close()
			if resp.StatusCode >= 200 && resp.StatusCode < 500 {
				raw := fmt.Sprintf("public_bucket_head status=%d host=%s", resp.StatusCode, host)
				h := sha256.Sum256([]byte(raw))
				f := types.Finding{
					ID:             hex.EncodeToString(h[:16]),
					Source:         "scanner",
					ModuleName:     s.Name(),
					RawContent:     raw,
					ContentHash:    hex.EncodeToString(h[:]),
					URL:            url,
					AffectedEntity: strings.Split(host, ".")[0],
					Metadata:       map[string]string{"status": fmt.Sprintf("%d", resp.StatusCode)},
					DiscoveredAt:   time.Now().UTC(),
					ScanSessionID:  "phase2-mvp",
				}
				metrics.FindingsTotal.WithLabelValues(s.Name(), "other").Inc()
				results <- types.ScanResult{Finding: f, Duration: dur}
			}
		}
	}
	return nil
}
