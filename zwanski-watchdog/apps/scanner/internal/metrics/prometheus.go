package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
	FindingsTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "watchdog_findings_total",
		Help: "Findings emitted by module",
	}, []string{"module", "leak_type"})

	ScanDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "watchdog_scan_duration_seconds",
		Help:    "Scan duration per module",
		Buckets: prometheus.ExponentialBuckets(0.01, 2, 12),
	}, []string{"module"})

	ErrorsTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "watchdog_scan_errors_total",
		Help: "Scanner errors",
	}, []string{"module"})

	QueueDepth = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "watchdog_redis_queue_depth",
		Help: "Depth of findings queue",
	})

	DedupHits = promauto.NewCounter(prometheus.CounterOpts{
		Name: "watchdog_dedup_hits_total",
		Help: "Dedup hits",
	})
)
