# Memory Bank

Memory Bank 是项目长期有效背景、术语和稳定约束的导航入口。它只保存当前可确认的
事实；一次性变更计划保存在 `specs/`，可替代决策保存在 `docs/decisions/`。

## 当前页面

| 页面 | 职责 |
| --- | --- |
| [product.md](product.md) | 产品用户、目的、品牌与交互原则。 |
| [domain-context.md](domain-context.md) | SC-Wiki 的领域模型与核心术语边界。 |
| [rag-maintenance-mission.md](rag-maintenance-mission.md) | RAG 子系统维护与学习目标。 |
| [rag-glossary.md](rag-glossary.md) | RAG 相关术语的受控词汇表。 |
| [../domains/README.md](../domains/README.md) | 当前业务和模块边界。 |
| [../operations/README.md](../operations/README.md) | 当前运行、部署和恢复约束。 |

## 维护规则

- 修改代码前，读取与改动领域直接相关的页面。
- 只有已验证的当前事实才能写入；推断和未知项必须标注并建立后续 Issue。
- 变更影响稳定行为、约束或术语时，必须在 Issue 关闭前回写对应页面。
- 本目录不复制 Spec、ADR/Decision Note 或 GitHub Issue 的详细内容，只链接其权威
  位置。
