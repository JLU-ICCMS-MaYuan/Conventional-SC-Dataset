# Tc 预测模块说明迁移提示

Tc 预测模块的业务说明已经合并进入新的文档体系，请优先阅读：

- [图表展示与 Tc 预测实验](/home/mayuan/code/Conventional-SC-Dataset/docs/business-visualization-and-tc-predict.md)
- [业务总览](/home/mayuan/code/Conventional-SC-Dataset/docs/business-overview.md)

本文件不再维护完整正文，避免与新文档重复或产生版本漂移。

1. 尝试用 `numpy.loadtxt` 读取。
2. 如果失败，再尝试 `numpy.genfromtxt`。
3. 要求至少两列。
4. 第一列视为能量，最后一列视为 DOS。
5. 找到最接近 `0 eV` 的能量点。
6. 取该点最后一列 DOS 值作为该文件特征值。

#### 5.4.1 为什么找最接近 0 eV 的点

```python
idx = int(np.argmin(np.abs(energies)))
return float(dos_values[idx])
```

含义：

- 这里默认费米能已经对齐到 `0 eV`。
- 所以最接近 0 的那一行代表费米能附近的态密度。

物理意义：

- 超导性质通常与费米能附近的电子态密度密切相关。
- 当前模型并没有对整个 PDOS 曲线做积分或形状分析，而是取费米能局部值作为简化特征。

---

### 5.5 第四步：区分 H 和金属的 PDOS 值

在主入口函数中：

```python
for upload in pdos_files:
    content = await upload.read()
    value = _read_pdos_value(content)
    filename = (upload.filename or "").upper()
    if "PDOS_H" in filename or filename.endswith("H.DAT"):
        if h_value is None:
            h_value = value
    else:
        metal_values.append(value)
```

含义：

- 通过文件名识别 `PDOS_H.dat`
- 第一个匹配到的 H 文件作为 `h_value`
- 其他文件都视为金属贡献

这里的业务假设很强：

- 输入文件命名必须规范
- H 的 PDOS 只能靠文件名识别
- 非 H 文件被统一看作“金属态密度输入”

如果文件名不规范，模型可能会把文件归错类。

---

### 5.6 第五步：补齐或截断金属 PDOS 数量

```python
metal_values = (metal_values + [0.0] * MAX_METAL_FILES)[:MAX_METAL_FILES]
```

含义：

- 最多保留 4 个金属 PDOS 值
- 不足 4 个用 0 补齐

物理意义：

- 当前模型的经验输入维度被人为固定在“1 个 H + 最多 4 个金属分量”的模式。
- 它没有显式保留元素身份，也不关心这些金属 PDOS 分别来自哪种元素，只关心它们的和。

---

### 5.7 第六步：键长分布归一化

函数：

```python
def _normalize_bonds(bonds: List[float], atoms: int) -> Dict[float, float]:
```

逻辑：

1. 每条 H-H 键长先向下截断到 `0.001 Å` 精度。
2. 按键长分桶统计数量。
3. 每个桶的计数再除以 H 原子总数。

示意：

如果有：

- `1.0012, 1.0018, 1.1204`

则分桶后可能变成：

- `1.001: count`
- `1.120: count`

再除以 `atoms` 得到每原子的归一化频次。

物理意义：

- 这是把原始离散键长列表转成一个简化的“键长分布”。
- 当前不是按“总键数”归一，而是按“H 原子数”归一，因此后续 `sum(bond_distribution.values())` 表示的是“每个 H 原子平均对应的短键计数规模”。

---

### 5.8 第七步：耦合项 `couple`

函数：

```python
def _calculate_coupling(bond_distribution: Dict[float, float], dos_h_atom_bond: float) -> float:
```

公式：

```python
couple += length * frac * dos_h_atom_bond * weight
```

其中：

- `length`：某个键长分桶的代表值
- `frac`：该分桶归一化频率
- `dos_h_atom_bond`：后面定义的 H 原子-键归一化 DOS 因子
- `weight`：若键长位于 `0.98-1.28 Å` 区间则为 1，否则为 0

因此可写成：

`couple = Σ[length * frac * dos_h_atom_bond * I(0.98 <= length <= 1.28)]`

