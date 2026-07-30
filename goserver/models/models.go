package models

import "time"

// ═══════════════════════════════════════════════
// Go struct → MySQL 表的映射规则：
//   - 字段名大写 = public（跨包可访问）
//   - `gorm:"..."` 控制数据库行为
//   - `json:"..."` 控制 JSON 序列化字段名
// ═══════════════════════════════════════════════

// User 用户
type User struct {
	ID              uint       `gorm:"primaryKey" json:"id"`
	Email           string     `gorm:"uniqueIndex;size:255" json:"email"`
	PasswordHash    string     `gorm:"size:255" json:"-"`
	RealName        string     `gorm:"size:100" json:"real_name"`
	Role            string     `gorm:"size:50;default:user" json:"role"`
	IsApproved      bool       `json:"is_approved"`
	IsEmailVerified bool       `json:"is_email_verified"`
	CreatedAt       time.Time  `json:"created_at"`
	ApprovedAt      *time.Time `json:"approved_at"` // *time.Time = 可为 nil
}

// Paper 论文
type Paper struct {
	ID           uint      `gorm:"primaryKey" json:"id"`
	DOI          *string   `gorm:"size:255" json:"doi"`
	Title        *string   `json:"title"`
	Journal      *string   `json:"journal"`
	Volume       *string   `json:"volume"`
	Pages        *string   `json:"pages"`
	Year         *int      `json:"year"`
	Abstract     *string   `json:"abstract"`
	Authors      *string   `json:"authors"` // JSON string
	ReviewStatus string    `gorm:"size:50;default:pending" json:"review_status"`
	ReviewComment *string  `json:"review_comment"`
	ReviewedBy   *uint    `json:"reviewed_by_user_id"`
	UploadedBy   *uint    `json:"uploaded_by_user_id"`
	CreatedAt    time.Time `json:"created_at"`
	UpdatedAt    time.Time `json:"updated_at"`
	// LLM 富化字段
	Summary            *string `json:"summary"`
	PaperType          *string `gorm:"size:20" json:"paper_type"`
	KeywordsTags       *string `json:"keywords_tags"`
	SourceFilePath     *string `gorm:"size:500" json:"source_file_path"`
	Methodology        *string `json:"methodology"`
	KeyFinding         *string `json:"key_finding"`
	Rationale          *string `json:"rationale"`
	ResearchMaterials  *string `json:"research_materials"`
	ReferencedMaterials *string `json:"referenced_materials"`
	MaterialRelations  *string `json:"material_relations"`
	BuildsOn           *string `json:"builds_on"`

	// 关联（GORM 预加载用）
	Reviewer       *User           `gorm:"foreignKey:ReviewedBy" json:"-"`
	Uploader       *User           `gorm:"foreignKey:UploadedBy" json:"-"`
	KeyProperties  []KeyProperty   `gorm:"foreignKey:PaperID" json:"key_properties,omitempty"`
}

// KeyProperty 物性记录
type KeyProperty struct {
	ID                 uint    `gorm:"primaryKey" json:"id"`
	PaperID            uint    `gorm:"index" json:"paper_id"`
	SuperconductorID   *uint   `gorm:"index" json:"superconductor_id"`
	Material           string  `gorm:"size:255;index" json:"material"`
	Name               string  `gorm:"size:100;index" json:"name"`
	NameRaw            string  `gorm:"size:255" json:"name_raw"`
	NameNote           *string `json:"name_note"`
	ValueMin           *float64 `json:"value_min"`
	ValueMax           *float64 `json:"value_max"`
	ValueRaw           *string `json:"value_raw"`
	Unit               *string `gorm:"size:50" json:"unit"`
	PressureGpa        *float64 `gorm:"index" json:"pressure_gpa"`
	TemperatureK       *float64 `json:"temperature_k"`
	ConditionJSON      *string `json:"condition_json"`
	ConditionNote      *string `json:"condition_note"`
	IsPrimary          bool    `gorm:"index;default:false" json:"is_primary"`
	SuperconductorType *string `gorm:"size:20;index" json:"superconductor_type"`
	ArticleType        *string `gorm:"size:10" json:"article_type"`
	SourceLabel        string  `gorm:"size:50;default:clean_results" json:"source_label"`
	StructureText      *string `json:"structure_text"`
	StructureFormat    *string `gorm:"size:20" json:"structure_format"`

	// 关联
	Paper         *Paper         `gorm:"foreignKey:PaperID" json:"-"`
	Superconductor *Superconductor `gorm:"foreignKey:SuperconductorID" json:"-"`
}

