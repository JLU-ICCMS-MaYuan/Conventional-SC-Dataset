# 快速验收：统一材料状态的超导物性记录

## 目的

本 Quickstart 用一组固定数据验证三件事：

1. 所有物性在一个平级列表中出现；
2. 平级记录仍保留计算/实验 Context 对应关系；
3. Tc 专用约束、Evidence、详情和图表行为不回退；
4. 结构引用可空，已有结构候选需要用户确认后才能复用。

## 前置条件

- Alembic 已升级到包含 #90 的目标 revision。
- Python、Go、前端和 MySQL 使用同一测试数据库契约。
- 使用具备上传和管理权限的测试账号。
- 测试论文尚未批准，或允许按 #76 进入升版重审。
- 测试库准备一条已批准论文当前 revision 的 `CanonicalStructureIdentity`，并保留至少一个公开来源
  `StructureModel`；另准备一条待审核来源用于验证不可见。

## 场景一：一个列表表达全部物性

准备 `LaH10 @ 170 GPa` 材料状态，输入以下平级记录：

| property_code | 值 | Context |
| --- | --- | --- |
| `tc` | 250 K | `calc-a` |
| `lambda_ep` | 2.2 | `calc-a` |
| `omega_log` | 1100 K | `calc-a` |
| `mu_star` | 0.10 | `calc-a` |
| `dos_fermi` | 0.8 states/eV | 无 |
| `hc2` | 120 T | `exp-a` |
| `superconducting_gap` | 40 meV | `exp-a` |
| `energy_above_hull` | 0 eV/atom | 无 |

预期：

- 页面只有一个物性列表，共 8 条记录；
- 页面和响应中不存在 `TcRelated`、`OtherProperties`、`UncontextualizedProperties`；
- λ、ωlog、μ* 不是 Tc 的子字段；
- 无 Context 的 DOS 和 energy above hull 正常保存。

## 场景二：验证两组 μ*—Tc 不错配

再增加：

```text
calc-a: μ*=0.10, Tc=250 K
calc-b: μ*=0.15, Tc=220 K
```

保存草稿、刷新、提交、从管理端读取并再次保存。

预期：

- `calc-a` 始终关联 0.10 和 250 K；
- `calc-b` 始终关联 0.15 和 220 K；
- 后端没有按物性名称或数值把两个 Context 合并；
- 用户没有输入或编辑数据库 `calculation_context_id`。

将 `calc-b` 的一条记录改成与其他 `calc-b` 记录不同的 Context 详情后再次提交。

预期：返回 `conflicting_context`，错误路径指向具体物性记录。

## 场景三：验证实验/理论 Tc

分别尝试：

1. `tc_method=experimental` + `context.kind=experimental`；
2. `tc_method=experimental` + `context.kind=calculation`；
3. `tc_method=allen_dynes` + `context.kind=calculation`；
4. `tc_method=allen_dynes` + `context.kind=experimental`。

预期：1、3 成功，2、4 在应用层被拒绝；绕过 API 的非法数据库写入也被约束拒绝。

同一材料状态和 `tc_method=allen_dynes` 提交两条 `is_representative=true`。

预期：保存失败，不产生部分数据。

## 场景四：验证旧契约转换

加载同时包含以下字段的旧 fixture：

```text
material_states[].tc_results[]
material_states[].calculation_contexts[]
material_states[].experimental_contexts[]
material_states[].properties[]
paper.key_properties[]
```

预期：

- 读取后只得到 `material_states[].superconductor_properties[]`；
- Context 中非空 λ、ωlog、μ* 被转换为平级记录；
- 已经存在对应通用物性行时不生成重复参数；
- 再次保存只输出新契约。

## 场景五：验证持久化与 Evidence

提交场景一的数据，并核对：

- Tc 进入专用 Tc 实体；
- 其余 7 条进入通用物性实体；
- `calc-a` 只建立一个计算 Context，`exp-a` 只建立一个实验 Context；
- λ、ωlog、μ* 不再写入 Context 参数列；
- 每条带 Evidence 的记录建立对应 Evidence 连接；
- 所有实体的论文、revision 和材料状态一致。

故意让最后一条 Evidence 跨 revision，预期整个事务回滚，残留新科学记录数为 0。

## 场景六：验证详情和下游

批准测试论文后依次检查上传只读态、管理员编辑页、论文详情、探索页和社区页。

预期：

- 五个入口对场景一均识别 8 条记录；
- 名称、值、单位和 Context 对应关系一致；
- Tc、Hc2 和超导能隙都被称为超导物性，不显示“其他普通物性”分组；
- Tc 搜索结果和社区图表中的代表 Tc 仍为 250 K。

## 场景七：验证迁移与回滚

在隔离 MySQL 中准备两个旧计算 Context，分别填充部分 λ、ωlog、μ*，然后执行：

1. upgrade 到 #90 revision；
2. 核对三个旧列的非空计数与新物性代码计数；
3. 检查缺失 Evidence 报告；
4. downgrade；
5. 再次 upgrade。

预期：

- 各参数计数逐项相等；
- 重复 upgrade 不生成重复记录；
- downgrade 恢复旧参数值，不删除迁移前已有的通用物性；
- 没有 Evidence 被自动伪造。

## 场景八：验证结构候选、确认与空引用

准备一个 `LaH10` 物性录入状态，填写压强 `170.000 GPa`、空间群 `Fm-3m/225`，并在计算 Context
填写 `geometry_method=relax`、`calculation_code=Quantum ESPRESSO`、`exchange_correlation=PBE`、
`nuclear_treatment=harmonic`。调用结构候选接口。

预期：

- 只返回已批准论文当前 revision 的候选；待审核来源不出现；
- 候选化学式标准化相等、压强差不超过 `0.01 GPa`，且已填写方法字段匹配；
- 结果包含 `structure_ref`、压强差、空间群、方法摘要和来源论文，并按压强差升序排列；
- 查询本身不修改物性草稿。

执行以下四种操作：

1. 只有一个候选时点击“关联此结构”；
2. 存在多个候选时不选择任何候选；
3. 候选压强距离相同；
4. 点击“跳过”或清空已有结构引用。

预期：

- 操作 1 后，Tc、λ、μ* 三条记录可以保存相同的不透明 `structure_ref`，Context 结构引用与记录一致；
- 操作 2、3、4 均保存 `structure_ref=null`，不会自动选择、创建或复制结构；
- 已有非空引用不会因再次查询而被覆盖；
- 来源 `StructureModel` 的 Evidence 仍只属于来源论文，不会复制到当前物性。

将候选结构所属论文升版或删除前，尝试删除其最后一个公开来源。

预期：系统阻止产生无来源的有效规范身份，或明确标记身份不可用并报告受影响的物性引用。

## 自动化验证命令

```bash
bash scripts/run-tests.sh backend
bash scripts/run-tests.sh go
bash scripts/run-tests.sh frontend
cd frontend && npm run build
```

另需执行 #90 的隔离 MySQL `upgrade → downgrade → upgrade` 验证和 `git diff --check`。
