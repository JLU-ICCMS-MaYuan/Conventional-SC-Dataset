package models

import (
	"encoding/json"
	"time"
)

// ═══════════════════════════════════════════════
// Go struct → MySQL 表的映射规则：
//   - 字段名大写 = public（跨包可访问）
//   - `gorm:"..."` 控制数据库行为
//   - `json:"..."` 控制 JSON 序列化字段名
// ═══════════════════════════════════════════════

// User 用户
type User struct {
	ID                    uint            `gorm:"primaryKey" json:"id"`
	Email                 string          `gorm:"uniqueIndex;size:255" json:"email"`
	Username              string          `gorm:"uniqueIndex;size:32;not null;collate:ascii_bin" json:"username"`
	UsernameChangeAllowed bool            `gorm:"not null;default:false" json:"username_change_allowed"`
	PasswordHash          string          `gorm:"size:255" json:"-"`
	RealName              string          `gorm:"size:100" json:"-"`
	Affiliation           *string         `gorm:"size:255" json:"-"`
	AvatarKey             *string         `gorm:"size:500" json:"-"`
	ORCID                 *string         `gorm:"column:orcid;size:19;uniqueIndex" json:"-"`
	ResearchInterests     json.RawMessage `gorm:"type:json" json:"-"`
	Role                  string          `gorm:"size:50;default:user" json:"role"`
	IsApproved            bool            `json:"is_approved"`
	IsEmailVerified       bool            `json:"is_email_verified"`
	SessionVersion        int64           `gorm:"not null;default:0" json:"-"`
	AccountStatus         string          `gorm:"size:20;not null;default:active" json:"account_status"`
	CreatedAt             time.Time       `json:"created_at"`
	UpdatedAt             time.Time       `json:"updated_at"`
	ApprovedAt            *time.Time      `json:"approved_at"` // *time.Time = 可为 nil
}

// UsernameChangeAuditEvent 超级管理员更名的只追加审计事件。
type UsernameChangeAuditEvent struct {
	ID              uint      `gorm:"primaryKey" json:"id"`
	TargetUserID    uint      `gorm:"index:ix_username_audit_target_time,priority:1" json:"target_user_id"`
	ChangedByUserID uint      `gorm:"index:ix_username_audit_actor_time,priority:1" json:"changed_by_user_id"`
	OldUsername     string    `gorm:"size:32;not null;collate:ascii_bin" json:"old_username"`
	NewUsername     string    `gorm:"size:32;not null;collate:ascii_bin" json:"new_username"`
	Reason          string    `gorm:"size:500;not null" json:"reason"`
	CreatedAt       time.Time `gorm:"index:ix_username_audit_target_time,priority:2;index:ix_username_audit_actor_time,priority:2" json:"created_at"`
}

type ProfileChangeAuditEvent struct {
	ID              uint64    `gorm:"primaryKey" json:"id"`
	TargetUserID    uint      `gorm:"not null;index:ix_profile_audit_target_time,priority:1" json:"target_user_id"`
	ChangedByUserID uint      `gorm:"not null" json:"changed_by_user_id"`
	FieldName       string    `gorm:"size:32;not null" json:"field_name"`
	OldValue        *string   `gorm:"type:text" json:"old_value"`
	NewValue        *string   `gorm:"type:text" json:"new_value"`
	CreatedAt       time.Time `gorm:"index:ix_profile_audit_target_time,priority:2" json:"created_at"`
}

type AdminApplication struct {
	ID                        uint64          `gorm:"primaryKey" json:"id"`
	UserID                    uint            `gorm:"not null;uniqueIndex:uq_admin_application_pending,priority:1" json:"user_id"`
	RealNameSnapshot          string          `gorm:"size:100;not null" json:"real_name_snapshot"`
	AffiliationSnapshot       string          `gorm:"size:255;not null" json:"affiliation_snapshot"`
	ORCIDSnapshot             *string         `gorm:"column:orcid_snapshot;size:19" json:"orcid_snapshot"`
	ResearchInterestsSnapshot json.RawMessage `gorm:"type:json" json:"research_interests_snapshot"`
	Status                    string          `gorm:"size:20;not null;default:pending" json:"status"`
	PendingGuard              *bool           `gorm:"uniqueIndex:uq_admin_application_pending,priority:2" json:"-"`
	ReviewedByUserID          *uint           `json:"reviewed_by_user_id"`
	RejectionReason           *string         `gorm:"type:text" json:"rejection_reason"`
	SubmittedAt               time.Time       `json:"submitted_at"`
	WithdrawnAt               *time.Time      `json:"withdrawn_at"`
	ReviewedAt                *time.Time      `json:"reviewed_at"`
}

