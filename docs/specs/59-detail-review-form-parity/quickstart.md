# 验收指引：只读详情页与校对表单一致

**Feature**：[spec.md](spec.md)

**日期**：2026-08-27

## 前置条件

- dev 栈位于 `/home/mayuan/work/SC-Wiki-docker`，compose 文件 `dev.yaml`，服务名 `frontend`。
- **前端改动生效需重建镜像**：代码经 `COPY` 打进镜像而非 bind mount，`restart` 不会加载工作区改动。
- 验收基准论文：paper 4（DOI 10.1073/pnas.1704505114，`review_status=pending`），需以上传者或管理员身份查看。
- 依赖 [#57](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/57)（已关闭）：详情接口已返回嵌套的 `tc_results`、`calculation_contexts`、`structures` 与完整材料状态字段。

## 自动化门槛

```bash
cd /home/mayuan/code/SC-Wiki/frontend && npm run test:upload-ui && npx tsc --noEmit
```

预期：既有 8 文件 65 用例 + 本 Feature 新增用例全部通过；`tsc` 无输出。

## 部署

```bash
cd /home/mayuan/work/SC-Wiki-docker && docker compose -f dev.yaml build frontend \
  && docker compose -f dev.yaml up -d frontend
```

## 场景 1：分类字段与校对页一致（US1，FR-001/FR-005，SC-001）

1. 打开 paper 4 的校对页（若任务已清理，以 [contracts/detail-view-fields.md](contracts/detail-view-fields.md) 的字段清单为基准）。
2. 打开 `/papers/4` 详情页，逐项比对材料状态。

**预期**：详情页材料状态展示材料、材料家族、不同元素种类数、材料维度、结构家族标签、晶系、空间群符号、空间群号、超导类型共 9 项。paper 4 应显示晶系 `cubic`、空间群 `Fm-3m`、群号 `225`、超导类型与维度。

**修复前对照**：只显示材料、材料家族、不同元素种类数 3 项，其余全缺。

## 场景 2：压强按单臂区间正确呈现（US1，FR-002，SC-002）

**预期**：paper 4 显示压强 250 GPa、原文压强 `above 200 GPa`、下限 200 GPa；**不显示**上限（库中为 NULL），也不把上限渲染为 0。

**修复前对照**：压强完全不显示。

## 场景 3：Tc 与计算上下文可见（US1，FR-003，SC-002）

**预期**：paper 4 的材料状态内显示 Tc 数值 274 K、Tc 方法，以及 λ=2.56、μ*=0.1。

**关键**：paper 4 有 **2 条**计算上下文，其中一条数值全为 NULL。两条都应展示；若只显示一条且恰为全 NULL 的那条，λ=2.56 会不可见——这是实现取首条时的典型错误。

**修复前对照**：Tc 与 λ/μ* 完全不显示。

## 场景 4：物性不再出现空的最小值/最大值（US1，FR-004，SC-003）

**预期**：paper 4 的物性显示名称 `thermodynamic stability`、原始值 `0`、解析值 200、单位 `meV/atom`。页面**不出现**「最小值」「最大值」两个空字段。

**已知数据事实**：原始值 `0` 与解析值 200 不一致，属写入侧历史数据问题（范围外）。详情页如实呈现两者，不是本 Feature 的缺陷。

**修复前对照**：最显眼位置是两个恒空的「最小值」「最大值」框，而真正有值的解析值与单位不显示。

## 场景 5：字段语义与形态正确（US2，FR-006~FR-008，SC-003/SC-004）

**预期**：

- 用户在校对页填写的那段分类说明，在详情页以「分类理由」为标签显示。
- 页面**不出现**标为「研究理由」且有内容的字段。
- 研究方法逐项可读展示（每行一项或 Chip），页面文本**不含** `["` 或 `"]` 形式的 JSON 片段。

**修复前对照**：同一段分类理由被标成「研究理由 (rationale)」，用户误以为系统凭空生成；研究方法以 `["particle swarm optimization crystal-structure search", ...]` 原始 JSON 呈现。

**说明**：研究方法在库中本就是英文术语列表，不存在中译英丢失（已核实草稿与库两端一致）。用户感知的「提交中文、审核英文」源于校对页按行排版、详情页塞 JSON 的形态差异。

## 场景 6：结构预览与空态（US3，FR-009，SC-005）

**预期**：paper 4 无结构数据，显示明确空态说明，不出现破损的预览容器或报错。

**当前限制**：`structure_models` 全库 0 行，**有结构数据的渲染分支无法在 dev 环境人工验收**，只能由单元测试注入数据覆盖。待有真实结构数据后再核验该分支。

```bash
docker compose -f /home/mayuan/work/SC-Wiki-docker/dev.yaml exec -T mysql \
  sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" scwiki -N -e "SELECT COUNT(*) FROM structure_models;" 2>/dev/null'
```

预期输出 `0`，确认当前只能验空态。

## 场景 7：只读性与无回归（US3，FR-010/FR-011，SC-005/SC-006）

1. 在详情页尝试点击任意文本区域。

**预期**：无可编辑输入框、无「添加物性」与「删除」按钮；页面不依赖整体 `disabled` 伪装只读。

2. 检查「返回上传列表」与「我的论文」入口。

**预期**：两个入口仍可用，行为与 #56 一致；刷新 `/papers/4` 仍得到同一篇论文。

3. 匿名访问 `/papers/4`（`pending`）。

**预期**：仍显示无权查看提示，不渲染任何论文字段。

## 验收对照

| 场景 | 覆盖 |
|---|---|
| 1 | FR-001、FR-005、SC-001 |
| 2 | FR-002、SC-002 |
| 3 | FR-003、SC-002 |
| 4 | FR-004、SC-003 |
| 5 | FR-006、FR-007、FR-008、SC-003、SC-004 |
| 6 | FR-009、SC-005 |
| 7 | FR-010、FR-011、SC-005、SC-006 |
