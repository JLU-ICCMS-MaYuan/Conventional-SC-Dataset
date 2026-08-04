# CONTCAR/PDOS Tc 估算

## 功能说明

解析 VASP CONTCAR 和 PDOS 文件，提取氢子晶格、键长分布与费米能级附近态密度，并根据固定经验参数返回 Tc 估算值。

## 当前行为

- 使用 pymatgen 解析 CONTCAR。
- 统计氢原子、H-H 键长及键长分布。
- 读取 `PDOS_H.dat` 和最多四个金属 PDOS 值，计算态密度与耦合特征。
- 返回 Tc 估算及中间解释特征。
- 缺少必要文件、文件无法解析、列数不足或关键数值为零时返回 400 错误。

## 工作流程

前端 `/tc-pre` 上传 CONTCAR 和 PDOS 文件；后端解析结构；识别氢和金属 PDOS；计算耦合、频率及 Tc；将数值和解释特征返回页面。

## 约束

- 必须包含可解析的 CONTCAR 和 `PDOS_H.dat`。
- 金属 PDOS 数量会补齐或截断为四个值。
- NumPy 被限制为 `<2.0`，以兼容 pymatgen。
- 当前测试主要隔离了材料科学依赖，不能证明真实文件端到端效果或模型科学有效性。

## 代码与测试

- API：`backend/api/tc_predict.py`
- 页面：`frontend/src/pages/TcPredictionPage.tsx`
- 依赖：`requirements.txt`
- 测试：`tests/06_ai_assisted_tc_estimation/test_tc_predict.py`

## 相关变更记录

当前未发现可链接的已完成 Feature 或 Debug 记录。

## 已知问题

- 经验公式的适用范围、校准数据和不确定度没有在当前实现中形成可验证的模型说明。