type UserGovernanceAuditEvent struct {
	ID           uint64    `gorm:"primaryKey" json:"id"`
	ActorUserID  uint      `gorm:"not null" json:"actor_user_id"`
	TargetUserID uint      `gorm:"not null;index:ix_governance_target_time,priority:1" json:"target_user_id"`
	EventType    string    `gorm:"size:32;not null" json:"event_type"`
	OldRole      *string   `gorm:"size:50" json:"old_role"`
	NewRole      *string   `gorm:"size:50" json:"new_role"`
	OldStatus    *string   `gorm:"size:20" json:"old_status"`
	NewStatus    *string   `gorm:"size:20" json:"new_status"`
	Reason       string    `gorm:"type:text;not null" json:"reason"`
	CreatedAt    time.Time `gorm:"index:ix_governance_target_time,priority:2" json:"created_at"`
}

// Paper 论文
type Paper struct {
	ID                uint       `gorm:"primaryKey;uniqueIndex:uq_papers_id_content_revision,priority:1" json:"id"`
	DOI               *string    `gorm:"size:255" json:"doi"`
	Title             *string    `json:"title"`
	Journal           *string    `json:"journal"`
	Volume            *string    `json:"volume"`
	Pages             *string    `json:"pages"`
	Year              *int       `json:"year"`
	Abstract          *string    `json:"abstract"`
	Authors           *string    `json:"authors"` // JSON string
	ReviewStatus      string     `gorm:"size:50;default:pending" json:"review_status"`
	ContentRevision   uint       `gorm:"not null;default:1;uniqueIndex:uq_papers_id_content_revision,priority:2" json:"content_revision"`
	ApprovedRevision  *uint      `json:"approved_revision"`
	ReviewComment     *string    `json:"review_comment"`
	AdminInternalNote *string    `json:"admin_internal_note"`
	ReviewedBy        *uint      `gorm:"column:reviewed_by_user_id" json:"reviewed_by_user_id"`
	UploadedBy        *uint      `gorm:"column:uploaded_by_user_id" json:"uploaded_by_user_id"`
	UploadTaskID      *string    `gorm:"size:32;uniqueIndex" json:"upload_task_id"`
	ReviewedAt        *time.Time `json:"reviewed_at"`
	CreatedAt         time.Time  `json:"created_at"`
	UpdatedAt         time.Time  `json:"updated_at"`
	// LLM 富化字段
	Summary            *string `json:"summary"`
	PaperType          *string `gorm:"size:20" json:"paper_type"`
	TheoreticalSubtype *string `gorm:"size:20" json:"theoretical_subtype"`
	KeywordsTags       *string `json:"keywords_tags"`
	Methodology        *string `json:"methodology"`
	KeyFinding         *string `json:"key_finding"`
	Rationale          *string `json:"rationale"`
	ResearchMaterials  *string `json:"research_materials"`
	MaterialRelations  *string `json:"material_relations"`
	BuildsOn           *string `json:"builds_on"`

	// 关联（GORM 预加载用）
	Reviewer       *User              `gorm:"foreignKey:ReviewedBy" json:"-"`
	Uploader       *User              `gorm:"foreignKey:UploadedBy" json:"-"`
	Files          []PaperFile        `gorm:"foreignKey:PaperID,PaperRevision;references:ID,ContentRevision" json:"files,omitempty"`
	Chunks         []PaperChunk       `gorm:"foreignKey:PaperID,PaperRevision;references:ID,ContentRevision" json:"chunks,omitempty"`
	Evidences      []PaperEvidence    `gorm:"foreignKey:PaperID,PaperRevision;references:ID,ContentRevision" json:"evidences,omitempty"`
	ReviewEvents   []PaperReviewEvent `gorm:"foreignKey:PaperID;references:ID" json:"review_events,omitempty"`
	MaterialStates []MaterialState    `gorm:"foreignKey:PaperID,PaperRevision;references:ID,ContentRevision" json:"material_states,omitempty"`
	KeyProperties  []KeyProperty      `gorm:"foreignKey:PaperID,PaperRevision;references:ID,ContentRevision" json:"key_properties,omitempty"`
}

