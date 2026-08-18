# I. 超导数据去中心化上传

## 功能定义

Decentralized Uploading of Superconductivity Data 指研究者或注册用户把超导相关数据提交到 SC-Wiki 的入口能力。这里的 decentralized 不是区块链意义的完全去中心化，而是相对于单一维护者手工录入而言：平台允许多个用户提交论文、超导物理记录和晶体结构，由后续维护与审核流程决定可信状态。

## 当前状态

当前状态是已部分落地。代码已经支持用户注册登录、论文和超导记录提交、CIF/POSCAR 晶体结构提交、DOI 元数据解析和结构文本校验。尚未完成的是新 MySQL 结构下的批量上传闭环，以及用户提交后的细粒度修改、撤回和协作修订体验。

## What Users Can Upload

用户上传的核心内容分三类。

第一类是论文元数据。论文保存在 `papers` 表，包含 DOI、标题、期刊、卷页、年份、摘要、作者、上传用户、审核用户和审核状态。普通用户上传时依赖 DOI 校验和 DOI 元数据解析；管理员在部分失败场景下可以使用更宽松的占位元数据。

第二类是超导结构化记录。每篇论文可以对应多条 `superconductor_records`，用于描述同一论文中的多个化学式、压强点、空间群、稳定性、Tc、电子声子耦合参数、计算设置和备注。它们是平台真正可检索、可画图、可被 RAG 或知识图谱使用的核心数据点。

第三类是晶体结构。结构正文保存在 `superconductors_structures` 表，支持 `cif` 和 `poscar` 两种格式。结构按超导体、空间群和压强组织，保存结构哈希、原始文本、来源、创建用户、审核状态和默认版本。这个能力已经并入本功能，不再作为独立的大功能单列。

## Main User Flow

1. 用户从首页周期表或化学式搜索进入 `/compound/{element_symbols}`。
2. 用户登录后在组合页提交 DOI、分类字段和一组或多组超导记录。
3. 后端解析记录中的 `chemical_formula`，自动获取或创建 `chemical_systems` 和 `superconductors`。
4. 后端创建 `papers`，并把每个数据点写入 `superconductor_records`。
5. 用户或维护者可以通过结构接口上传 CIF/POSCAR 结构文本。
6. 结构上传时后端使用 ASE 解析校验；解析失败不会写入数据库。
7. 新提交内容进入后续审核、维护和展示流程。

## Code and API Evidence

主要页面是 `/compound/{element_symbols}`，模板为 `frontend/templates/compound.html`，前端脚本为 `frontend/static/js/compound_page.js`。核心后端在 `backend/api/papers.py`、`backend/api/structures.py`、`backend/models.py` 和 `backend/services/structure_storage.py`。

相关接口包括：

- `GET /api/papers/compound/{element_symbols}`
- `POST /api/papers/search-by-mode`
- `GET /api/papers/{paper_id}`
- `POST /api/structures/`
- `POST /api/structures/{structure_id}/review`
- `GET /api/structures/by-record/{record_id}`
- `GET /api/structures/representative`
- `GET /api/structures/{structure_id}/raw`

当前代码中图片存储能力已经下线，图片读取接口返回 410。旧文档里提到的截图或图片 BLOB 不能再当作当前上传能力来描述。

## Data Model Boundary

`superconductors.formula_normalized` 是当前超导体实体的唯一标识。`superconductor_records` 是具体数据点，不能仅靠化学式唯一标识，因为同一化学式可能在不同压强、空间群、论文、方法和来源下出现多个记录。晶体结构的业务分组接近 `superconductor_id + space_group_symbol + space_group_number + pressure_gpa`，但表中保留多版本，不强制把这个组合做成唯一键。

## Limitations

批量上传入口在前端和旧接口语义中仍能看到，但新 MySQL 结构下的批量导入需要围绕 `papers + superconductor_records` 重新设计字段映射。当前没有完整的用户自助修订工作流，也没有对提交内容进行多人讨论、投票或版本协作的社区机制。

## Future Direction

后续最自然的方向是把批量上传重做成新数据模型的一等入口，增加提交记录的版本历史，允许用户补充结构和物理参数，并把上传、审核、公开展示之间的状态变化做得更透明。
