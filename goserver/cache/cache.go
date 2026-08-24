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

func SetString(key, value string, ttl time.Duration) error {
	return rdb.Set(ctx, key, value, ttl).Err()
}

func Delete(keys ...string) error {
	if rdb == nil {
		return redis.ErrClosed
	}
	return rdb.Del(ctx, keys...).Err()
}

// IncrementWindow 原子增加固定窗口计数，并在首次增加时设置 TTL。
func IncrementWindow(key string, ttl time.Duration) (int64, error) {
	if rdb == nil {
		return 0, redis.ErrClosed
	}
	result, err := rdb.Eval(ctx, `
local value = redis.call('INCR', KEYS[1])
if value == 1 then redis.call('PEXPIRE', KEYS[1], ARGV[1]) end
return value
`, []string{key}, ttl.Milliseconds()).Int64()
	return result, err
}

// ConsumeVerificationCode 原子比较摘要并消费；返回 valid、invalid、locked 或 missing。
func ConsumeVerificationCode(codeKey, attemptsKey, expected string, maxAttempts int64, ttl time.Duration) (string, error) {
	if rdb == nil {
		return "", redis.ErrClosed
	}
	result, err := rdb.Eval(ctx, `
local stored = redis.call('GET', KEYS[1])
if not stored then return 0 end
if stored == ARGV[1] then
  redis.call('DEL', KEYS[1], KEYS[2])
  return 1
end
local attempts = redis.call('INCR', KEYS[2])
if attempts == 1 then redis.call('PEXPIRE', KEYS[2], ARGV[3]) end
if attempts >= tonumber(ARGV[2]) then
  redis.call('DEL', KEYS[1])
  return -1
end
return -2
`, []string{codeKey, attemptsKey}, expected, maxAttempts, ttl.Milliseconds()).Int64()
	if err != nil {
		return "", err
	}
	switch result {
	case 1:
		return "valid", nil
	case -1:
		return "locked", nil
	case -2:
		return "invalid", nil
	default:
		return "missing", nil
	}
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
