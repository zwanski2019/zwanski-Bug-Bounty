package queue

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/zwanski/watchdog/scanner/internal/types"
)

const (
	QueueKey = "findings:queue"
	DLQKey   = "findings:dlq"
)

// RedisQueue pushes serialized findings for the classifier service.
type RedisQueue struct {
	client *redis.Client
}

// Redis exposes the underlying client for deduplication and metrics.
func (q *RedisQueue) Redis() *redis.Client {
	return q.client
}

func NewRedisQueue() *RedisQueue {
	addr := os.Getenv("REDIS_URL")
	if addr == "" {
		addr = "redis://localhost:6379"
	}
	opt, err := redis.ParseURL(addr)
	if err != nil {
		opt = &redis.Options{Addr: "localhost:6379"}
	}
	return &RedisQueue{client: redis.NewClient(opt)}
}

// Push serializes a finding to the Redis list.
func (q *RedisQueue) Push(ctx context.Context, f types.Finding) error {
	b, err := json.Marshal(f)
	if err != nil {
		return err
	}
	return q.client.LPush(ctx, QueueKey, b).Err()
}

// PushDLQ stores failed classification handoffs.
func (q *RedisQueue) PushDLQ(ctx context.Context, f types.Finding, reason string) error {
	b, err := json.Marshal(map[string]any{"finding": f, "reason": reason, "at": time.Now().UTC()})
	if err != nil {
		return err
	}
	return q.client.LPush(ctx, DLQKey, b).Err()
}

// Handler processes findings popped from the queue (used by tests / local workers).
func (q *RedisQueue) Subscribe(ctx context.Context, handler func(types.Finding) error) error {
	if handler == nil {
		return errors.New("handler required")
	}
	for {
		res, err := q.client.BRPop(ctx, time.Second*5, QueueKey).Result()
		if err != nil {
			if errors.Is(err, redis.Nil) || errors.Is(err, context.Canceled) {
				return ctx.Err()
			}
			continue
		}
		if len(res) < 2 {
			continue
		}
		var f types.Finding
		if err := json.Unmarshal([]byte(res[1]), &f); err != nil {
			_ = q.PushDLQ(ctx, f, "json_unmarshal")
			continue
		}
		if err := handler(f); err != nil {
			_ = q.PushDLQ(ctx, f, err.Error())
		}
	}
}
