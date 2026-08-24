# Quickstart：论文附件晶体结构提取

**GitHub Issue**：[#49](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/49)

## 前置条件

1. 使用项目 Docker Compose 启动 FastAPI、RQ Worker、Redis 和 MySQL。
2. 安装 Python 依赖，确认 `ase`、`pymatgen` 和 PyMuPDF 可导入。
3. 使用已登录测试用户；准备一个可搜索正文 PDF、一个合法 CIF、一个合法 POSCAR，以及
   一个包含完整坐标和一个包含 Wyckoff 位点的 PDF 测试夹具。
4. 测试数据库使用 #32/#46 目标 Schema；不要连接或修改历史业务库。

## 端到端验证

```powershell
cd "//wsl$/Ubuntu-20.04/home/mayuan/code/SC-Wiki"
docker compose up -d api worker redis mysql
pytest backend/tests/test_structure_candidates.py backend/tests/test_upload_jobs.py -q
pytest tests/02_maintenance_and_verification/test_fresh_mysql_schema.py -q
npm --prefix frontend run build
npx vitest run tests/01_decentralized_uploading/structure-candidates.test.tsx
```

## 手工路径

1. 在上传任务中选择正文 PDF 和 CIF/POSCAR 附件，确认文件角色后开始解析。
2. 打开解析详情，检查候选材料状态、压力、物相、计算条件、来源文件、页码/表格和证据句。
3. 对 PDF Wyckoff 候选检查“推导”标识、独立位点和空间群；对缺失或冲突候选确认其 blocked
   原因，不补猜。
4. 打开候选预览，确认 3Dmol.js 默认显示惯用胞；分别选择原胞/惯用胞和 CIF/POSCAR 导出。
5. 明确确认需要提交的候选，提交论文审核。
6. 以管理员批准当前 revision，再用授权普通用户查看论文详情；确认 pending/rejected/旧
   revision 不可被普通用户预览或导出。

## 预期信号

- 合法原生附件和完整 PDF 候选进入 `valid`，每个候选四种表示可重新读取。
- 同一材料状态等价 PDF/附件合并为一个候选但保留多条来源。
- 缺字段、冲突、部分占位和无序候选保持 `blocked` 或 `needs_review`，不生成完整结构。
- 未确认候选不会出现在正式 `structure_models`。
- 提交晚期失败后，Paper、Evidence 和结构实体没有残留新增记录。
- approved 当前 revision 的授权查看和导出成功；无权限请求不返回内容。
