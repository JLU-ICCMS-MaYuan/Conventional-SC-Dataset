# RAG Brainstorm 头脑风暴模式 — 设计文档

**日期:** 2026-06-26
**状态:** 待审查

---

## 1. 概述

在现有 RAG AI 文献助手中集成 Brainstorm 头脑风暴模式。该模式基于 superpowers:brainstorming skill 的核心思考过程：探索上下文 → 逐轮澄清 → 提出多路径 → 逐节呈现 → 收敛总结。Brainstorm 模式下 AI 以交互式对话引导用户深入理解问题、探索研究方向、形成可行方案。

## 2. 动机

**当前状态：** RAG 模块是单阶段问答——用户提问，AI 检索 + 生成答案。这对事实性查询（"LaH10 的 Tc 是多少？"）效果良好，但对探索性/模糊问题（"有什么有潜力的研究方向？"）无法提供结构化引导。

**目标：** 让 AI 能检测探索性意图，在获得用户确认后切换到 Brainstorm 模式，按五阶段状态机进行多轮交互式引导。

## 3. 架构

### 3.1 整体流程

```
用户问题
  │
  ▼
主 Agent (DeepSeek Function Calling)
  工具: [search_kg, search_rag, brainstorm]
  │
  ├─ 事实性查询 → 普通模式（查KG/RAG → 生成答案）
  │
  └─ 探索性意图 → 提议进入 Brainstorm 模式
                    │
                    ├─ 用户拒绝 → 普通模式回答
                    │
                    └─ 用户接受 → Brainstorm 状态机
                                   │
                                   ├─ Phase 1: 探索上下文
                                   ├─ Phase 2: 追问澄清（可循环）
                                   ├─ Phase 3: 提出2-3条路径
                                   ├─ Phase 4: 逐节呈现方案
                                   └─ Phase 5: 收敛总结 → 退出
```

### 3.2 状态机

| 阶段 | 名称 | AI行为 | 可用工具 | 推进条件 |
|------|------|--------|---------|---------|
| 1 | 探索上下文 | 复述理解 + 问一个澄清选择题 | KG ✅ RAG ✅ — 验证用户方向是否有数据支撑 | 用户回答 |
| 2 | 追问澄清 | 每次一问，逐步深入，最多5轮（配置项 `MAX_CLARIFY_ROUNDS`），满5轮若AI未发 [PHASE_COMPLETE] 则强制推进 | KG 按需 RAG 按需 — 用户提到具体化合物/属性时查数据，作为追问依据 | AI发 [PHASE_COMPLETE] 或 达到最大轮数 |
| 3 | 提出路径 | 给出2-3条方向 + 文献支撑 + 推荐 | KG ✅ RAG ✅ — 每条路径必须有数据支撑+文献证据 | 用户选择一条 |
| 4 | 逐节呈现 | 分4个小节，逐节等用户确认 | KG ✅ RAG ✅ — 每节深入搜索相关数据和文献 | 4节全部通过 |
| 5 | 收敛总结 | 汇总结论 + 文献 + 下一步 | KG ❌ RAG ❌ — 纯汇总，不再搜 | AI发 [BRAINSTORM_END] |

**退出机制：** 用户可在任何阶段说"退出"/"不用brainstorm"终止。
**降级机制：** 任何阶段 AI 如果无法推进（无数据支撑），降级为普通模式回答。

### 3.3 进入 Brainstorm 的判断条件

探索性意图检测方式：**LLM 分析判断**（在意图解析阶段扩展 `_extract_intent` 的输出字段，新增 `suggest_brainstorm: bool`），而非关键词匹配。满足以下任一特征：

判断依据（给 LLM 的分析指南）：
- 研究方向探索："有什么方向"、"潜力"、"idea"、"课题"
- 综述/比较："对比"、"哪个更好"、"发展趋势"
- 方法论："怎么做"、"如何设计实验"、"从哪入手"
- 用户明确请求："brainstorm"、"头脑风暴"、"帮我分析"

