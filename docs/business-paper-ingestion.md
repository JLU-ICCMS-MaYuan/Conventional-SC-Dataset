# 文献采集与数据入库

## 1. 这是什么业务

这一模块负责把外部文献信息转成数据库中的结构化记录，覆盖单篇上传、DOI 元数据解析、多组超导记录录入、批量上传入口、JSON 导入导出和数据迁移支持。

## 2. 单篇上传流程

### 2.1 入口
- 组合页上传弹窗
- 后端接口：`POST /api/papers/`

### 2.2 基本前提
- 必须登录
- 必须提供 DOI
- 必须指定文章类型和超导体类型
- 必须至少提供一组物理数据

### 2.3 上传步骤
1. 前端收集当前组合页的元素集合
2. 提交 DOI、元素、分类字段、物理数据、截图和备注
3. 后端校验登录态
4. 后端解析 JSON 字符串形式的 `records`
5. 后端进行 DOI 有效性校验并尝试抓取元数据
6. 后端按每条记录的 `chemical_formula` 获取或创建 `chemical_systems` 和 `superconductors`
7. 检查 DOI 是否已存在
8. 创建 `papers`
9. 为该文献创建多条 `superconductor_records`

## 3. DOI 元数据策略

### 3.1 普通用户
- 必须通过 DOI 校验
- 必须成功拉取元数据，否则上传失败

### 3.2 管理员
- 可跳过严格 DOI 校验
- 如果元数据抓取失败，系统会使用占位信息创建记录

## 4. 物理数据模型

每篇文献可以有多组 `superconductor_records` 数据点。每条记录至少需要：

- `chemical_formula`
- `pressure_gpa`
- 至少一种 Tc 字段，例如 `mcmillan_tc`、`allen_dynes_tc`、`isotropic_eliashberg_tc`、`anisotropic_eliashberg_tc`、`experimental_tc`

业务含义：
- 一篇论文可对应多个压强点或多组结果
- 同一个超导体化学式可以关联多篇论文
- 同一个化学式、压强、空间群下可以记录不同来源或方法给出的超导结果
- 稳定性、能量凸包上方能量、赝势、k/q 网格、截断能、电子态密度等计算设置保存在 `superconductor_records`

## 5. 晶体结构存储

当前晶体结构正文由 `superconductors_structures` 表保存，支持 `cif` 和 `poscar` 两种格式。上传结构时后端会使用 ASE 解析校验，解析失败不会写入数据库。

结构存储粒度为“化学式 + 空间群 + 压强”。同一粒度下可以保存多个版本，管理员审核通过后，最新审核通过版本会成为该粒度下的默认结构。`superconductor_records.crystal_structure` 仍用于结构类型或空间群描述，不保存 CIF/POSCAR 正文。

已落地的结构接口包括：

- `POST /api/structures/`：登录用户上传结构，初始状态为 `pending`
- `POST /api/structures/{structure_id}/review`：管理员或超级管理员审核结构
- `GET /api/structures/by-record/{record_id}`：按超导记录的化学式、空间群和压强查找已审核默认结构
- `GET /api/structures/representative`：按化学式和空间群查找代表结构
- `GET /api/structures/{structure_id}/raw`：下载 CIF/POSCAR 原文；未审核结构仅创建者或管理员可下载

代表结构选择只从 `approved` 结构中取值，优先默认结构，再按压强升序和创建时间倒序选择。

## 6. 图片处理

- 当前代码不再保存文献截图
- `paper_images` 和图片 BLOB 路径已下线
- 图片读取接口返回 410，表示该能力已停止提供

## 7. 批量上传与导入

### 7.1 首页快速上传
- 入口位于首页
- 接口：`POST /api/papers/batch-upload`
- 当前接口保留入口，但新 MySQL 结构下的批量导入逻辑标记为未实现
- 需要按新 `papers + superconductor_records` 结构重新设计导入字段

### 7.2 JSON 导入导出

#### 导出
- 脚本：`python -m backend.export_data`
- 当前导出 `mysql-redesign-v1` JSON
- 导出内容包括 `users`、`papers`、`superconductor_records` 和 `superconductors_structures`
- `chemical_systems` 与 `superconductors` 可由记录中的 `chemical_formula` 重建

#### 导入
- 脚本：`python -m backend.import_data <json_path>`
- 当前支持导入 `mysql-redesign-v1` JSON
- 可使用 `--clear` 清空业务数据后重建
- 若导入文件没有可用上传用户，系统会创建 `import@example.local` 作为导入用户
- 结构导入要求每条 `superconductors_structures` 包含 `chemical_formula`、`pressure_gpa`、`structure_format`、`structure_text` 和 `structure_hash`，缺失时会直接报错，不会静默丢弃

### 7.3 ID 迁移
- 旧 `migrate_ids` 脚本面向旧组合表，新 MySQL 结构不再依赖 `element_id_list`

## 8. 采集模块与其他模块的关系

- 依赖认证模块控制谁能上传
- 依赖元素组合模块决定文献归属到哪个体系
- 依赖审核模块控制文献后续状态
- 依赖图表模块决定是否在首页展示

## 9. 边界与限制

- 上传不是全文解析流程，当前主要依赖 DOI 元数据和手工补充字段
- 批量导入并不等价于自动高质量清洗，仍依赖输入文件质量
- 导入导出是运维级能力，不等于前端用户常规操作
- 当前系统没有完整的重复合并策略，主要依赖 DOI 全局唯一和化学式标准化
