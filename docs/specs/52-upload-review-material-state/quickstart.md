# 快速验证：上传校对页布局重构与材料状态卡片完善

**Feature**：[spec.md](spec.md) ／ **日期**：2026-08-26

## 前置条件

- 后端依赖已安装（含新增 spglib）：`pip install -r requirements.txt`
- 前端依赖已安装：`cd frontend && npm install`
- 本地 MySQL 已执行 `alembic upgrade head`（含 `20260826_0014`）；Redis 可用
- 服务已启动：Python API/Worker、goserver、前端（localhost:8080）

## 自动化验证

```bash
# 后端
python -m pytest backend/tests/test_upload_jobs.py backend/tests/test_scientific_drafts.py backend/tests/test_classification_catalog.py -q
# 前端
cd frontend && npm run test:upload-ui
```

预期：全部通过；新增用例覆盖元素数锁定/宽松解析、空间群全表映射、提交逐条 CalculationContext、research_materials 汇总、超导类型条件化渲染。

## 端到端场景

### 场景 1：布局与折叠（US1）

1. 上传一篇含多个材料状态的论文，等待进入「第 5/5 步：等待用户校对」。
2. 预期：页面无「研究材料」输入框；「关键词」左、「研究方法」右、初始等高；材料状态卡片数 >2 时仅首张展开。
3. 点击「全部折叠」→ 全部仅剩标题栏；点击某卡片标题 → 仅该卡展开；点击「全部展开」→ 全部展开。

### 场景 2：元素种类数（US2）

1. 材料化学式填 `LaHx (x = 1–12) 150 GPa`，停止编辑 5 秒自动保存。
2. 预期：元素种类数显示 2。
3. 手动改为 3 → 保存 → 刷新页面 → 仍为 3（不被重算覆盖）。
4. 解锁场景：把化学式改为 `CeCu2Si2` 且未手动改过数字 → 保存后显示 3。

### 场景 3：超导类型与 Tc（US3）

1. 某材料状态超导类型选「常规 (BCS)」→ 点击「添加 Tc」。
2. 预期：条目含 λ、ωlog、μ\*、Tc 数值、方法下拉（McMillan / Allen-Dynes-McMillan / isotropic Migdal-Eliashberg / anisotropic Migdal-Eliashberg / SCDFT / 其他）。
3. 方法选「其他」→ 出现自定义文本框，填 `my-method` → 保存刷新后仍在。
4. 类型切为「非常规」→ 再「添加 Tc」→ 新条目仅 Tc 数值框；原常规条目不消失。
5. 提交 → 管理员审核页：该状态显示超导类型；每条 theoretical Tc 关联各自的 λ/ωlog/μ\*。

### 场景 4：空间群（US4）

1. 空间群符号输入 `Fm-3m` 并选中 → 群号自动 225。
2. 输入 `P6_3/mmc` → 194；输入非标准 `Xyz` → 可保存、群号留空、无阻断报错。

### 场景 5：文案与顺序（US5）

1. 页面显示「压强 (GPa)」，无「压力」标签。
2. 未选结构家族时主结构家族禁用并显示说明；选择两个结构家族后可指定唯一主项。
3. 结构附件模块在卡片最底端（Tc 与其他普通物性之下）。

### 场景 6：energy above hull（US6）

1. 上传明确声明 thermodynamically stable 的论文 → 对应材料状态普通物性含 energy above hull = 0（eV/atom）。
2. 手动场景：点击「＋ energy above hull」→ 生成空值条目；再次点击不重复添加。

### 场景 7：提交回归

1. 非综述论文删除全部材料化学式后提交 → 被拒并提示 `research_material_required`。
2. 正常提交 → papers 表 `research_materials` 为材料状态化学式汇总。
