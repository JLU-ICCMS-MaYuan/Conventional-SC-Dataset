# Inspiration Agent 设计规格

> 日期: 2026-06-29
> 状态: 设计中
> 分支: rag

## 1. 背景与动机

### 1.1 现状

当前 `rag` 分支实现了两套问答管线：

- **普通 RAG 管线**：意图解析 → KG + RAG 检索 → LLM 生成回答
- **Brainstorm 管线**：5 阶段线性流程（了解方向 → 追问澄清 → 提出路径 → 生成计划 → 审核定稿）

Brainstorm 存在几个问题：

1. **阶段过于死板**——所有探索性对话都走相同流程，不管用户实际需要什么
2. **缺乏领域专精**——是通用头脑风暴，不理解超导文献的特殊结构（缺口、矛盾、类比等）
3. **输出质量不可审计**——没有强制证据绑定，没有双角色自省机制

### 1.2 目标

将 Brainstorm 替换为 **Inspiration Agent**——一个领域专精的科研灵感激发引擎。

核心差异：

| 维度 | 旧 brainstorm | 新 inspiration |
|------|-------------|---------------|
| 模式 | 单一 5 阶段线性 | 5 种可路由的思考模式 |
| 证据 | 简单 [PID_xxx] 引用 | 证据绑定 + 推理链 + 假设前提 |
| 质量 | 第 5 阶段自审 | 双角色自省（生成者 → 审稿人） |
| 入口 | 自动意图检测 | "探索"按钮主动触发 |
| 输出 | 纯对话文本 | 对话 + 嵌入式 IdeaCard + ReviewVerdict |

## 2. 用户故事

- **研究者**：在浏览 La-H 文献时点"探索"，系统分析 32 篇论文后指出 3 个缺口，其中一个关于 LaH₄ 的理论预测与实验缺失引起了注意。对话中切换为"成分空间漫步"，以 LaH₁₀ 为起点生成 Ba-Si-H 等候选三元组合。
- **学生**：刚接触氢化物超导，点"探索"问"这个领域还有什么方向可做"，系统用缺口探测模式扫描 conclusion/future_work 片段，给出 5 个候选方向，每条附带原始文献句子和推理逻辑。
- **实验员**：看到两篇论文对 H₃S 的 Tc 报道差异很大（203 K vs 190 K），点"探索"后系统自动触发矛盾催化模式，列出可能原因并建议验证实验。

## 3. 架构设计

### 3.1 分层架构

```
用户问题 (explore: true)
        │
        ▼
┌─────────────────────────────────┐
│  engine.py (ask_stream 扩展)     │
│  → 创建/恢复 InspirationSession  │
│  → SSE: inspire_enter            │
└──────────────┬──────────────────┘
               │
      ┌────────▼────────┐
      │  ModeRouter      │  mode_router.py
      │  LLM ×1           │
      │  输入: 用户问题    │
      │  输出: mode +      │
      │  search_queries   │
      └────────┬────────┘
               │
      ┌────────▼────────┐
      │  Retrieval       │  retrieval.py
      │  5 种策略         │
      │  共享 RAG + KG    │
      └────────┬────────┘
               │
      ┌────────▼────────┐
      │  EvidenceBuilder │  evidence.py
      │  LLM ×1           │
      │  生成对话 +        │
      │  <!--IDEA_CARD--> │
      └────────┬────────┘
               │
      ┌────────▼────────┐
      │  DualReviewer    │  reviewer.py
      │  LLM ×1           │
      │  审稿 +            │
      │  <!--REVIEW-->    │
      └────────┬────────┘
               │
      ┌────────▼────────┐
      │  SSE Stream      │
      │  token +          │
      │  evidence_card +  │
      │  review_verdict   │
      └──────────────────┘
```

每次探索模式对话触发 **3 次 LLM 调用**（路由 + 生成 + 审核），加上初始检索共 4 个异步步骤。

### 3.2 模块职责

| 模块 | 文件 | 行数估 | 职责 |
|------|------|--------|------|
| Session | `inspiration/session.py` | ~80 | `InspirationSession` 状态管理、持久化、恢复 |
| Prompts | `inspiration/prompts.py` | ~150 | 5 种模式 + 路由 + 生成 + 审核的 prompt 模板 |
| ModeRouter | `inspiration/mode_router.py` | ~80 | LLM 判断模式 + 生成搜索查询 |
| Retrieval | `inspiration/retrieval.py` | ~120 | 5 种检索策略注册表 + 统一执行入口 |
| EvidenceBuilder | `inspiration/evidence.py` | ~100 | 对话生成 + IdeaCard 嵌入式输出 |
| DualReviewer | `inspiration/reviewer.py` | ~80 | 双角色自省 + ReviewVerdict 输出 |
| Engine 扩展 | `engine.py` | +40 | explore 参数路由到 inspiration 管线 |
| API 层 | `api/rag.py` | +5 | SSE 端点读取 explore 参数 |

