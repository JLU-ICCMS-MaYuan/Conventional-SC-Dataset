package cache

import (
	"context"
	"encoding/json"
	"os"
	"time"

	"github.com/redis/go-redis/v9"
)

var rdb *redis.Client
var ctx = context.Background()

func init() {
	addr := os.Getenv("REDIS_ADDR")
	if addr == "" {
		addr = "127.0.0.1:6379"
	}
	Connect(addr)
}

// Connect 切换 Redis 地址，供应用初始化和隔离集成测试复用。
func Connect(addr string) {
	if rdb != nil {
		_ = rdb.Close()
	}
	rdb = redis.NewClient(&redis.Options{Addr: addr, DialTimeout: 2 * time.Second})
}

func Get(key string, dest any) bool {
	if rdb == nil {
		return false
	}
	data, err := rdb.Get(ctx, key).Bytes()
	if err != nil {
		return false
	}
	return json.Unmarshal(data, dest) == nil
}

func Set(key string, val any, ttl time.Duration) {
	if rdb == nil {
		return
	}
	data, _ := json.Marshal(val)
	rdb.Set(ctx, key, data, ttl)
}

// FlushPattern 清除匹配 pattern 的所有缓存
func FlushPattern(pattern string) {
	if rdb == nil {
		return
	}
	keys, _ := rdb.Keys(ctx, pattern).Result()
	if len(keys) > 0 {
		rdb.Del(ctx, keys...)
	}
}