// PaperFile 当前论文 revision 的正文、补充材料或附件。
type PaperFile struct {
	ID               uint      `gorm:"primaryKey;uniqueIndex:uq_paper_files_identity_revision,priority:1" json:"id"`
	PaperID          uint      `gorm:"not null;index:ix_paper_files_paper_revision,priority:1;uniqueIndex:uq_paper_files_identity_revision,priority:2" json:"paper_id"`
	PaperRevision    uint      `gorm:"not null;default:1;index:ix_paper_files_paper_revision,priority:2;uniqueIndex:uq_paper_files_identity_revision,priority:3" json:"paper_revision"`
	Role             string    `gorm:"size:20;not null" json:"role"`
	OriginalFilename string    `gorm:"size:500;not null" json:"original_filename"`
	StoredPath       string    `gorm:"size:500;not null" json:"stored_path"`
	SHA256           string    `gorm:"size:64;not null;index" json:"sha256"`
	Size             int64     `gorm:"not null" json:"size"`
	MediaType        *string   `gorm:"size:100" json:"media_type"`
	SortOrder        int       `gorm:"not null;default:0" json:"sort_order"`
	MainMarker       *uint     `gorm:"->" json:"-"`
	CreatedAt        time.Time `json:"created_at"`
}

// PaperChunk 当前论文 revision 的文本块。
type PaperChunk struct {
	ID            uint      `gorm:"primaryKey;uniqueIndex:uq_paper_chunks_identity_revision,priority:1" json:"id"`
	PaperID       uint      `gorm:"not null;index:ix_paper_chunks_paper_revision,priority:1;uniqueIndex:uq_paper_chunks_identity_revision,priority:2" json:"paper_id"`
	PaperRevision uint      `gorm:"not null;default:1;index:ix_paper_chunks_paper_revision,priority:2;uniqueIndex:uq_paper_chunks_identity_revision,priority:3" json:"paper_revision"`
	PaperFileID   uint      `gorm:"not null;index" json:"paper_file_id"`
	ChunkIndex    int       `gorm:"not null;uniqueIndex:uq_paper_chunks_file_index,priority:2" json:"chunk_index"`
	SectionName   *string   `gorm:"size:500" json:"section_name"`
	Heading       *string   `gorm:"size:500" json:"heading"`
	Content       string    `gorm:"type:longtext;not null" json:"content"`
	TokenCount    *int      `json:"token_count"`
	PageStart     *int      `json:"page_start"`
	PageEnd       *int      `json:"page_end"`
	CreatedAt     time.Time `json:"created_at"`
}

// PaperEvidence 当前论文 revision 中直接锚定 Chunk 的证据快照。
type PaperEvidence struct {
	ID            uint      `gorm:"primaryKey;uniqueIndex:uq_paper_evidences_identity_revision,priority:1" json:"id"`
	PaperID       uint      `gorm:"not null;index:ix_paper_evidences_paper_revision,priority:1;uniqueIndex:uq_paper_evidences_identity_revision,priority:2" json:"paper_id"`
	PaperRevision uint      `gorm:"not null;default:1;index:ix_paper_evidences_paper_revision,priority:2;uniqueIndex:uq_paper_evidences_identity_revision,priority:3" json:"paper_revision"`
	PaperChunkID  uint      `gorm:"not null;index" json:"paper_chunk_id"`
	FieldPath     string    `gorm:"size:255;not null" json:"field_path"`
	Section       *string   `gorm:"size:500" json:"section"`
	PageStart     *int      `json:"page_start"`
	PageEnd       *int      `json:"page_end"`
	Quote         string    `gorm:"type:longtext;not null" json:"quote"`
	CreatedAt     time.Time `json:"created_at"`
}