### 3.3 与旧代码的关系

- `brainstorm.py` 标记为 deprecated（模块级 docstring + 注释），不再被 engine.py 调用
- `MAIN_AGENT_SYSTEM_PROMPT` 中 brainstorm 相关部分标注 deprecated
- `BrainstormSession` 不被删除——git 历史可追溯，且不占用运行时资源
- `engine.py` 中原 brainstorm 路由分支替换为 inspiration 路由

## 4. 核心数据结构

### 4.1 InspirationSession

```python
@dataclass
class InspirationSession:
    session_id: str                    # uuid，用于持久化
    user_question: str                 # 触发探索的原始问题
    history: list[dict]                # 标准消息格式 [{role, content}]
    current_mode: str | None           # 当前思考模式
    collected_ideas: list[IdeaCard]    # 收集的点子
    rag_data: str                      # 预取的知识库上下文
    mode_history: list[str]            # 模式切换轨迹
```

与旧 `BrainstormSession` 的关键区别：
- `phase: int (1-5)` → `current_mode: str`（不再有固定阶段）
- `collected_info: list[str]` → `history: list[{role, content}]`（标准消息格式）
- `paths + plan_sheet` → `collected_ideas: list[IdeaCard]`（多点子收集）
- 新增 `mode_history` 追踪模式切换

### 4.2 IdeaCard

```python
@dataclass
class IdeaCard:
    title: str
    fragments: list[EvidenceFragment]  # 灵感来源文献片段
    reasoning_chain: str               # 推理逻辑
    assumptions: list[str]             # 假设前提
    feasibility: FeasibilityScore | None  # 审核后填充

@dataclass
class EvidenceFragment:
    paper_id: int
    quoted_text: str                   # 引用的原句
    section: str                       # 来自论文的哪个部分

@dataclass
class FeasibilityScore:
    overall: int                       # 1-5
    theory: int
    synthesis: int
    measurement: int
```

### 4.3 ModeResult

```python
@dataclass
class ModeResult:
    primary_mode: str                  # gap_detector | analogy_engine | ...
    secondary_modes: list[str]
    confidence: float
    search_queries: list[str]          # 由 LLM 动态生成的搜索查询
    rationale: str                     # 为什么选择这个模式
```

### 4.4 ReviewVerdict

```python
@dataclass
class ReviewVerdict:
    flaws: list[dict]                  # [{severity: "high/medium/low", description}]
    feasibility_score: int             # 1-5
    revised_idea: str                  # 修正后的点子描述
    dimensions: dict                   # {theory, synthesis, measurement} 各维度 1-5
```

## 5. 5 种思考模式

### 5.1 gap_detector（文献缺口探测器）

**触发场景**：用户想找未解决的研究问题、空白方向
**检索策略**：
- section_filter: `["conclusion", "future_work", "outlook"]`
- semantic_boost: `["research gap", "remains unclear", "future work", "beyond scope", "requires further"]`
- kg_enabled: false
**典型输出**：从论文结论/展望段提取缺口，归纳为具体研究方向

### 5.2 analogy_engine（类比推荐引擎）

**触发场景**：用户给一种成功策略，想找可迁移的其他体系
**检索策略**：
- section_filter: `["discussion", "results"]`
- semantic_boost: `["chemical precompression", "charge transfer", "electron-phonon coupling", "hydrogen cage"]`
- kg_enabled: true, kg_filter: `{"by_elements": true}`
**典型输出**：基于机制相似性推荐其他材料体系

### 5.3 contradiction_catalyst（矛盾证据催化器）

**触发场景**：用户关注某材料的争议数据、反常现象
**检索策略**：
- section_filter: `["results", "discussion"]`
- semantic_boost: `["discrepancy", "different", "however", "unexpected", "anomalous"]`
- kg_enabled: true, kg_filter: `{"by_formula": true, "cross_paper": true}`
**典型输出**：识别同一材料不同论文的 Tc/压力差异并推测原因

### 5.4 composition_walker（成分空间漫步）

**触发场景**：用户想基于已知化合物探索衍生/替换组合
**检索策略**：
- section_filter: `[]`（全文）
- semantic_boost: `["doping", "substitution", "ternary", "alloying"]`
- kg_enabled: true, kg_filter: `{"by_elements": true, "include_candidates": true}`
**典型输出**：元素周期表近邻替换生成多组分候选

### 5.5 counterfactual_reasoner（反事实推理器）

