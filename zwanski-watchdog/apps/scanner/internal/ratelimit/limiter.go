package ratelimit

import (
	"sync"
	"time"
)

// TokenBucket is a simple in-memory limiter per module.
type TokenBucket struct {
	mu       sync.Mutex
	rate     float64
	capacity float64
	tokens   float64
	last     time.Time
}

func New(rpm int) *TokenBucket {
	if rpm <= 0 {
		rpm = 30
	}
	rate := float64(rpm) / 60.0
	return &TokenBucket{rate: rate, capacity: rate * 2, tokens: rate * 2, last: time.Now()}
}

// Allow returns true if a request may proceed.
func (b *TokenBucket) Allow() bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	now := time.Now()
	elapsed := now.Sub(b.last).Seconds()
	b.last = now
	b.tokens = min(b.capacity, b.tokens+elapsed*b.rate)
	if b.tokens < 1 {
		return false
	}
	b.tokens -= 1
	return true
}

func min(a, b float64) float64 {
	if a < b {
		return a
	}
	return b
}
