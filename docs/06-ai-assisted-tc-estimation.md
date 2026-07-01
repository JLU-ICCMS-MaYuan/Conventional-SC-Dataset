# VI. AI-Assisted Estimation of Superconducting Transition Temperatures

## Definition

AI-Assisted Estimation of Superconducting Transition Temperatures 指 SC-Wiki 中面向含氢体系的 Tc 预测实验工具。它接收结构文件和 PDOS 文件，抽取 H 子晶格几何特征和费米能附近态密度特征，使用经验公式估算超导临界温度。

## Current Status

当前状态是已落地但实验性。页面 `/tc-pre` 和接口 `POST /api/tc-predict/` 已存在。该模块不写入数据库，不进入论文审核，不进入首页图表，不保存预测历史，也不与用户账户形成持久记录。

## Input

当前输入包括：

- 一个 VASP 结构文件，页面文案中通常称为 POSCAR 或 CONTCAR。
- 一组 PDOS 文件。
- 文件组中必须能识别出 H 的 PDOS 文件，例如 `PDOS_H.dat`。

后端依赖 `numpy` 和 `pymatgen` 解析输入。依赖采用懒加载，缺少这些库时主要影响预测接口，不应阻止主站其他页面启动。

## Calculation Flow

核心计算流程包括：

1. 解析结构文件。
2. 提取 H 子晶格。
3. 计算 H-H 短键分布。
4. 读取每个 PDOS 文件在费米能附近的 DOS 值。
5. 根据文件名区分 H PDOS 和金属 PDOS。
6. 对 H 原子数、短键数和 DOS 比例做归一化。
7. 计算经验耦合特征 `couple`。
8. 计算核心特征 `f2`。
9. 通过线性关系输出 `predicted_tc`。

旧说明中明确给出的最终形式是：

`Tc = 16370.6 * f2 + 24.7`

这里的 Tc 不是严格从 BCS 或 Eliashberg 理论直接推导出来的闭式理论结果，而是结构特征和 DOS 特征上的经验估计。

## Output

接口返回：

- `predicted_tc`
- `f2_value`
- `dos_h_ratio`
- `dos_h_atom_bond`
- `bonds_mean`
- `bonds_var`

`predicted_tc` 面向终端用户，其余字段用于解释和调试。例如可以判断预测偏低是来自 H DOS 占比不足、键长窗口未命中，还是几何分布特征较弱。

## Code and API Evidence

页面和脚本：

- `/tc-pre`
- `frontend/templates/tc_pre.html`
- `frontend/static/js/tc_pre.js`

后端：

- `backend/api/tc_predict.py`
- `backend/schemas.py` 中的 Tc 预测响应模型

接口：

- `POST /api/tc-predict/`

## Boundary

该功能与数据上传功能共享“用户上传文件”这个交互形式，但业务闭环完全不同。数据上传会产生论文、超导记录或结构记录；Tc 预测只进行即时计算并返回结果。

该功能也不等于已经建立了预测材料数据库。当前没有 `tc_prediction_jobs`、`predicted_material_records` 或类似表。没有历史记录、模型版本记录、输入文件追踪、用户预测记录或预测结果审核。

## Limitations

当前模型明显偏向含氢体系。结构中没有 H 原子、没有 H-H 短键、PDOS 文件无法解析、缺少 `PDOS_H`、H 与金属 DOS 总和为 0 等情况都会失败。文件命名对结果有实际影响，因为 H 和金属 PDOS 的区分依赖文件名。

## Future Direction

最合理的演进不是直接把预测结果塞进 `papers` 表，而是先建立独立预测任务表，记录用户、输入摘要、模型版本、预测结果和失败信息。之后再考虑从元素体系页或论文详情页发起预测，并让高质量预测结果经过审核后进入图表或候选材料库。
