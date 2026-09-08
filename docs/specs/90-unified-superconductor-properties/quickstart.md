# 快速验收：MaterialState 模块化物性与动态表单

## 实施验证结果

本地已完成 Python、Go、前端模块化契约回归，并在隔离真实 MySQL 完成 Expand、Copy、Reconcile、
Final sync、Read/Write switch、Observe、Contract 和恢复验证；结果见 [validation.md](validation.md)。
部署到具体数据库时仍必须按阶段门禁执行，不能用仓库验收替代部署确认：

```bash
alembic upgrade issue90_copy_v1
DATABASE_URL="$DATABASE_URL" python3 -m backend.scripts.migrate_issue90_properties --dry-run
DATABASE_URL="$DATABASE_URL" python3 -m backend.scripts.migrate_issue90_properties
```

迁移脚本输出 `errors=[]` 且重复运行 `copied=0` 后，才可进入读取切换和观察阶段。

## 前置条件

- 使用包含 #90 Expand 与 Copy 阶段的隔离 MySQL。
- Python、Go 和前端读取同一套已发布定义。
- 准备上传用户、管理员和超级管理员测试账号。

## 场景一：按需挂载模块

为论文 A 的 `LaH10 @ 170 GPa` 添加 `superconductive_properties` 和 `electronic_properties`，
分别录入 Tc 与 DOS，不添加另外两个模块。

预期：保存、刷新和详情只出现两个模块；新增动力学模块后原记录键、定义版本和值不变；空模块可以
删除；删除含记录模块时必须先显式处理记录，不能静默级联删除。

## 场景二：每条预测 Tc 自带完整资料

以下为归属测试示例，不是论文数据或公式验算：

```text
Tc-A：250 K；Allen-Dynes；自己的 Conditions；λ=2.2，ωlog=1100 K，μ*=0.10
Tc-B：220 K；Allen-Dynes；自己的 Conditions；λ=2.2，ωlog=1100 K，μ*=0.15
```

两条记录分别填写软件、k/q 网格及各自展宽与单位。直接保存草稿、提交、管理端读取并再次保存，
不需要先创建 Conditions 或独立参数记录。

预期：两条记录资料不交换或合并；修改 A 的展宽、λ 和 Tc 后，B 完全不变。
复制 A 得到 C，修改 C 后 A 不变；保留内容完全相同的 D，系统也不自动合并。
参数错误类型、无单位或方法不允许的字段按定义被拒绝；论文未报告的可选参数可留缺失。

## 场景三：预测与测量 Tc 动态字段

1. 添加 `predicted_tc + allen_dynes`，确认显示计算 Conditions 和该方法允许字段。
2. 添加 `measured_tc + resistivity`，确认显示实验 Conditions、样品及电阻判据字段。
3. 给预测 Tc 填入实验条件对象，给测量 Tc 填入计算条件对象。
4. 把已填写方法扩展字段的记录切换到另一方法。

预期：1、2 成功；3 被前后端拒绝；4 要求明确清理、转换或取消，隐藏字段不会继续进入提交数据。

## 场景四：定义 v1/v2 并存

超级管理员发布 `record.superconductive_properties.predicted_tc.allen_dynes` v1，创建记录 A；再发布增加
可选字段的 v2，创建记录 B。

预期：A 继续绑定 v1，B 默认绑定 v2；直接修改 v1 失败；停用 v1 后 A 仍可读取但不能用 v1 新建；
未知版本和校验和错误被拒绝。显式升级 A 时先预览，验证通过后才写入 v2 和转换后的 `payload`。

记录升级返回 `upgrade_event_id` 后立即执行回滚，预期恢复 v1 和升级前 `payload` 并新增反向审计事件。
随后再次升级、修改记录，再尝试使用旧事件回滚，预期返回 `definition_rollback_stale` 且数据不变。

## 场景五：论文内材料隔离

论文 A、B 分别创建 LaH10 和 170 GPa 状态。两份 `Superconductor` 主键必须不同。修改论文 A 的
展示名称并删除其草稿。

预期：论文 B 的材料、状态、物性和 Conditions 不变；搜索 LaH10 仍能按规范化字段找到两篇论文。

## 场景六：Evidence 与模块所有权

为 Tc、其内部 mu_star 字段和独立 DOS 分别填写各自真实原文 Evidence，再尝试直接删除仍包含 DOS 的电子性质模块。

预期：新批准记录都能追溯到同 revision Evidence；跨 revision Evidence 被拒绝；非空模块删除被阻止，
显式删除 DOS 后才可删除模块，不创建跨模块引用或副本。

## 场景七：分阶段迁移

在旧 Schema fixture 上依次执行 Expand、Copy、Reconcile，随后阻止科学数据写入并完成最终增量 Copy
与 Reconcile，再执行 Read switch、Write switch、解除停写、Observe 和 Contract。