**关键规则：** 检测到探索性意图后，AI 必须先向用户确认，获同意后才进入 Brainstorm 模式。

## 4. 文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/rag/rag/brainstorm.py` | **新建** | 状态机 + 会话管理 + 各阶段 prompt |
| `backend/rag/rag/engine.py` | 修改 | 检测探索性意图 → 提议 brainstorm → 切换到 brainstorm 管线 |
| `backend/rag/rag/prompts.py` | 修改 | 新增 BRAINSTORM_PHASE_PROMPTS（5阶段 prompt）、更新主 Agent system prompt |
| `backend/rag/config.py` | 修改 | 新增 brainstorm 配置（最大追问轮数、超时等） |
| `backend/api/rag.py` | 修改 | SSE 新增 `brainstorm_enter` / `brainstorm_phase` / `brainstorm_options` / `brainstorm_exit` 事件 |
| `frontend_test/src/hooks/useStreamingChat.ts` | 修改 | 处理 brainstorm SSE 事件、跟踪 brainstorm 状态 |
| `frontend_test/src/pages/RagPage.tsx` | 修改 | Brainstorm UI（进度条、选项按钮、退出按钮、模式标记） |

## 5. 后端设计

### 5.1 `brainstorm.py` — 会话管理 + 子 Agent

Brainstorm 是一个递归 Agent，内部可调用 `search_kg` 和 `search_rag` 两个工具（通过 DeepSeek Function Calling 实现）。与主 Agent 的区别：
- 主 Agent 工具: `[search_kg, search_rag, brainstorm]`
- Brainstorm 子 Agent 工具: `[search_kg, search_rag]`（无 brainstorm 递归）

子 Agent 每次 Function Calling 最多 3 轮迭代，防止无限循环。

```python
class BrainstormPhase(IntEnum):
    EXPLORE = 1    # 探索上下文
    CLARIFY = 2    # 追问澄清（可循环）
    PROPOSE = 3    # 提出路径
    PRESENT = 4    # 逐节呈现方案
    SUMMARIZE = 5  # 收敛总结

class BrainstormSession:
    phase: BrainstormPhase
    context: dict            # {topic, domain, constraints, preferences}
    collected_info: list     # Phase 2 收集的用户偏好
    paths: list[dict]        # Phase 3 生成的路径
    selected_path: int | None
    present_section: int     # Phase 4 当前小节 (0-3)
    clarify_rounds: int      # Phase 2 追问计数

    def build_prompt(user_message, db_context, search_results) -> str
        # 根据当前 phase 返回对应阶段的 system prompt

    def advance(user_response) -> bool
        # 判断是否进入下一阶段
        # Phase 2: 检查 [PHASE_COMPLETE] 标记
        # Phase 3: 用户选择了路径
        # Phase 4: 4节全部通过
        # Phase 5: 用户确认总结
```

### 5.2 `prompts.py` — 各阶段 Prompt

**Phase 1 — 探索上下文**

```
你是学术头脑风暴助手。当前阶段: 探索上下文 (1/5)

用户问题: "{user_question}"
数据库概况: {db_context}

任务:
1. 用1-2句话总结你对用户探索方向的理解
2. 提一个澄清选择题（2-4选项），选项基于专业知识 + 数据库实际情况

先复述理解，再提问。只输出这些。
```

**Phase 2 — 追问澄清**

```
当前阶段: 追问澄清 (2/5)

已收集信息: {collected_info}

逐一追问关键问题。每次只问一个，优先选择题。
基于已回答问题逐步深入。信息足够时输出 [PHASE_COMPLETE] 结束。
```

**Phase 3 — 提出路径**

```
当前阶段: 提出路径 (3/5)

基于需求: {collected_info}
检索结果: {search_results}

提出2-3条具体思路。每条包含:
1. 思路标题（一句话）
2. 可行性评估（高/中/低，基于数据库数据）
3. 关键文献支撑（标注 [PID_xxx]）
4. 推荐理由

推荐一条并说明原因。最后让用户选择。
```

