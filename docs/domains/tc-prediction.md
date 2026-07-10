# Tc 估算

## 职责

`/tc-pre` 页面和 `/api/tc-predict/` 提供实验性即时估算：从 VASP CONTCAR 和 PDOS
文件提取特征并返回预测值和中间特征。

## 当前行为与约束

- 输入必须包含可解析的 CONTCAR、氢子晶格和 `PDOS_H` 数据。
- 计算使用 H-H 键长分布、氢态密度和最多四个金属 PDOS 值。
- 运行依赖 `numpy` 与 `pymatgen`；依赖缺失时 API 返回 503。
- 结果直接响应，不保存预测历史、模型版本或审核记录。

## 证据

- `frontend/src/App.tsx`
- `backend/api/tc_predict.py`
- `tests/06_ai_assisted_tc_estimation/`

## 已知缺口

- 任务历史、模型版本和入库审核均不是当前能力；相关需求必须以 `type:idea` 或
  `type:feature` 进入 GitHub Issues。