逐项检查：

- 共享材料在影子表按论文 revision 拆分且关系正确，旧全局唯一键不阻断第二篇同名材料复制；
- 理论/实验 Tc 映射到正确记录类型；
- 普通物性映射到正确模块和定义 v1；
- lambda、omega_log、mu_star 和条件按旧引用复制到每条 Tc 内，以源字段到目标记录字段逐项对账；
- 无引用条件、参数冲突和缺失来源进入异常清单，未明确处理前阻断切换；不得把 Tc 证据自动当成参数证据；
- Evidence 不丢失、不伪造；
- 重复执行 Copy 不产生重复记录；
- 停写并排空在途事务后，最终复制包含新增、修改、升版和删除；对账完成前不切换读取，读取验收前不切写；
- 材料表更名时暂停科学读取并返回维护错误；旧外键按映射显式重建，不依赖表更名自动改变引用对象；
- Read switch 失败恢复旧读取并解除停写，期间没有已提交数据丢失或暂时不可见；
- 每个阶段失败后可从最近稳定阶段恢复；
- 切写前保留旧读取恢复能力，切写后按目标模型恢复；Contract 后无旧写入依赖。

解除停写后再提交一条新记录，然后模拟目标服务故障：恢复必须使用目标 Schema 检查点及后续事务日志，
新提交记录仍然存在。此时不允许直接切回过期旧表。具体步骤以[迁移契约](contracts/persistence-mapping.md#分阶段迁移)为准。

## 场景八：详情、搜索和图表

批准测试论文，依次检查上传只读态、管理员编辑、论文详情、材料搜索和 Tc 图表。

预期：各入口的模块、记录数、定义版本、值和 Conditions 一致；搜索同时返回论文 A、B 的 LaH10；
预测/测量 Tc、方法和代表点与迁移前一致；查询计划使用目标索引。

## 场景九：自定义性质保留与管理员直接提升

使用贡献者 A、普通管理员 B、另一贡献者 C 三个账号，全程不使用超级管理员账号：

1. A 在已注册模块中选择自定义性质，分别录入数值、范围、文本和布尔性质，填写原名、单位及各自证据，
   保存草稿、重新打开并提交。
2. B 批准论文并选择暂不提升。详情必须保留四种性质，不能因为全站未收录而遗漏。
3. B 在已批准记录上选择提升，确认名称、代码、类型、单位和模块后直接发布；不产生待超级管理员批准状态。
4. C 刷新对应模块定义选择器，选择 B 发布的新性质并保存一条新记录。
5. A 直接调用提升接口必须得到 403；B 用同 operation_id 重试得到同一结果，另一次重复代码请求得到 409。
6. 提升时修改来源 revision、重复提升同一来源、使用保留代码分别触发稳定错误；已批准源记录不受失败影响。
7. 比较提升前后源记录的名称、值、单位、Evidence 与定义绑定，必须完全相同；升版或删除来源后，新定义仍存在。

审计应包含 B 的身份、操作时间、来源快照及目标定义版本，公开记录和定义选择器不暴露审计信息。

## 场景十：预留分组新增字段

在 Tc-A 的参数分组添加一个尚未收录的字段，填写名称、类型、单位、值和 Evidence。
保存、提交、随论文批准，重新打开详情并导出。

预期：字段始终留在 A 的参数分组，Tc-B 不增加该字段；审核保留不要求发布全站 Schema。
绕过前端提交未预留路径、重复 field_key、覆盖系统键或非法类型时后端拒绝。升级定义版本不能静默丢弃该字段。

## 场景十一：完整 MaterialState 导出

从已批准论文导出一个包含两条预测 Tc、一条测量 Tc、其他物性、结构文件和字段级证据的 MaterialState。
断开网络和数据库，仅打开下载的数据包。

预期：包内能读取材料、压力、结构内容、全部模块、每条 Tc 的结果、方法、条件、参数和各自来源；
能按包内定义版本解释新增字段，不需外取关系表或在线定义。导出期间修改 revision 得到明确重试或冲突；
公开用户不能导出未批准数据或管理员审计信息。已有结构文件缺失时返回明确错误，不输出貌似完整的包。

## 自动验证

```bash
bash scripts/run-tests.sh backend
bash scripts/run-tests.sh go
cd frontend && npm run test:upload-ui
cd frontend && npm run build
PYTHONPATH=. python -m compileall -q backend alembic
git diff --check
```

每次部署到新的具体 MySQL 环境前，均需先运行 #90 的隔离 MySQL 分阶段迁移与恢复专项测试；
已完成环境及结果记录在 [validation.md](validation.md)，此要求不是尚未实施的功能任务。
