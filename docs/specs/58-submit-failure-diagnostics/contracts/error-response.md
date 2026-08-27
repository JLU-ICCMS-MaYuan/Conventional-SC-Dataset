# 契约：提交失败的错误响应与前端反馈

**GitHub Issue**：[#58](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/58)

**Spec**：[../spec.md](../spec.md)

## 1. 后端错误响应体

### 1.1 既有契约（不变）

`_upload_error(status_code, code, message, **extra)` 产出：

```json
{ "detail": { "code": "state_material_required", "message": "第 3 个材料状态缺少材料" } }
```

`extra` 用于附加字段，如 DOI 重复时的 `existing_paper_id`。前端 `frontend/src/lib/api.ts:30-38` 从 `body.detail` 提取 `code`、`message`、`existing_paper_id`。

本 Feature 不修改该契约，也不修改 `_validate_draft` 的 12 个错误码。

### 1.2 新增：未捕获异常的响应（FR-004、FR-005）

修复前：Starlette 默认返回纯文本 `Internal Server Error`，`detail` 无法解析，前端只能回退通用文案。

修复后统一返回：

```json
{ "detail": { "code": "internal_error", "message": "<面向用户的中文说明>" } }
```

- HTTP 状态码：`500`
- `code`：稳定标识 `internal_error`
- `message`：固定的面向用户文案，**不含**异常原文

**必须排除的内容**（FR-005）：

| 禁止出现 | 实测示例 |
|---|---|
| 数据库驱动与错误码 | `asyncmy.errors.DataError`、`(1406, ...)` |
| 表名与列名 | `Data too long for column 'section_name'` |
| SQL 语句片段 | `INSERT INTO paper_chunks ...` |
| 堆栈与文件路径 | `File "/app/backend/api/rag.py", line 1102` |

完整异常信息记录到服务端日志，不进入响应体。

**已有 `HTTPException` 不受影响**：`_upload_error`、`_service_error` 产出的响应保持原样，全局处理器只处理未被捕获的异常（FR-006、US2 场景 4）。

## 2. 前端校验错误项（FR-007）

进程内结构，不经网络传输：

```ts
interface ValidationIssue {
  stateIndex?: number   // 材料状态序号（0 基）；论文级问题为 undefined
  field: string         // 字段标识，用于 DOM 定位
  message: string       // 面向用户的说明，进入横幅汇总
}
```

`validate()` 返回 `ValidationIssue[]`；空数组表示通过。

**与修复前的差异**：原签名为 `(): string | null` 且遇错即 `return`，只能报第一条且无位置信息。

### 2.1 字段标识与 DOM 锚点

字段定位通过 `data-*` 属性查询，不依赖 MUI 内部 DOM 结构（research D5）。锚点命名规则：

| 问题 | `field` | 锚点位置 |
|---|---|---|
| 标题为空 | `paper.title` | 论文标题输入框 |
| DOI 格式错误 | `paper.doi` | DOI 输入框 |
| 论文类型未选 | `paper.paper_type` | 论文整体类型选择器 |
| 理论二级类型未选 | `paper.theoretical_subtype` | 理论二级类型选择器 |
| 材料状态缺少材料 | `material_states[N].material` | 第 N 张卡片的材料输入框 |
| 空间群号越界 | `material_states[N].reported_space_group_number` | 第 N 张卡片的空间群号输入框 |
| 计算参数为负 | `material_states[N].calculation_context` | 第 N 张卡片的计算参数区 |
| Tc 缺少数值 | `material_states[N].tc_results` | 第 N 张卡片的 Tc 区 |
| 普通物性不完整 | `material_states[N].properties` | 第 N 张卡片的普通物性区 |

## 3. 提交失败的前端反馈行为

### 3.1 前端校验失败（FR-008、FR-009）

按顺序执行：

1. 若首个错误项含 `stateIndex`，展开该卡片（`setCollapsedStates`）——出错字段可能位于默认折叠的卡片内（卡片数 >2 时仅第一张展开）。
2. 滚动到首个错误字段的锚点并使其获得焦点。
3. 全部错误字段渲染 `error` 态与 `helperText`。
4. 横幅汇总**全部** `message`，不止第一条。
5. 不发起提交请求。

### 3.2 后端校验失败（FR-010）

后端 400 响应的 `message` 已含「第 N 个材料状态」（`rag.py:254`、`:282`、`:287`、`:293`、`:301`、`:307`、`:311`）。前端从该文案解析序号：

1. 解析成功 → 展开对应卡片并滚动，横幅显示后端 `message` 与 `code`。
2. 解析失败或无序号 → 仅显示横幅，不做定位（US2 场景 4、边界场景第 4 条）。

该文案解析是脆弱耦合，由专门单元测试保护（research D6）。

### 3.3 既有分支不变（SC-006）

| 情形 | 行为 |
|---|---|
| DOI 重复 409 `existing_paper_id` | 保持既有专门文案 `该 DOI 已存在（论文 #N）…` |
| 一致性确认 409 `consistency_ack_required` | 保持既有 `window.confirm` 二次提交流程 |
| 提交成功 | 清除全部错误态与横幅（FR-011） |

## 4. 章节判定契约（FR-001、FR-002）

`_split_by_h2` 对每个 `##` 行判定：

| 条件 | 判定 | `section_name` | 该行文本去向 |
|---|---|---|---|
| 长度 ≤ 300 | 真实标题 | 该行文本 | 作为 `heading`，不进入 `content`（既有行为） |
| 长度 > 300 | 正文内容 | 沿用前一个真实章节 | **并入该节 `body`，进入 `content`** |
| 长度 > 300 且无前置真实章节 | 正文内容 | `全文` | 并入 `body` |

阈值 300 的依据：实测真实标题上界 204、误判正文下界 389（research D1）。

写入 `PaperChunk` 前，`section_name` 与 `heading` 按 500 字符安全截断（FR-003）——与判定逻辑无关的第二道防线。