// PaperReviewEvent 一次不可变、覆盖整篇论文 revision 的审核动作。
type PaperReviewEvent struct {
	ID                     uint            `gorm:"primaryKey" json:"id"`
	PaperID                uint            `gorm:"not null;index:ix_paper_review_events_paper_revision,priority:1" json:"paper_id"`
	PaperRevision          uint            `gorm:"not null;default:1;index:ix_paper_review_events_paper_revision,priority:2" json:"paper_revision"`
	ReviewerUserID         uint            `gorm:"index:ix_paper_review_events_reviewer_time,priority:1" json:"reviewer_user_id"`
	Status                 string          `gorm:"size:50" json:"status"`
	ReviewComment          *string         `json:"review_comment"`
	ReviewedAt             time.Time       `gorm:"index:ix_paper_review_events_reviewer_time,priority:2;index:ix_paper_review_events_paper_revision,priority:3" json:"reviewed_at"`
	RequestID              *string         `gorm:"size:64;uniqueIndex" json:"request_id"`
	Source                 string          `gorm:"size:20" json:"source"`
	ClassificationSnapshot json.RawMessage `gorm:"type:json" json:"-"`
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
	ID                uint            `gorm:"primaryKey" json:"id"`
	ChemicalSystemID  uint            `json:"chemical_system_id"`
	ChemicalFormula   string          `gorm:"size:255" json:"chemical_formula"`
	FormulaNormalized string          `gorm:"uniqueIndex;size:255" json:"formula_normalized"`
	CompositionKey    string          `gorm:"uniqueIndex;size:255;not null" json:"composition_key"`
	IsotopeSignature  *string         `gorm:"size:255;index" json:"isotope_signature"`
	DisplayName       string          `gorm:"size:255" json:"display_name"`
	ElementsList      string          `gorm:"type:json" json:"elements_list"`
	Composition       string          `gorm:"type:json" json:"composition"`
	ElementRatio      string          `gorm:"type:json" json:"element_ratio"`
	MaterialStates    []MaterialState `gorm:"foreignKey:SuperconductorID" json:"material_states,omitempty"`
}

type MaterialFamily struct {
	ID              uint                  `gorm:"primaryKey" json:"id"`
	Code            string                `gorm:"size:64;not null;uniqueIndex" json:"-"`
	NameZH          string                `gorm:"column:name_zh;size:100;not null;uniqueIndex" json:"name"`
	NameEN          string                `gorm:"column:name_en;size:160" json:"-"`
	NormalizedName  string                `gorm:"size:160;not null;uniqueIndex" json:"-"`
	CreatedByUserID *uint                 `json:"created_by_user_id,omitempty"`
	CreatedAt       time.Time             `json:"created_at"`
	UpdatedAt       time.Time             `json:"updated_at"`
	Aliases         []MaterialFamilyAlias `gorm:"foreignKey:MaterialFamilyID" json:"aliases,omitempty"`
}

type MaterialFamilyAlias struct {
	ID               uint      `gorm:"primaryKey" json:"id"`
	MaterialFamilyID uint      `gorm:"not null;index" json:"material_family_id"`
	Alias            string    `gorm:"size:160;not null" json:"alias"`
	NormalizedAlias  string    `gorm:"size:160;not null;uniqueIndex" json:"-"`
	Language         string    `gorm:"size:10;not null;default:other" json:"language"`
	CreatedByUserID  *uint     `json:"created_by_user_id,omitempty"`
	CreatedAt        time.Time `json:"created_at"`
}

type StructureFamily struct {
	ID              uint                   `gorm:"primaryKey" json:"id"`
	Code            string                 `gorm:"size:64;not null;uniqueIndex" json:"-"`
	NameZH          string                 `gorm:"column:name_zh;size:100;not null;uniqueIndex" json:"name"`
	NameEN          string                 `gorm:"column:name_en;size:160" json:"-"`
	NormalizedName  string                 `gorm:"size:160;not null;uniqueIndex" json:"-"`
	CreatedByUserID *uint                  `json:"created_by_user_id,omitempty"`
	CreatedAt       time.Time              `json:"created_at"`
	UpdatedAt       time.Time              `json:"updated_at"`
	Aliases         []StructureFamilyAlias `gorm:"foreignKey:StructureFamilyID" json:"aliases,omitempty"`
}

type StructureFamilyAlias struct {
	ID                uint      `gorm:"primaryKey" json:"id"`
	StructureFamilyID uint      `gorm:"not null;index" json:"structure_family_id"`
	Alias             string    `gorm:"size:160;not null" json:"alias"`
	NormalizedAlias   string    `gorm:"size:160;not null;uniqueIndex" json:"-"`
	Language          string    `gorm:"size:10;not null;default:other" json:"language"`
	CreatedByUserID   *uint     `json:"created_by_user_id,omitempty"`
	CreatedAt         time.Time `json:"created_at"`
}