物理意义：

- 这不是标准 Eliashberg 方程中的严格耦合常数，而是一个经验构造的代理特征。
- 模型强调两件事：
  - 只有处于特定窗口的 H-H 键长才贡献有效耦合
  - H 相关态密度越大，这类键长分布带来的耦合作用越强

也就是说，`couple` 是一个“结构窗口筛选后的 H 子晶格几何特征”和“H 态密度归一化特征”的组合量。

---

### 5.9 第八步：中间物理量定义

主入口中的核心中间量如下。

#### 5.9.1 `total_metal`

```python
total_metal = sum(metal_values)
```

含义：

- 所有非 H PDOS 特征值的总和。

物理意义：

- 用来表示费米能附近非氢部分的总态密度贡献。

#### 5.9.2 `bonds_num_atom`

```python
bonds_num_atom = sum(bond_distribution.values())
```

含义：

- 归一化键长分布求和，表示平均每个 H 原子参与的有效短键规模。

物理意义：

- 这是一个结构复杂度/连接度的简化指标。

#### 5.9.3 `dos_h_atom`

```python
dos_h_atom = h_value / h_atoms
```

含义：

- 每个 H 原子平均分到的 H 态密度。

物理意义：

- 用原子数归一后，试图消除超胞大小带来的线性放大影响。

#### 5.9.4 `dos_h_atom_bond`

```python
dos_h_atom_bond = dos_h_atom / bonds_num_atom
```

含义：

- 在“H 原子平均 DOS”的基础上，再按每原子短键规模继续归一。

物理意义：

- 可理解为“单位 H 原子、单位有效短键规模上的 H 态密度强度”。
- 这个量直接进入 `couple` 计算。

#### 5.9.5 `dos_h_ratio`

```python
dos_h_ratio = h_value / (h_value + total_metal)
```

含义：

- H 在总 DOS 中所占比例。

物理意义：

- 反映费米能附近电子态中 H 成分的主导程度。
- 如果该比例高，模型会认为 H 子晶格对超导相关行为更重要。

---

### 5.10 第九步：特征量 `f2`

公式：

```python
denominator = 1 + dos_h_ratio ** 2
f2 = (dos_h_ratio * couple) / denominator if denominator else 0
```

即：

`f2 = dos_h_ratio * couple / (1 + dos_h_ratio^2)`

物理意义：

- `f2` 是当前模型真正用于预测 Tc 的核心特征。
- 它把两部分信息合并起来：
  - `dos_h_ratio`：H 在总电子态中的占比
  - `couple`：特定 H-H 键长窗口与 H 态密度共同构成的耦合代理量

分母 `1 + dos_h_ratio^2` 起到一个平滑抑制作用：

- 当 `dos_h_ratio` 很小时，`f2` 近似与 `dos_h_ratio * couple` 成正比
- 当 `dos_h_ratio` 持续增大时，增长被分母部分抑制，不再线性放大

因此它本质上是一个经验型、带有饱和抑制的组合特征。

---

### 5.11 第十步：最终 Tc 预测值

公式：

```python
predicted_tc = SLOPE1 * f2 + SLOPE2
```

即：

`Tc = 16370.6 * f2 + 24.7`

物理意义：

- 这是一个线性回归型映射。
- `f2` 是经验构造特征，`Tc` 是基于拟合参数得到的最终估计值。
- `24.7` 可以理解为模型拟合中的截距项。

需要强调：

- 这不是从 BCS 或 Eliashberg 理论直接推出来的封闭理论公式。
- 它是“结构特征 + DOS 特征 -> 特征量 f2 -> 线性拟合 Tc”的经验模型。

---

## 6. 返回值的业务含义

返回模型定义在 `backend/schemas.py`：

- `predicted_tc`: 预测超导临界温度，单位 K
- `f2_value`: 核心中间特征值
- `dos_h_ratio`: H DOS 占总 DOS 比例
- `dos_h_atom_bond`: H 原子-键归一化 DOS 特征
- `bonds_mean`: 有效 H-H 短键均值
- `bonds_var`: 有效 H-H 短键方差

这些字段的业务作用分为两层：

1. `predicted_tc`
   面向终端用户，是主结果。

