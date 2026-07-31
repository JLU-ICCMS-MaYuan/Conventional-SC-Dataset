package database

import (
	"log"

	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

// DB 全局数据库连接 —— *gorm.DB 是指针类型
// 对比 Python: db = SessionLocal()
var DB *gorm.DB

// Connect 连接 MySQL
func Connect(dsn string) {
	var err error
	// := 是声明 + 赋值（只用一次）
	// =  是赋值（已声明过的变量）
	DB, err = gorm.Open(mysql.Open(dsn), &gorm.Config{})
	if err != nil {
		log.Fatalf("MySQL 连接失败: %v", err) // Fatalf = 打印后退出
	}

	// 连接池配置
	sqlDB, _ := DB.DB()
	sqlDB.SetMaxOpenConns(25)           // 最大连接数
	sqlDB.SetMaxIdleConns(10)           // 最大空闲连接
	// defer sqlDB.Close() 不在这里 —— main 退出时关闭
}