// MaterialState 一篇论文当前 revision 中材料的条件化状态。
type MaterialState struct {
	ID                       uint64                         `gorm:"primaryKey;uniqueIndex:uq_material_states_identity_revision,priority:1" json:"id"`
	PaperID                  uint                           `gorm:"not null;index:ix_material_states_paper_revision,priority:1;uniqueIndex:uq_material_states_identity_revision,priority:2" json:"paper_id"`
	PaperRevision            uint                           `gorm:"not null;index:ix_material_states_paper_revision,priority:2;uniqueIndex:uq_material_states_identity_revision,priority:3" json:"paper_revision"`
	SuperconductorID         uint                           `gorm:"not null;index" json:"superconductor_id"`
	MaterialFamilyID         *uint                          `gorm:"index" json:"material_family_id"`
	ElementCount             *int16                         `json:"element_count"`
	MaterialDimensionality   string                         `gorm:"size:32;not null;default:unknown" json:"material_dimensionality"`
	SuperconductorKind       string                         `gorm:"size:32;not null;default:unknown" json:"superconductor_kind"`
	PressureValueGPa         *float64                       `json:"pressure_value_gpa"`
	PressureMinGPa           *float64                       `json:"pressure_min_gpa"`
	PressureMaxGPa           *float64                       `json:"pressure_max_gpa"`
	PressureRaw              *string                        `gorm:"size:255" json:"pressure_raw"`
	PressureUnitRaw          *string                        `gorm:"size:50" json:"pressure_unit_raw"`
	ReportedSpaceGroupSymbol *string                        `gorm:"size:100" json:"reported_space_group_symbol"`
	ReportedSpaceGroupNumber *int16                         `json:"reported_space_group_number"`
	TemperatureValueK        *float64                       `json:"temperature_value_k"`
	TemperatureRaw           *string                        `gorm:"size:255" json:"temperature_raw"`
	TemperatureUnitRaw       *string                        `gorm:"size:50" json:"temperature_unit_raw"`
	MagneticFieldT           *float64                       `json:"magnetic_field_t"`
	StateKind                string                         `gorm:"size:20;not null;default:unknown" json:"state_kind"`
	Note                     *string                        `json:"note"`
	CreatedAt                time.Time                      `json:"created_at"`
	UpdatedAt                time.Time                      `json:"updated_at"`
	Structures               []StructureModel               `gorm:"foreignKey:MaterialStateID" json:"structures,omitempty"`
	CalculationContexts      []CalculationContext           `gorm:"foreignKey:MaterialStateID" json:"calculation_contexts,omitempty"`
	ExperimentalContexts     []ExperimentalContext          `gorm:"foreignKey:MaterialStateID" json:"experimental_contexts,omitempty"`
	TcResults                []TcResult                     `gorm:"foreignKey:MaterialStateID" json:"tc_results,omitempty"`
	Properties               []SuperconductorProperty       `gorm:"foreignKey:MaterialStateID" json:"properties,omitempty"`
	Superconductor           Superconductor                 `gorm:"foreignKey:SuperconductorID" json:"superconductor,omitempty"`
	MaterialFamily           *MaterialFamily                `gorm:"foreignKey:MaterialFamilyID" json:"material_family,omitempty"`
	StructureFamilyLinks     []MaterialStateStructureFamily `gorm:"foreignKey:MaterialStateID" json:"structure_families,omitempty"`
}

type MaterialStateStructureFamily struct {
	MaterialStateID   uint64          `gorm:"primaryKey" json:"material_state_id"`
	StructureFamilyID uint            `gorm:"primaryKey" json:"id"`
	IsPrimary         bool            `gorm:"not null;default:false" json:"is_primary"`
	PrimaryMarker     *uint64         `gorm:"->;uniqueIndex" json:"-"`
	CreatedAt         time.Time       `json:"created_at"`
	StructureFamily   StructureFamily `gorm:"foreignKey:StructureFamilyID" json:"structure_family"`
}

