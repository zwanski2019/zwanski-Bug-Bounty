package dedup

import (
	"context"
	"errors"
	"hash/fnv"
	"time"

	"github.com/redis/go-redis/v9"
)

const ttl = 24 * time.Hour

// Deduper prevents re-queuing identical content hashes within TTL.
type Deduper struct {
	rdb *redis.Client
}

func New(rdb *redis.Client) *Deduper {
	return &Deduper{rdb: rdb}
}

// Seen returns true if hash was recently queued.
func (d *Deduper) Seen(ctx context.Context, contentHash string) (bool, error) {
	key := "watchdog:dedup:" + contentHash
	ok, err := d.rdb.SetNX(ctx, key, "1", ttl).Result()
	if err != nil {
		return false, err
	}
	return !ok, nil
}

// BloomQuick is a cheap in-process pre-check (not cryptographically sound).
func BloomQuick(contentHash string) uint64 {
	h := fnv.New64a()
	_, _ = h.Write([]byte(contentHash))
	return h.Sum64()
}

var ErrDuplicate = errors.New("duplicate content hash within ttl")
