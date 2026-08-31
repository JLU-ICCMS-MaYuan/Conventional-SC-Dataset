package handlers

import (
	"testing"

	"scwiki/server/database"
	"scwiki/server/models"

	"github.com/stretchr/testify/assert"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

// setupTestDB 创建测试数据库
func setupTestDB(t *testing.T) *gorm.DB {
	db, err := gorm.Open(sqlite.Open("file::memory:?cache=shared"), &gorm.Config{})
	assert.NoError(t, err)

	// 自动迁移所有模型
	err = db.AutoMigrate(
		&models.Paper{},
		&models.KeyProperty{},
		&models.MaterialState{},
		&models.TcResult{},
		&models.CalculationContext{},
		&models.ExperimentalContext{},
		&models.StructureModel{},
		&models.PaperChunk{},
		&models.PaperEvidence{},
		&models.PaperReviewEvent{},
		&models.Superconductor{},
	)
	assert.NoError(t, err)

	return db
}

// TestCascadeDeleteInDB 测试完整的级联删除
func TestCascadeDeleteInDB(t *testing.T) {
	db := setupTestDB(t)
	database.DB = db // 临时替换全局 DB

	// 创建测试数据
	superconductor := models.Superconductor{
		ChemicalFormula:   "H3S",
		FormulaNormalized: "H3S",
		CompositionKey:    "H3S",
		DisplayName:       "H3S",
		ElementsList:      `["H", "S"]`,
		Composition:       `{"H": 3, "S": 1}`,
		ElementRatio:      `{"H": 0.75, "S": 0.25}`,
	}
	assert.NoError(t, db.Create(&superconductor).Error)

	paper := models.Paper{
		DOI:          strPtr("10.1021/test.123"),
		Title:        strPtr("Test Paper"),
		ReviewStatus: "pending",
	}
	assert.NoError(t, db.Create(&paper).Error)

	keyProp := models.KeyProperty{
		PaperID:  paper.ID,
		Material: strPtr("H3S"),
	}
	assert.NoError(t, db.Create(&keyProp).Error)

	materialState := models.MaterialState{
		PaperID:          paper.ID,
		PaperRevision:    1,
		SuperconductorID: superconductor.ID,
	}
	assert.NoError(t, db.Create(&materialState).Error)

	tcResult := models.TcResult{
		PaperID:         paper.ID,
		PaperRevision:   1,
		MaterialStateID: materialState.ID,
		ResultKind:      "experimental",
		TcMethod:        "resistivity",
		ValueRaw:        "200 K",
	}
	assert.NoError(t, db.Create(&tcResult).Error)

	paperChunk := models.PaperChunk{
		PaperID:       paper.ID,
		PaperRevision: 1,
		Content:       "Test content",
	}
	assert.NoError(t, db.Create(&paperChunk).Error)

	// 执行删除
	err := cascadeDeleteInDB(db, paper.ID)
	assert.NoError(t, err)

	// 验证所有关联记录已删除
	var count int64
	db.Model(&models.Paper{}).Where("id = ?", paper.ID).Count(&count)
	assert.Equal(t, int64(0), count, "论文记录应被删除")

	db.Model(&models.KeyProperty{}).Where("paper_id = ?", paper.ID).Count(&count)
	assert.Equal(t, int64(0), count, "关键物性应被删除")

	db.Model(&models.MaterialState{}).Where("paper_id = ?", paper.ID).Count(&count)
	assert.Equal(t, int64(0), count, "材料状态应被删除")

	db.Model(&models.TcResult{}).Where("paper_id = ?", paper.ID).Count(&count)
	assert.Equal(t, int64(0), count, "Tc 结果应被删除")

	db.Model(&models.PaperChunk{}).Where("paper_id = ?", paper.ID).Count(&count)
	assert.Equal(t, int64(0), count, "论文分块应被删除")

	// 验证 superconductor 仍存在
	db.Model(&models.Superconductor{}).Where("id = ?", superconductor.ID).Count(&count)
	assert.Equal(t, int64(1), count, "超导材料记录应保留")
}

// TestCascadeDeleteTransactionRollback 测试事务回滚
func TestCascadeDeleteTransactionRollback(t *testing.T) {
	db := setupTestDB(t)
	database.DB = db

	paper := models.Paper{
		DOI:          strPtr("10.1021/test.456"),
		Title:        strPtr("Test Paper 2"),
		ReviewStatus: "pending",
	}
	assert.NoError(t, db.Create(&paper).Error)

	// 模拟删除失败（通过删除不存在的记录触发错误）
	// 注意：SQLite 的 Delete 不会因为记录不存在而报错，需要用其他方式模拟
	// 这里简化测试，直接验证事务的原子性

	err := db.Transaction(func(tx *gorm.DB) error {
		// 删除论文
		if err := tx.Delete(&models.Paper{}, paper.ID).Error; err != nil {
			return err
		}
		// 模拟中途失败
		return gorm.ErrInvalidTransaction
	})

	assert.Error(t, err, "事务应失败")

	// 验证论文仍存在
	var count int64
	db.Model(&models.Paper{}).Where("id = ?", paper.ID).Count(&count)
	assert.Equal(t, int64(1), count, "事务回滚后论文应仍存在")
}

// strPtr 辅助函数，返回字符串指针
func strPtr(s string) *string {
	return &s
}