// StructureModel 论文内独立保存的一个结构模型。
type StructureModel struct {
	ID                  uint64    `gorm:"primaryKey" json:"id"`
	PaperID             uint      `gorm:"not null;index" json:"paper_id"`
	PaperRevision       uint      `gorm:"not null;index" json:"paper_revision"`
	MaterialStateID     uint64    `gorm:"not null;index" json:"material_state_id"`
	ParentStructureID   *uint64   `json:"parent_structure_id"`
	SpaceGroupSymbol    *string   `gorm:"size:100" json:"space_group_symbol"`
	SpaceGroupNumber    *int16    `json:"space_group_number"`
	StructureFormat     string    `gorm:"size:20;not null" json:"structure_format"`
	StructureText       string    `gorm:"type:longtext;not null" json:"structure_text"`
	StructureHash       string    `gorm:"size:64;not null;index" json:"structure_hash"`
	CellParameters      *string   `gorm:"type:json" json:"cell_parameters"`
	VolumeAngstrom3     *float64  `json:"volume_angstrom3"`
	AtomCount           *int      `json:"atom_count"`
	GeometryMethod      *string   `gorm:"size:100" json:"geometry_method"`
	NuclearTreatment    string    `gorm:"size:32;not null" json:"nuclear_treatment"`
	ExchangeCorrelation *string   `gorm:"size:100" json:"exchange_correlation"`
	CalculationCode     *string   `gorm:"size:100" json:"calculation_code"`
	MethodParameters    *string   `gorm:"type:json" json:"method_parameters"`
	SourceLocator       *string   `gorm:"size:500" json:"source_locator"`
	CreatedAt           time.Time `json:"created_at"`
	UpdatedAt           time.Time `json:"updated_at"`
}

// CalculationContext 理论 Tc 或普通物性的计算上下文。
type CalculationContext struct {
	ID                     uint64    `gorm:"primaryKey" json:"id"`
	PaperID                uint      `gorm:"not null;index" json:"paper_id"`
	PaperRevision          uint      `gorm:"not null;index" json:"paper_revision"`
	MaterialStateID        uint64    `gorm:"not null;index" json:"material_state_id"`
	StructureID            *uint64   `json:"structure_id"`
	MissingStructureReason *string   `json:"missing_structure_reason"`
	ElectronicMethod       *string   `gorm:"size:100" json:"electronic_method"`
	ExchangeCorrelation    *string   `gorm:"size:100" json:"exchange_correlation"`
	PseudopotentialType    *string   `gorm:"size:100" json:"pseudopotential_type"`
	PseudopotentialName    *string   `gorm:"size:255" json:"pseudopotential_name"`
	SpinOrbitCoupling      *bool     `json:"spin_orbit_coupling"`
	PhononMethod           *string   `gorm:"size:100" json:"phonon_method"`
	PhononNuclearTreatment string    `gorm:"size:32;not null" json:"phonon_nuclear_treatment"`
	EPCMethod              *string   `gorm:"column:epc_method;size:100" json:"epc_method"`
	MuStar                 *float64  `json:"mu_star"`
	LambdaEP               *float64  `gorm:"column:lambda_ep" json:"lambda_ep"`
	OmegaLogK              *float64  `json:"omega_log_k"`
	KGrid                  *string   `gorm:"size:100" json:"k_grid"`
	QGrid                  *string   `gorm:"size:100" json:"q_grid"`
	EnergyCutoffValue      *float64  `json:"energy_cutoff_value"`
	EnergyCutoffUnit       *string   `gorm:"size:50" json:"energy_cutoff_unit"`
	CalculationCode        *string   `gorm:"size:100" json:"calculation_code"`
	ParametersJSON         *string   `gorm:"type:json" json:"parameters_json"`
	CreatedAt              time.Time `json:"created_at"`
	UpdatedAt              time.Time `json:"updated_at"`
}

// ExperimentalContext 实验 Tc 的样品与测量上下文。
type ExperimentalContext struct {
	ID                     uint64    `gorm:"primaryKey" json:"id"`
	PaperID                uint      `gorm:"not null;index" json:"paper_id"`
	PaperRevision          uint      `gorm:"not null;index" json:"paper_revision"`
	MaterialStateID        uint64    `gorm:"not null;index" json:"material_state_id"`
	StructureID            *uint64   `json:"structure_id"`
	SampleLabel            *string   `gorm:"size:255" json:"sample_label"`
	SamplePreparation      *string   `json:"sample_preparation"`
	MeasurementMethod      *string   `gorm:"size:100" json:"measurement_method"`
	TcCriterion            string    `gorm:"size:64;not null" json:"tc_criterion"`
	AppliedFieldT          *float64  `json:"applied_field_t"`
	PressureUncertaintyGPa *float64  `json:"pressure_uncertainty_gpa"`
	ParametersJSON         *string   `gorm:"type:json" json:"parameters_json"`
	CreatedAt              time.Time `json:"created_at"`
	UpdatedAt              time.Time `json:"updated_at"`
}

