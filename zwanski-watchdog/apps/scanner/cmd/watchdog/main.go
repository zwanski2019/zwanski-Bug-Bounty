package main

import (
	"context"
	"flag"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"

	"github.com/prometheus/client_golang/prometheus/promhttp"

	"github.com/zwanski/watchdog/scanner/internal/dedup"
	"github.com/zwanski/watchdog/scanner/internal/metrics"
	"github.com/zwanski/watchdog/scanner/internal/queue"
	s3mod "github.com/zwanski/watchdog/scanner/modules/s3"
	"github.com/zwanski/watchdog/scanner/internal/types"
)

func main() {
	modules := flag.String("modules", "s3", "comma-separated modules")
	concurrency := flag.Int("concurrency", 4, "goroutines")
	dry := flag.Bool("dry-run", false, "do not push to redis")
	flag.Parse()

	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()

	q := queue.NewRedisQueue()
	rdb := q.Redis()
	go startMetrics()

	modList := strings.Split(*modules, ",")
	results := make(chan types.ScanResult, 128)
	go func() {
		defer close(results)
		for _, name := range modList {
			name = strings.TrimSpace(name)
			switch name {
			case "s3":
				sc := s3mod.New()
				if err := sc.Run(ctx, results); err != nil {
					log.Printf("module %s: %v", name, err)
				}
			default:
				log.Printf("unknown module %s", name)
			}
		}
	}()

	d := dedup.New(rdb)
	processed := 0
	for res := range results {
		if res.Error != nil {
			continue
		}
		seen, err := d.Seen(ctx, res.Finding.ContentHash)
		if err != nil {
			log.Printf("dedup: %v", err)
		}
		if seen {
			metrics.DedupHits.Inc()
			continue
		}
		if *dry {
			log.Printf("dry-run finding %s", res.Finding.ID)
			continue
		}
		if err := q.Push(ctx, res.Finding); err != nil {
			log.Printf("push: %v", err)
			_ = q.PushDLQ(ctx, res.Finding, err.Error())
			continue
		}
		processed++
		if processed >= *concurrency*10 {
			break
		}
	}
	log.Printf("done, processed=%d", processed)
}

func startMetrics() {
	http.Handle("/metrics", promhttp.Handler())
	addr := ":9090"
	if p := os.Getenv("METRICS_ADDR"); p != "" {
		addr = p
	}
	_ = http.ListenAndServe(addr, nil)
}
