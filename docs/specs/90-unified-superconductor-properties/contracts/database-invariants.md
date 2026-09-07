# 数据库不变量：模块化物性与定义版本

## 归属

1. `ChemicalSystem`、`Superconductor`、`MaterialState`、模块、记录、Conditions、结构和 Evidence
   必须属于同一 `paper_id + paper_revision`。
2. 同名或同组成材料可以分别属于不同论文；任何子实体不得跨论文引用材料主键。
3. 科学子实体服从论文 revision 的整体审核，不增加独立审核状态。

## 模块与记录

1. 一个材料状态的 `module_code` 最多挂载一个模块实例。
2. 每条记录只属于一个权威模块；跨模块展示不得复制记录。
3. 每条记录必须绑定存在的 `definition_key + definition_version`。
4. 固定核心字段和 `payload_json` 不能表达同一事实的两个可写值。
5. 范围上下界必须成对出现且下界不大于上界；不确定度不得为负。
6. 原始名称、值和单位不得被规范值覆盖。

## Conditions

1. 一个 Conditions 只属于一个材料状态和论文 revision。
2. 一个 `condition_key` 表示一次确定的运行或测量；决定性输入不同必须使用不同键。
3. 预测 Tc 必须关联计算 Conditions，测量 Tc 必须关联实验 Conditions。
4. 同一 Conditions 下的全部记录必须通过绑定定义的 `group_rules`。
5. Conditions 不保存 lambda、omega_log、mu_star、Tc 或其他物性权威值。

## Tc

1. `record_type=predicted_tc|measured_tc` 时 `property_code` 必须为 `tc`。
2. 预测/测量记录类型、方法和 Conditions 类型必须一致。
3. Tc 规范值、范围及不确定度必须非负，规范单位为 `K`。
4. 同一论文 revision、材料状态、Tc 记录类型和方法最多一条代表记录。
5. 非 Tc 记录的 Tc 专用代表标记必须为空。

## 定义版本

1. `definition_key + version` 唯一，版本从 1 单调递增。
2. `published` 定义不可修改内容；修订只能产生新版本。
3. `retired` 定义允许历史读取，不允许新建记录。
4. 定义的 Schema、UI Schema 和组级规则必须与校验和一致。
5. 定义只包含受支持的声明式关键字，不得执行脚本。
6. 历史记录读取不得自动修改绑定版本。

## Evidence 与审核

1. 新建或编辑后准备批准的每条记录至少关联一个同 revision Evidence。
2. 迁移不得把 Tc Evidence 自动复制给相关参数，也不得伪造缺失 Evidence。
3. Evidence 连接可以级联删除，但不能反向删除 Evidence 正文或记录。

## 迁移

1. 旧 ID 到新 ID 的映射必须可追溯且包含论文 revision。
2. 复制与对账完成前不得关闭旧读取；新写入切换后不得继续双写。
3. 旧表退役必须是独立阶段，并以真实 MySQL 验证恢复路径。
4. 迁移异常必须逐条报告；记录数相等不能替代核心值和关联一致性核验。
