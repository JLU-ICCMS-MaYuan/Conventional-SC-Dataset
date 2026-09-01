# 接口契约：分类目录双语名与叙述字段英文化

**GitHub Issue**：[#74](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/74)

**日期**：2026-09-01（2026-09-01 范围修订：删除双语存储相关契约）

**Spec**：[../spec.md](../spec.md)

本 Feature 对接口只做**向后兼容的增量**：新增两个响应键、补齐一处写入白名单缺口。不改动现有键的语义或类型，不删除任何键，不新增端点。

## C1：分类目录接口增量返回英文名

`GET /api/classification-catalogs`（Go：`handlers.GetClassificationCatalogs`）

**权限**：无变化（公开可读）。

**响应变更**：`material_families[]` 与 `structure_families[]` 的每一项新增两个键。

```json
{
  "material_families": [
    { "id": 1, "name": "氢基超导体", "name_zh": "氢基超导体", "name_en": "Hydrogen-based superconductor", "aliases": ["hydride"] },
    { "id": 8, "name": "单质超导体", "name_zh": "单质超导体", "name_en": "", "aliases": [] }
  ],
  "structure_families": [],
  "material_dimensionalities": [{ "value": "three_dimensional", "name": "三维" }]
}
```

| 键 | 变更 | 约束 |
| --- | --- | --- |
| `name` | 保留不变 | 恒等于 `name_zh`，供既有调用点消费 |
| `name_zh` | 新增 | 非空 |
| `name_en` | 新增 | 可为空字符串（用户自建家族无英文名） |

**兼容性**：`name` 键语义不变，`ClassificationAutocomplete`、`ChartGroupEditor`、社区图表家族筛选等既有消费点无需改动即可继续工作（[../research.md](../research.md) R3）。

**`material_dimensionalities` 不变**：其 `name` 仍为中文。枚举标签由前端字典按 `value` 查表（R2），后端不承担语言协商。

**Python 侧对等**：`backend/services/classification_catalog.py` 的 `load_active_catalogs` 序列化输出同步增加 `name_zh` 与 `name_en`，保持两服务响应形状一致。

## C2：论文更新接口补齐 `knowledge_graph_title` 白名单

`PUT /api/admin/papers/:id`（Go：`handlers.UpdatePaper`）
`PATCH /api/papers/:id`（Go：`handlers.PatchPaper`）

**权限**：无变化。

**请求变更**：字段白名单新增 1 项。

| 新增可写字段 | 说明 |
| --- | --- |
| `knowledge_graph_title` | **补齐既有缺口**。该字段不在 `paperUpdateFields`（`goserver/handlers/admin.go:34-39`）与 `PatchPaper` 的 `allowed` map（`goserver/handlers/papers.go:155-162`）内，管理员编辑它会被静默丢弃——接口返回 200 但数据未保存 |

**这是最危险的失败模式**：无任何错误信号。因此该改动必须有测试覆盖（FR-019、SC-007）。

**与本 Feature 的关系**：该缺口与语言无关，是 Issue #70 遗留的贯通遗漏。因本 Feature 要求管理员能编辑六个叙述字段（FR-018），而 `knowledge_graph_title` 是其中之一，故在此一并修复。

## C3：论文详情接口不变

`GET /api/papers/:id`、`GET /api/admin/papers/:id`

**无变更**。六个叙述字段统一英文存储，不新增 `*_en` 键，不下发语言或同步状态元数据。前端两种界面语言下都读取并展示同一份字段值（FR-014）。

## C4：手工快讯接口不变

`GET /api/news`、`POST /api/admin/news`、`PUT /api/admin/news/:id`

**无变更**。`news_items` 不加列，超管以英文录入（FR-020）。

## C5：存量数据转换不暴露为接口

存量中文叙述字段的英文化通过一次性后端脚本执行，不提供 HTTP 端点。

**理由**：一次性维护动作，无需鉴权入口与前端界面；且按 FR-017 要求，转换验证完成后脚本即删除，不应留下长期接口。

**契约要求**：

- 只处理内容非空的字段（FR-016）。
- 单篇失败跳过并继续，最终输出失败清单（FR-016）。
- 转换后字段内容为英文，中日韩字符出现次数为 0（SC-005）。

## 范围修订说明

本文件早先版本包含以下契约，均已随「数据层统一英文」的范围修订而删除：

- `papers` 新增 6 个 `*_en` 键与 `narrative_en_sync` 同步状态对象的详情响应契约。
- `PUT /api/admin/papers/:id` 接受 6 个 `*_en` 字段与指纹维护规则。
- `POST /api/rag/papers/{paper_id}/narrative-translation` 重新生成英文端点。
- `news_items` 的 `title_en` / `summary_en` 键。
- 批量回填的幂等契约。

删除理由见 [../spec.md](../spec.md) 澄清记录 2026-09-01。