// TcResult 一个方法、参数和判据下的纵向 Tc 结论。
type TcResult struct {
	ID                    uint64    `gorm:"primaryKey" json:"id"`
	PaperID               uint      `gorm:"not null;index" json:"paper_id"`
	PaperRevision         uint      `gorm:"not null;index" json:"paper_revision"`
	MaterialStateID       uint64    `gorm:"not null;index" json:"material_state_id"`
	CalculationContextID  *uint64   `json:"calculation_context_id"`
	ExperimentalContextID *uint64   `json:"experimental_context_id"`
	ResultKind            string    `gorm:"size:16;not null" json:"result_kind"`
	TcMethod              string    `gorm:"size:64;not null;index" json:"tc_method"`
	TcMethodCustom        *string   `gorm:"size:128" json:"tc_method_custom"`
	TcValueK              *float64  `json:"tc_value_k"`
	TcMinK                *float64  `json:"tc_min_k"`
	TcMaxK                *float64  `json:"tc_max_k"`
	UncertaintyK          *float64  `json:"uncertainty_k"`
	ValueRaw              string    `gorm:"size:255;not null" json:"value_raw"`
	UnitRaw               string    `gorm:"size:50;not null" json:"unit_raw"`
	SourceLocator         *string   `gorm:"size:500" json:"source_locator"`
	SourceFingerprint     string    `gorm:"size:64;not null" json:"source_fingerprint"`
	IsRepresentative      bool      `gorm:"not null;default:false" json:"is_representative"`
	RepresentativeMarker  *uint     `gorm:"->" json:"-"`
	CreatedAt             time.Time `json:"created_at"`
	UpdatedAt             time.Time `json:"updated_at"`
}

// PropertyDefinition 普通物性的规范定义；Tc 不进入此表。
type PropertyDefinition struct {
	ID            uint      `gorm:"primaryKey" json:"id"`
	Code          string    `gorm:"size:100;uniqueIndex;not null" json:"code"`
	DisplayName   string    `gorm:"size:255;not null" json:"display_name"`
	CanonicalUnit *string   `gorm:"size:50" json:"canonical_unit"`
	ValueKind     string    `gorm:"size:20;not null" json:"value_kind"`
	Description   *string   `json:"description"`
	IsActive      bool      `gorm:"not null;default:true" json:"is_active"`
	CreatedAt     time.Time `json:"created_at"`
	UpdatedAt     time.Time `json:"updated_at"`
}

// SuperconductorProperty 普通物性；原文列是网页展示的首选来源。
type SuperconductorProperty struct {
	ID                   uint64    `gorm:"primaryKey" json:"id"`
	PaperID              uint      `gorm:"not null;index" json:"paper_id"`
	PaperRevision        uint      `gorm:"not null;index" json:"paper_revision"`
	MaterialStateID      uint64    `gorm:"not null;index" json:"material_state_id"`
	StructureID          *uint64   `json:"structure_id"`
	CalculationContextID *uint64   `json:"calculation_context_id"`
	PropertyDefinitionID uint      `gorm:"not null;index" json:"property_definition_id"`
	Material             string    `gorm:"column:material_raw;size:255" json:"material"`
	NameRaw              string    `gorm:"size:255;not null" json:"name_raw"`
	ValueRaw             *string   `gorm:"type:text;not null" json:"value_raw"`
	Unit                 *string   `gorm:"column:unit_raw;size:100" json:"unit"`
	ValueNumber          *float64  `json:"value_number"`
	ValueMin             *float64  `json:"value_min"`
	ValueMax             *float64  `json:"value_max"`
	CanonicalUnit        *string   `gorm:"size:50" json:"canonical_unit"`
	ConditionNote        *string   `json:"condition_note"`
	SourceFingerprint    string    `gorm:"size:64;not null" json:"source_fingerprint"`
	CreatedAt            time.Time `json:"created_at"`
	UpdatedAt            time.Time `json:"updated_at"`

	// 旧 Handler 的临时编译兼容字段；不写入目标 Schema。
	SuperconductorID   *uint    `gorm:"-" json:"superconductor_id,omitempty"`
	Name               string   `gorm:"-" json:"name,omitempty"`
	NameNote           *string  `gorm:"-" json:"name_note,omitempty"`
	PressureGpa        *float64 `gorm:"-" json:"pressure_gpa,omitempty"`
	TemperatureK       *float64 `gorm:"-" json:"temperature_k,omitempty"`
	ConditionJSON      *string  `gorm:"-" json:"condition_json,omitempty"`
	IsPrimary          bool     `gorm:"-" json:"is_primary,omitempty"`
	SuperconductorType *string  `gorm:"-" json:"superconductor_type,omitempty"`
	ArticleType        *string  `gorm:"-" json:"article_type,omitempty"`
	SourceLabel        string   `gorm:"-" json:"source_label,omitempty"`
	StructureText      *string  `gorm:"-" json:"structure_text,omitempty"`
	StructureFormat    *string  `gorm:"-" json:"structure_format,omitempty"`
}