2. 其他中间量
   面向调试、解释和模型可观察性。
   这些量可以帮助判断：
   - 是几何分布导致 Tc 低
   - 还是 H DOS 占比不够
   - 或者键长窗口没有命中

---

## 7. 当前模块的异常与边界条件

当前实现包含多处输入校验。

### 7.1 结构文件相关

- 结构文件解析失败
- 结构中没有 H 原子
- 删除非 H 原子后仍无法得到 H 子晶格
- 没有任何 `1.4 Å` 以内的 H-H 键
- H 原子总数与最简化学式推算的超胞倍数不一致

这些错误说明当前模型对氢化物结构有明显前提假设，不适用于无氢体系。

### 7.2 PDOS 相关

- 没有上传任何 PDOS 文件
- 无法解析 PDOS 数据
- PDOS 列数不足
- 没有找到 `PDOS_H.dat`
- H 与金属 DOS 之和为 0

这说明模型强依赖输入文件命名和文件格式一致性。

### 7.3 数值相关

- `bonds_num_atom == 0` 时直接报错

虽然在已有逻辑下通常不会发生，但它避免了除零错误。

---

## 8. 当前模块与主站数据库模块的关系

### 8.1 当前关系：同站点、同代码仓、不同数据闭环

现在它们的关系是“同一个 FastAPI 应用下的并列模块”，但业务上基本解耦。

主站数据库模块负责：

- 元素
- 元素组合
- 文献
- 物理参数
- 图片
- 用户
- 审核状态

Tc 预测模块负责：

- 接收一次性上传文件
- 即时计算预测值
- 返回结果给前端

二者共享的只有：

- FastAPI 应用实例
- 前端导航体系
- 公共依赖环境
- `schemas.py` 中的响应模型定义风格

二者当前不共享的内容：

- 不共用数据库表
- 不共享文献主记录
- 不共享用户操作历史
- 不共享图表数据
- 不共享审核流

### 8.2 为什么当前是解耦的

这与代码设计和页面文案一致：

- `tc_pre.html` 已明确写明“上传文件只用于即时计算，不会被持久保存”
- `backend/api/tc_predict.py` 全程没有导入数据库会话
- API 中没有 `get_db`
- 也没有任何 `models` 的写库逻辑

这意味着当前模块更像：

- 一个实验工具页
- 一个研究辅助小服务
- 一个挂在主站上的即时算子

而不是主站数据资产的一部分。

---

## 9. 当前解耦设计的优点与局限

### 9.1 优点

#### 9.1.1 简单

不写数据库，状态少，逻辑直观，调试门槛低。

#### 9.1.2 风险隔离

预测失败不会污染主站数据库，也不会把脏数据写进文献系统。

#### 9.1.3 适合实验阶段

模型、参数、输入格式都可能变化时，先做成即时计算接口是合理的。

### 9.2 局限

#### 9.2.1 结果不可追踪

现在无法回答这些问题：

- 谁做过预测
- 对哪个体系做过预测
- 输入文件是什么
- 结果是多少
- 同一个结构重复跑过几次

#### 9.2.2 无法与文献库联动

当前预测结果不能：

- 关联某篇文献
- 进入主站图表
- 被管理员审核
- 成为“理论预测”数据的一部分

#### 9.2.3 无法形成研究资产

预测只在页面上展示一次，刷新或离开页面后就丢失。

#### 9.2.4 缺少审计与复现实验条件

没有存原始输入、参数版本、模型版本、执行时间，后续很难做复现和比对。

---

## 10. 未来如何接入主站更合理

这里不建议一步到位把它完全并入现有文献表，而应分阶段接入。

### 10.1 第一阶段：先做“预测任务持久化”，不要直接写入文献库

建议新增一张独立表，例如：

`tc_prediction_jobs`

建议字段：

- `id`
- `user_id`
- `status`
- `source_type`
- `source_paper_id`
- `source_compound_id`
- `formula_label`
- `structure_filename`
- `pdos_manifest`
- `predicted_tc`
- `f2_value`
- `dos_h_ratio`
- `dos_h_atom_bond`
- `bonds_mean`
- `bonds_var`
- `model_version`
- `created_at`
- `finished_at`
- `error_message`

