package config

import (
	"fmt"
	"log"
	"net/url"
	"os"
	"strings"
)

// Config 应用配置
type Config struct {
	Port          string
	MySQL_DSN     string // Go MySQL driver DSN: user:pass@tcp(host:port)/db
	JWTSecret     string
	PythonBackend string
	DataDir       string // 数据目录路径
	SMTPHost      string
	SMTPPort      string
	SMTPUsername  string
	SMTPPassword  string
	SMTPFrom      string
	SMTPTLSMode   string
	AvatarDir     string
}

// Load 加载配置。关键配置缺少环境变量时直接 Fatal 退出。
func Load() Config {
	dataDir := getEnv("SC_WIKI_DATA_DIR", "data")
	return Config{
		Port:          getEnv("PORT", "8080"),
		MySQL_DSN:     parseMySQLDSN(requireEnv("DATABASE_URL")),
		JWTSecret:     requireEnv("JWT_SECRET_KEY"),
		PythonBackend: getEnv("PYTHON_BACKEND_URL", "http://127.0.0.1:8000"),
		DataDir:       dataDir,
		SMTPHost:      getEnv("SMTP_HOST", ""),
		SMTPPort:      getEnv("SMTP_PORT", "587"),
		SMTPUsername:  getEnv("SMTP_USERNAME", getEnv("SMTP_USER", "")),
		SMTPPassword:  getEnv("SMTP_PASSWORD", ""),
		SMTPFrom:      getEnv("SMTP_FROM", ""),
		SMTPTLSMode:   getEnv("SMTP_TLS_MODE", "starttls"),
		AvatarDir:     getEnv("AVATAR_DIR", dataDir+"/avatars"),
	}
}

// parseMySQLDSN 将 Python 格式 DSN 转为 Go 格式
// "mysql+pymysql://user:pass@host:port/db?params" → "user:pass@tcp(host:port)/db?params"
func parseMySQLDSN(pythonDSN string) string {
	// 去掉协议前缀
	dsn := pythonDSN
	if idx := strings.Index(dsn, "://"); idx != -1 {
		dsn = dsn[idx+3:]
	}

	u, err := url.Parse("mysql://" + dsn)
	if err != nil {
		log.Fatalf("无法解析 DATABASE_URL: %v", err)
	}

	password, _ := u.User.Password()
	host := u.Hostname()
	port := u.Port()
	if port == "" {
		port = "3306"
	}

	goDSN := fmt.Sprintf("%s:%s@tcp(%s:%s)/%s",
		u.User.Username(), password, host, port, strings.TrimPrefix(u.Path, "/"))

	if u.RawQuery != "" {
		goDSN += "?" + u.RawQuery + "&parseTime=true"
	} else {
		goDSN += "?parseTime=true"
	}
	return goDSN
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func requireEnv(key string) string {
	v := os.Getenv(key)
	if v == "" {
		log.Fatalf("环境变量 %s 未设置，拒绝以不安全默认值启动", key)
	}
	return v
}
