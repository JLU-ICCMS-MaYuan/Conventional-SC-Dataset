# 元素检索与文献发现

## 1. 这是什么业务

这一模块负责把“选元素或化学式”转化为“查超导体体系和相关文献/记录”。它覆盖首页周期表交互、元素组合标准化、四种检索模式、组合页文献展示、关键词/年份/审核状态筛选、分页以及列表导出。

## 2. 用户入口

- 首页：`/`
- 组合页：`/compound/{element_symbols}`
- 主要前端脚本：`frontend/static/js/periodic_table.js`、`frontend/static/js/compound_page.js`
- 主要后端接口：
  - `/api/compounds/search`
  - `/api/papers/compound/{element_symbols}`
  - `/api/papers/search-by-mode`

## 3. 首页元素选择流程

### 3.1 周期表交互
- 首页渲染完整元素周期表
- 用户点击元素后，前端使用 `Set` 维护已选元素
- 元素可重复点按切换选中状态

### 3.2 四种检索模式

#### `formula_search`
- 按输入化学式标准化后精确检索 `superconductors.formula_normalized`
- 适合直接搜索 `LaH10` 这类明确化学式

#### `elements_exact_search`
- 只返回元素集合与当前选择完全一致的体系
- 适合精确查看某个二元、三元或多元体系

#### `elements_combination_search`
- 返回“所选元素的所有已存在子组合”
- 例如选择四种元素时，可能看到其中单质、二元、三元体系

#### `elements_contained_search`
- 返回所有包含所选元素的体系
- 适合做“以某些元素为核心”的扩展检索

### 3.3 跳转行为
- 前端会将已选元素排序后拼接为路径参数
- 模式写入查询参数 `?mode=...`
- 进入 `/compound/{sorted_symbols}`

## 4. 后端组合标准化逻辑

### 4.1 元素组合统一规则
- 所有元素组合按符号排序
- 使用 `-` 连接形成 `chemical_systems.system_key`
- 元素列表保存在 `chemical_systems.elements_list`
- 化学式按元素排序标准化后保存在 `superconductors.formula_normalized`

### 4.2 组合检索逻辑
- `formula_search`：标准化化学式完全相等
- `elements_exact_search`：体系元素集合必须完全相等
- `elements_combination_search`：数据库中的体系元素集合必须是用户选择集合的子集
- `elements_contained_search`：用户选择集合必须是数据库体系元素集合的子集

### 4.3 兼容性处理
- 前端仍兼容旧 URL 参数 `only`、`combination`、`contains`，会映射到新模式名
- 空组合或无效元素不会返回结果

## 5. 组合页文献浏览逻辑

### 5.1 页面加载
- 页面直接显示当前路径中的元素体系标题和当前模式描述
- `elements_exact_search` 模式下，默认按单一体系读取文献
- `elements_combination_search` 和 `elements_contained_search` 模式下，按体系集合聚合文献并分段展示
- 页面不再提供“数据库”下拉框；进入体系后统一展示来自论文和人工指定 `source_label` 的结构化数据

### 5.2 可用筛选
- 审核状态：全部、已通过、未审核、已拒绝、需修改
- 关键词：标题、作者、化学式
- 年份区间：最小年份、最大年份
- 分页：每页 30 篇

### 5.3 列表展示内容
- 标题、年份、作者、通讯作者
- 文章类型、超导体类型、审核状态
- 化学式、晶体结构、摘要
- 多组物理参数
- DOI 与 RIS 导出按钮
- 文献关联的超导记录摘要

## 6. 导出逻辑

### 6.1 单篇导出
- 在文献卡片中生成 RIS 内容并触发下载
- 该逻辑主要在前端完成

### 6.2 列表页批量导出
- 前端提供导出入口
- 当前组合页偏向导出“当前展示结果”
- 需以当前页面筛选结果为准理解，不应误认为支持复杂馆藏式批量勾选工作流

## 7. 边界与限制

- 列表页展示依赖后端返回 JSON；当接口返回非 JSON 错误时，前端会将其视为加载失败
- 检索模式只影响体系匹配逻辑，不改变文献审核规则
- 组合页不是全文搜索入口，本质上是围绕元素体系的结构化筛选入口
- 首页说明中提到的部分未来联动能力当前未实现
