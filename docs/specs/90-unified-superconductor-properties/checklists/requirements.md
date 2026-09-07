# 需求质量检查表：MaterialState 模块化物性与动态表单

**Feature**：[spec.md](../spec.md)

**重写日期**：2026-09-07

## 目标与边界

- [x] CHK001 已明确 `MaterialState` 是结构、Conditions 和物性模块的共同主体（FR-001）。
- [x] CHK002 已定义首批四个模块及按需挂载行为（FR-002–FR-004）。
- [x] CHK003 已说明模块是配置式扩展，不执行第三方插件代码（假设与范围外事项）。
- [x] CHK004 已明确跨模块只展示或引用，不复制同一科学事实（FR-003）。

## Tc 与 Conditions

- [x] CHK005 已区分 `predicted_tc`、`measured_tc` 和具体方法（FR-004、FR-007、FR-011）。
- [x] CHK006 已定义预测/测量 Tc 与计算/实验 Conditions 的强制关系（FR-007）。
- [x] CHK007 已定义一个 Conditions 表示一次确定执行，决定性输入不同必须拆分（FR-008–FR-010）。
- [x] CHK008 已覆盖两组 mu_star-Tc、互斥输入和实验多物性共享条件（US3、SC-002–SC-003）。
- [x] CHK009 已保留代表 Tc 唯一范围、非负值和单位规则（FR-011–FR-012）。

## Schema 驱动表单

- [x] CHK010 已区分固定核心字段、扩展 JSON 和各自权威（FR-005、FR-018–FR-019）。
- [x] CHK011 已定义 FormDefinition 的键、版本、状态、Schema、规则、校验和与审计（FR-015）。
- [x] CHK012 已定义发布不可变、停用后的历史读取和显式升级（FR-016–FR-017）。
- [x] CHK013 已明确前端生成表单、后端使用同版本最终校验（FR-013–FR-014）。
- [x] CHK014 已限制定义为声明式规则并限制超级管理员发布（FR-032）。
- [x] CHK015 已覆盖未知版本、校验失败和字段定位错误（FR-033）。

## 数据所有权与迁移

- [x] CHK016 已明确每篇论文 revision 拥有独立 ChemicalSystem 和 Superconductor（FR-020–FR-022）。
- [x] CHK017 已覆盖双论文 LaH10 的修改、删除和搜索隔离（US5、SC-006）。
- [x] CHK018 已定义 Contexts 到 Conditions 的目标改名且禁止长期双写（FR-023）。
- [x] CHK019 已定义旧 Tc、普通物性、参数和 Evidence 到统一记录的映射（FR-024–FR-028）。
- [x] CHK020 已使用分阶段迁移和恢复点，不假定 MySQL DDL 整体事务回滚（FR-029）。
- [x] CHK021 已要求逐项核对核心值与关联，且禁止伪造 Evidence（SC-007）。

## 接口与验收

- [x] CHK022 已定义模块、记录、Conditions 和定义版本的统一 API（FR-027）。
- [x] CHK023 已覆盖上传、管理、详情、搜索、图表、审核、升版和删除（FR-030）。
- [x] CHK024 已为全部 35 项 FR 建立 Tasks 覆盖映射。
- [x] CHK025 已为六个用户故事提供独立验收和 Quickstart 场景。
- [x] CHK026 已要求 Python、Go、前端和真实 MySQL 分阶段验证（FR-034、SC-011）。
- [x] CHK027 已把 Overview 更新放在实现验证之后（FR-035）。

## 结论

当前文档覆盖已确认的新设计基线，可以进入实施前的最终评审。实现开始前仍需确认运行库迁移窗口和
目标 Alembic head，这两项属于环境事实，不改变本 Feature 的领域设计。