这样做的好处：

- 不破坏现有文献库结构
- 先把“预测行为”和“预测结果”沉淀下来
- 允许未来做历史记录、结果回看、失败诊断

这是最符合 KISS 的第一步。

### 10.2 第二阶段：建立与元素体系和文献的显式关联

可以在预测任务表中增加可选外键：

- `source_paper_id`
- `source_compound_id`

含义：

- 如果预测是从某篇文献详情发起，就绑定到 `paper`
- 如果预测是从某个元素体系发起，就绑定到 `compound`
- 如果只是纯上传实验，可以只保留自由文本标签

这样就能实现：

- 在元素体系页展示相关预测记录
- 在文献详情页关联理论预测结果
- 在后台查看某篇文献对应的预测历史

### 10.3 第三阶段：把“高质量预测结果”转化为主站可展示数据

这一步不要直接混入 `papers` 表原始文献记录，而建议新增专用表，例如：

`predicted_material_records`

建议字段：

- `id`
- `compound_id`
- `submitted_by`
- `prediction_job_id`
- `chemical_formula`
- `predicted_tc`
- `pressure`
- `article_type` 固定为 `theoretical`
- `review_status`
- `show_in_chart`
- `notes`
- `created_at`

这样做的原因：

- 文献记录和预测记录本质不同
- 文献有 DOI、期刊、作者
- 预测没有这些天然字段
- 强行塞进 `papers` 表会让语义混乱，字段大量为空

更合理的做法是：

- 预测记录独立存储
- 前端图表层可以联合展示“实验文献数据”和“理论预测数据”

### 10.4 第四阶段：统一图表层，而不是统一底层表

首页和体系页图表不一定要求底层只有一张表。

更好的方案是统一“读模型”：

- 文献实验数据来源：`papers + paper_data`
- 预测数据来源：`predicted_material_records` 或 `tc_prediction_jobs`

然后在 API 聚合层统一输出图表点：

- `x`
- `y`
- `year`
- `type`
- `source_kind`
- `source_id`
- `label`

这样比把所有数据硬塞进 `papers` 更清晰。

---

## 11. 更合理的演进建议

结合当前代码现状，建议按下面顺序推进。

### 11.1 近期建议

先做最小闭环：

1. 新增预测结果持久化表
2. 保存预测结果和模型版本
3. 保存用户 ID 和创建时间
4. 前端增加“我的预测记录”入口

这个阶段不要急着把预测结果变成文献数据。

### 11.2 中期建议

增加以下能力：

1. 从元素体系页发起预测，自动关联 `compound_id`
2. 从文献详情页发起预测，自动关联 `paper_id`
3. 支持管理员审核预测结果是否公开展示
4. 支持将预测记录纳入图表展示

### 11.3 长期建议

如果预测模块持续扩展，可以进一步做：

1. 异步任务队列
2. 文件对象存储
3. 模型版本管理
4. 预测结果复现和对比
5. 用预测记录支撑新的“理论候选材料库”

---

## 12. 当前代码对应的业务结论

基于当前实现，可以得出如下结论：

1. 这个模块是一个面向含氢体系的轻量经验 Tc 预测器。
2. 它依赖两个输入源：
   - 结构几何信息：来自 CONTCAR/POSCAR
   - 费米能附近投影态密度：来自 PDOS 文件
3. 它的核心思想是：
   - 从 H 子晶格抽取短程 H-H 键长分布
   - 用 H DOS 占比和 H-键归一化 DOS 构造经验耦合特征
   - 最终通过线性拟合输出 Tc
4. 它目前是即时计算工具，不是主站数据库的一部分。
5. 它未来更合理的接入方式不是直接塞进 `papers`，而是先建立独立的预测结果持久化层，再通过关联和聚合接口接入主站。

---

## 13. 一句话总结

当前 Tc 预测模块本质上是一个“挂在超导文献主站上的即时经验预测服务”；它已经具备独立计算能力，但尚未形成可追踪、可审核、可复用的主站数据资产。后续最合理的方向，是先把预测任务和结果独立持久化，再逐步与元素体系、文献详情和图表层建立关联，而不是直接并入现有文献表。