**触发场景**：颠覆性目标（如常压超导），需要非常规思路
**检索策略**：
- section_filter: `[]`
- semantic_boost: `["metastable", "pressure quenching", "template", "molecular cation", "quasi-hydrogen cage", "ambient pressure"]`
- kg_enabled: true, kg_filter: `{"max_pressure": 10}`
**典型输出**：结合亚稳/淬火/模板等非常规策略提出冒险但合理的点子

## 6. SSE 事件协议

### 6.1 新增事件类型

| 事件类型 | 触发时机 | payload |
|----------|---------|---------|
| `inspire_enter` | 进入探索模式 | `{session_id, mode, mode_label}` |
| `inspire_mode` | 模式切换 | `{mode, label, rationale}` |
| `evidence_card` | 每个点子生成后 | `IdeaCard` 完整 JSON |
| `review_verdict` | 审稿完成后 | `ReviewVerdict` 完整 JSON |
| `inspire_exit` | 退出探索模式 | `{reason: "user_abort" \| "completed"}` |

### 6.2 完整对话时序

```
→ inspire_enter
→ status: "正在分析问题并选择分析视角..."
→ status: "正在检索相关文献..."
→ token: "基于你的问题，我从三个角度来思考...\n\n"
→ token: "## 方向一：LaH₄ 的理论预测与实验缺失\n..."
→ evidence_card: {title: "LaH₄...", fragments: [...], ...}
→ token: "\n\n## 方向二：..."
→ evidence_card: {...}
→ status: "正在自我审核..."
→ token: "\n\n---\n**审稿意见：**\n..."
→ review_verdict: {flaws: [...], feasibility_score: 4, ...}
→ done: {session, ideas_count: 2}
```

## 7. 文件变更清单

| 文件 | 操作 | 估行 |
|------|------|------|
| `backend/rag/rag/inspiration/__init__.py` | 新建 | ~5 |
| `backend/rag/rag/inspiration/session.py` | 新建 | ~80 |
| `backend/rag/rag/inspiration/prompts.py` | 新建 | ~150 |
| `backend/rag/rag/inspiration/mode_router.py` | 新建 | ~80 |
| `backend/rag/rag/inspiration/retrieval.py` | 新建 | ~120 |
| `backend/rag/rag/inspiration/evidence.py` | 新建 | ~100 |
| `backend/rag/rag/inspiration/reviewer.py` | 新建 | ~80 |
| `backend/rag/rag/engine.py` | 修改 | +40 |
| `backend/api/rag.py` | 修改 | +5 |
| `frontend_test/src/hooks/useStreamingChat.ts` | 修改 | +30 |
| `frontend_test/src/pages/RagPage.tsx` | 修改 | +40 |
| `frontend_test/src/components/EvidenceCard.tsx` | 新建 | ~50 |
| `tests/inspiration/__init__.py` | 新建 | 0 |
| `tests/inspiration/test_mode_router.py` | 新建 | ~40 |
| `tests/inspiration/test_retrieval.py` | 新建 | ~50 |
| `tests/inspiration/test_evidence.py` | 新建 | ~40 |
| `tests/inspiration/test_reviewer.py` | 新建 | ~40 |
| `tests/inspiration/test_integration.py` | 新建 | ~60 |

## 8. 风险与约束

1. **3 次 LLM 调用延迟**：路由 + 生成 + 审核 ≈ 3-5 秒总延迟。通过 SSE 流式输出（生成阶段即开始推 token）缓解用户感知
2. **模式路由准确性**：LLM 可能选错模式。解决方案：secondary_modes 提供备选，用户可手动切换
3. **证据绑定可靠性**：LLM 可能编造 [PID_xxx]。解决方案：审稿阶段检查引用是否存在（二次检索验证留给 v2）
4. **不实施物理栅栏**：v1 仅做提示词层面的可行性约束，硬编码规则过滤器留给 v2
5. **不实施二次检索验证**：v1 审稿人只审核逻辑一致性，不检索反例，留给 v2

## 9. 与 qa.md 的差异

qa.md 描述的是完整愿景，v1 做了以下裁剪（YAGNI）：

| qa.md 特性 | v1 决策 |
|------------|--------|
| 向量库结构化分段（事实单元+元数据标签） | 暂不实施，先用现有 chunk 结构 |
| 物理化学硬栅栏（压力/稳定性/相容性） | 不硬编码，审稿人自然语言审核 |
| 二次检索反例验证 | v1 不实施 |
| 可行性雷达图前端展示 | 审稿维度用文本展示，雷达图 v2 |
| 一键深挖"现实障碍" | 不实施 |
| "先例地图" | 不实施 |
| 失败案例反馈闭环 | 不实施 |
| 引导式入口（3 条起始路径） | 不实施，用自由输入+探索按钮 |
