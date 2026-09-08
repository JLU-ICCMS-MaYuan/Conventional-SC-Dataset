# 快速验收

## 自动验证

在项目根目录使用已有依赖：

```bash
node "frontend/node_modules/vitest/vitest.mjs" run --config "vitest.config.ts" "tests/01_decentralized_uploading/property-record-editor.test.tsx" "tests/01_decentralized_uploading/material-states-editor.test.tsx"
(cd "frontend" && node "node_modules/typescript/bin/tsc" -b)
DATABASE_URL="sqlite://" JWT_SECRET_KEY="test-only-secret" "$HOME/miniconda3/envs/sc-wiki/bin/python" -m pytest "backend/tests/test_property_record_conditions.py" "backend/tests/test_property_modules.py" "backend/tests/test_upload_jobs.py" -q
```

Python 测试使用 SQLite 内存数据库，不触碰开发数据或真实 LLM。

## 界面路径

1. 上传校对或管理员编辑页打开一个材料状态，添加测量 Tc、预测 Tc 和自定义性质。
2. 确认菜单和标题无模板版本后缀；测量 Tc 只显示一个实验条件多行框。
3. 填写两条不同条件，分别折叠/展开；修改、复制和删除一条，确认另一条保持不变。
4. 保存后再次读取，确认文本及换行保留；只读详情可折叠且不可编辑。
5. 打开旧结构化条件，确认内容可读；编辑后原始字段与 Evidence 仍在导出数据中。

真实 LLM 输出质量需用具体论文复核；自动测试证明提示词接入和实际数据通路，不声称覆盖外部模型每次生成。

## 本次验证结果（2026-09-08）

- 前端 48 项通过：本功能 6 项、共享材料状态 25 项、管理员科学数据编辑 5 项、管理员数据展示及详情字段一致性合计 12 项。
- 后端 62 项通过：本功能提取到数据库及导出往返、描述类型与空值、模块持久化、上传归一化和材料状态导出。
- TypeScript 项目编译通过。
- 上述为本地自动验证，不代表生产部署或真实 LLM 对特定论文的准确率。
