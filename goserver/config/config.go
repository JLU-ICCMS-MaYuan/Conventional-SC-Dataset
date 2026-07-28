package config

import "os"

// Config 应用配置 —— Go 用 struct 代替 Python dict
type Config struct {
	Port         string
	MySQL_DSN    string // Data Source Name: 连接字符串
	JWTSecret    string
	PythonBackend string // Python 后端地址
}

// Load 加载配置
func Load() Config {
	return Config{
		Port:          getEnv("PORT", "8080"),
		MySQL_DSN:     getEnv("DATABASE_URL", "work:12345678@tcp(127.0.0.1:3306)/superconductor_dataset_v2?charset=utf8mb4&parseTime=True"),
		JWTSecret:     getEnv("JWT_SECRET_KEY", "fallback-insecure-key-for-dev-only"),
		PythonBackend: getEnv("PYTHON_BACKEND_URL", "http://127.0.0.1:8000"),
	}
}

// getEnv 辅助函数 —— Go 没有 os.Getenv 带默认值的版本
func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