**Phase 4 — 逐节呈现**

```
当前阶段: 逐节呈现 (4/5)

将路径分4小节，逐节呈现:
1. 背景与研究现状
2. 候选材料/方法
3. 预期挑战与风险
4. 下一步具体建议

每节等用户确认（"好的"/"继续"）后前进。
```

**Phase 5 — 收敛总结**

```
当前阶段: 收敛总结 (5/5)

汇总:
- 讨论的问题与选定方向
- 关键结论
- 推荐下一步行动
- 相关文献列表

输出后加 [BRAINSTORM_END] 退出模式。
```

### 5.3 主 Agent System Prompt 更新

在现有 `FUSION_SYSTEM_PROMPT` 前加入模块能力声明：

```
你是氢化物超导文献专家。有以下工作模式：

## 普通模式
数据查询。结合工具结果直接回答。引用 [PID_xxx]。

## 头脑风暴模式
当用户问题涉及研究方向探索、综述比较、方法论，或用户明确请求时，
先问用户"要进入头脑风暴模式吗？"，确认后进入5阶段交互引导。
每阶段严格按该阶段规则执行，禁止跳步。用户说"退出"立即终止。

## 引用格式
所有数据引用使用 [PID_xxx]。禁止 [来源X]。
```

### 5.4 SSE 事件

| Event | Data | 触发时机 |
|-------|------|---------|
| `brainstorm_enter` | `{phase: 1, total: 5, label: "探索上下文"}` | 用户确认进入 Brainstorm |
| `brainstorm_phase` | `{phase: N, label: "..."}` | 阶段切换 |
| `brainstorm_options` | `{options: [{label, value}]}` | AI 发出选择题 |
| `brainstorm_exit` | `{reason: "completed"\|"user_abort"}` | 退出 Brainstorm |
| `token` | `{data: "文本..."}` | 流式文本（同现有） |
| `done` | `{answer, source, papers, top10}` | 生成完成（同现有） |

## 6. 前端设计

### 6.1 状态管理

在 `useStreamingChat` hook 中新增：
```typescript
interface BrainstormState {
  active: boolean
  phase: number       // 1-5
  phaseLabel: string
  totalPhases: 5
}
```

### 6.2 UI 变化

| 区域 | 变化 |
|------|------|
| 顶部进度条 | Brainstorm 模式下显示阶段进度 `🟢🟢⚪⚪⚪ 追问澄清 (2/5)` |
| AI 气泡 | 选项渲染为可点击按钮 |
| 输入框下方 | "退出头脑风暴" 按钮 |
| 左侧对话列表 | 当前对话标记 🧠 |
| 右侧文献来源 | 同现有逻辑 |

### 6.3 选项按钮交互

AI 返回选择题时，前端将选项渲染为按钮，点击后自动发送对应选项文本，无需用户手动输入。

## 7. 错误处理与边界情况

| 场景 | 处理 |
|------|------|
| Brainstorm 阶段数据不足 | 告知用户"当前数据库缺少相关数据"，降级为普通回答 |
| 用户输入不明确 | Phase 2 继续追问，不推进阶段 |
| DeepSeek API 超时 | 保留已有状态，提示重试 |
| 用户刷新页面 | 从对话历史恢复 brainstorm 状态。BS 状态 `{phase, collected_info, paths, selected_path, present_section}` 序列化存入 localStorage 的 `rag_meta_{conversation_id}` 中（扩展现有 `CachedMeta` 结构） |
| 多轮后用户放弃 | 任何阶段可通过"退出"终止 |
| 对话切换 | 不同对话独立维护 brainstorm 状态 |

## 8. 测试要点

1. 探索性意图检测准确率（5类样本各20条）
2. 5阶段推进逻辑正确（Playwright E2E）
3. 用户拒绝不进入 Brainstorm
4. 退出机制正常工作
5. SSE 事件序列完整
6. 对话历史恢复 brainstorm 状态
7. 各阶段 prompt 生成的回答质量