func (SuperconductorProperty) TableName() string { return "superconductor_properties" }

// KeyProperty 是旧 Handler 的临时类型别名；数据库表名已改为 superconductor_properties。
type KeyProperty = SuperconductorProperty

type TcResultEvidence struct {
	TcResultID      uint64 `gorm:"primaryKey" json:"tc_result_id"`
	PaperEvidenceID uint   `gorm:"primaryKey" json:"paper_evidence_id"`
	PaperID         uint   `gorm:"not null" json:"paper_id"`
	PaperRevision   uint   `gorm:"not null" json:"paper_revision"`
	EvidenceRole    string `gorm:"size:32;not null;default:primary" json:"evidence_role"`
}

type StructureModelEvidence struct {
	StructureID     uint64 `gorm:"primaryKey" json:"structure_id"`
	PaperEvidenceID uint   `gorm:"primaryKey" json:"paper_evidence_id"`
	PaperID         uint   `gorm:"not null" json:"paper_id"`
	PaperRevision   uint   `gorm:"not null" json:"paper_revision"`
	EvidenceRole    string `gorm:"size:32;not null;default:primary" json:"evidence_role"`
}

type SuperconductorPropertyEvidence struct {
	SuperconductorPropertyID uint64 `gorm:"primaryKey" json:"superconductor_property_id"`
	PaperEvidenceID          uint   `gorm:"primaryKey" json:"paper_evidence_id"`
	PaperID                  uint   `gorm:"not null" json:"paper_id"`
	PaperRevision            uint   `gorm:"not null" json:"paper_revision"`
	EvidenceRole             string `gorm:"size:32;not null;default:primary" json:"evidence_role"`
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
	ID                uint     `gorm:"primaryKey" json:"id"`
	GroupID           uint     `gorm:"index" json:"group_id"`
	KeyPropertyID     *uint    `json:"key_property_id"`
	SortOrder         int      `json:"sort_order"`
	CustomLabel       *string  `json:"custom_label"`
	CustomTc          *float64 `json:"custom_tc"`
	CustomPressure    *float64 `json:"custom_pressure"`
	CustomType        *string  `gorm:"size:20" json:"custom_type"`
	CustomArticleType *string  `gorm:"size:10" json:"custom_article_type"`
	CustomYear        *int     `json:"custom_year"`
}

// AlexandriaEntry Alexandria 外部数据集
type AlexandriaEntry struct {
	ID           uint     `gorm:"primaryKey" json:"id"`
	MatID        string   `gorm:"size:100" json:"mat_id"`
	Formula      *string  `gorm:"size:200" json:"formula"`
	Elements     *string  `json:"elements"`
	NSites       *int     `json:"nsites"`
	SPG          *int     `json:"spg"`
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
	ID          uint     `gorm:"primaryKey" json:"id"`
	Name        *string  `gorm:"size:200" json:"name"`
	Formula     *string  `gorm:"size:200" json:"formula"`
	ClassName   *string  `gorm:"size:100" json:"class_name"`
	Tc          *float64 `json:"tc"`
	Elements    string   `gorm:"type:json" json:"elements"`
	Composition string   `gorm:"type:json" json:"composition"`
}

func (HTSCMaterial) TableName() string { return "htsc2025_materials" }

// NewsItem 快讯
type NewsItem struct {
	ID        uint   `gorm:"primaryKey" json:"id"`
	EventDate string `gorm:"size:20" json:"event_date"`
	Title     string `gorm:"size:500" json:"title"`
	Summary   string `json:"summary"`
	Link      string `gorm:"size:1000" json:"link"`
}
