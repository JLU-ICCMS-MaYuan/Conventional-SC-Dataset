# 快速验收：MaterialState 模块化物性与动态表单

## 前置条件

- 使用包含 #90 Expand 与 Copy 阶段的隔离 MySQL。
- Python、Go 和前端读取同一套已发布定义。
- 准备上传用户、管理员和超级管理员测试账号。

## 场景一：按需挂载模块

为论文 A 的 `LaH10 @ 170 GPa` 添加 `superconductive_properties` 和 `electronic_properties`，
分别录入 Tc 与 DOS，不添加另外两个模块。

预期：保存、刷新和详情只出现两个模块；新增动力学模块后原记录键、定义版本和值不变；删除空模块
不删除其他模块记录。

## 场景二：两组预测 Tc 不错配

```text
calc-a: mu_star=0.10, lambda=2.2, omega_log=1100 K, predicted Tc=250 K
calc-b: mu_star=0.15, lambda=2.2, omega_log=1100 K, predicted Tc=220 K
```

两组可以使用相同软件和网格，但必须具有不同 `condition_key`。保存草稿、提交、管理端读取并再次
保存。

预期：两组关系始终不交换或合并；尝试把两个互斥 mu_star 放入同一 Conditions 时返回
`condition_group_rule_failed`。

## 场景三：预测与测量 Tc 动态字段

1. 添加 `predicted_tc + allen_dynes`，确认显示计算 Conditions 和该方法允许字段。
2. 添加 `measured_tc + resistivity`，确认显示实验 Conditions、样品及电阻判据字段。
3. 让预测 Tc 引用实验 Conditions，让测量 Tc 引用计算 Conditions。
4. 把已填写方法扩展字段的记录切换到另一方法。

预期：1、2 成功；3 被前后端拒绝；4 要求明确清理、转换或取消，隐藏字段不会继续进入提交数据。

## 场景四：定义 v1/v2 并存

超级管理员发布 `superconductive_properties.predicted_tc` v1，创建记录 A；再发布增加可选字段的 v2，
创建记录 B。

预期：A 继续绑定 v1，B 默认绑定 v2；直接修改 v1 失败；停用 v1 后 A 仍可读取但不能用 v1 新建；
未知版本和校验和错误被拒绝。显式升级 A 时先预览，验证通过后才写入 v2 和转换后的 `payload`。

## 场景五：论文内材料隔离

论文 A、B 分别创建 LaH10 和 170 GPa 状态。两份 `Superconductor` 主键必须不同。修改论文 A 的
展示名称并删除其草稿。

预期：论文 B 的材料、状态、物性和 Conditions 不变；搜索 LaH10 仍能按规范化字段找到两篇论文。

## 场景六：Evidence 与跨模块单一事实

为 Tc、mu_star 和 DOS 分别关联各自原文 Evidence。尝试将同一 DOS 复制到两个模块后独立修改。

预期：新批准记录都能追溯到同 revision Evidence；跨 revision Evidence 被拒绝；同一事实只保留一个
权威记录，其他模块只能引用或展示它。

## 场景七：分阶段迁移

在旧 Schema fixture 上依次执行 Expand、Copy、Reconcile、Read switch、Write switch、Observe 和
Contract。

逐项检查：

- 共享材料按论文 revision 拆分且关系正确；
- 理论/实验 Tc 映射到正确记录类型；
- 普通物性映射到正确模块和定义 v1；
- lambda、omega_log、mu_star 成为独立记录并保持 Conditions；
- Evidence 不丢失、不伪造；
- 重复执行 Copy 不产生重复记录；
- 每个阶段失败后可从最近稳定阶段恢复；
- Contract 前旧读取可用，Contract 后无旧写入依赖。

## 场景八：详情、搜索和图表

批准测试论文，依次检查上传只读态、管理员编辑、论文详情、材料搜索和 Tc 图表。

预期：各入口的模块、记录数、定义版本、值和 Conditions 一致；搜索同时返回论文 A、B 的 LaH10；
预测/测量 Tc、方法和代表点与迁移前一致；查询计划使用目标索引。

## 自动验证

```bash
bash scripts/run-tests.sh backend
bash scripts/run-tests.sh go
bash scripts/run-tests.sh frontend
cd frontend && npm run build
git diff --check
```

另需运行 #90 的隔离 MySQL 分阶段迁移与恢复专项测试。