// ChemicalSystem 化学体系
type ChemicalSystem struct {
	ID           uint   `gorm:"primaryKey" json:"id"`
	SystemKey    string `gorm:"size:100" json:"system_key"`
	ElementsList string `json:"elements_list"`
	ElementCount int    `json:"element_count"`
}

// Superconductor 超导材料
type Superconductor struct {
	ID               uint   `gorm:"primaryKey" json:"id"`
	ChemicalSystemID uint   `json:"chemical_system_id"`
	ChemicalFormula  string `gorm:"size:255" json:"chemical_formula"`
	FormulaNormalized string `gorm:"uniqueIndex;size:255" json:"formula_normalized"`
	DisplayName      string `gorm:"size:255" json:"display_name"`
	ElementsList     string `json:"elements_list"`
	Composition      string `json:"composition"`
	ElementRatio     string `json:"element_ratio"`
}

// ChartGroup 图表组合
type ChartGroup struct {
	ID          uint      `gorm:"primaryKey" json:"id"`
	Name        string    `gorm:"size:255" json:"name"`
	Description *string   `json:"description"`
	IsPreset    bool      `gorm:"index;default:false" json:"is_preset"`
	IsPublic    bool      `gorm:"index;default:false" json:"is_public"`
	CreatedBy   *uint     `gorm:"index" json:"created_by"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`

	Items []ChartGroupItem `gorm:"foreignKey:GroupID" json:"items,omitempty"`
}

// ChartGroupItem 组合数据点
type ChartGroupItem struct {
	ID               uint    `gorm:"primaryKey" json:"id"`
	GroupID          uint    `gorm:"index" json:"group_id"`
	KeyPropertyID    *uint   `json:"key_property_id"`
	SortOrder        int     `json:"sort_order"`
	CustomLabel      *string `json:"custom_label"`
	CustomTc         *float64 `json:"custom_tc"`
	CustomPressure   *float64 `json:"custom_pressure"`
	CustomType       *string `gorm:"size:20" json:"custom_type"`
	CustomArticleType *string `gorm:"size:10" json:"custom_article_type"`
	CustomYear       *int    `json:"custom_year"`
}

// AlexandriaEntry Alexandria 外部数据集
type AlexandriaEntry struct {
	ID           uint    `gorm:"primaryKey" json:"id"`
	MatID        string  `gorm:"size:100" json:"mat_id"`
	Formula      *string `gorm:"size:200" json:"formula"`
	Elements     *string `json:"elements"`
	NSites       *int    `json:"nsites"`
	SPG          *int    `json:"spg"`
	LambdaVal    *float64 `json:"lambda_val"`
	TcMax        *float64 `json:"tc_max"`
	TcMcMillan   *float64 `json:"tc_mcmillan"`
	TcAllenDynes *float64 `json:"tc_allen_dynes"`
	TcEliashberg *float64 `json:"tc_eliashberg"`
	WLog         *float64 `json:"wlog"`
	DosEf        *float64 `json:"dos_ef"`
	BandGap      *float64 `json:"band_gap"`
	EAboveHull   *float64 `json:"e_above_hull"`
	StructureCIF *string  `json:"structure_cif"`
}

func (AlexandriaEntry) TableName() string { return "alexandria_entries" }

// AlexandriaElementIdx 元素→Alexandria 条目映射
type AlexandriaElementIdx struct {
	Element string `gorm:"size:5;primaryKey" json:"element"`
	EntryID uint   `gorm:"primaryKey" json:"entry_id"`
}

func (AlexandriaElementIdx) TableName() string { return "alexandria_element_idx" }

// HTSCMaterial HTSC-2025 外部数据集
type HTSCMaterial struct {
	ID        uint    `gorm:"primaryKey" json:"id"`
	Name      *string `gorm:"size:200" json:"name"`
	Formula   *string `gorm:"size:200" json:"formula"`
	ClassName *string `gorm:"size:100" json:"class_name"`
	Tc        *float64 `json:"tc"`
	Elements  *string  `json:"elements"`
	Composition *string `json:"composition"`
}

func (HTSCMaterial) TableName() string { return "htsc2025_materials" }
