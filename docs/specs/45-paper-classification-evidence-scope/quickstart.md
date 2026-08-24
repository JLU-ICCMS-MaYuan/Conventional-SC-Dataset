# 快速验收：论文分类证据作用域与汇总前状态

## 前置条件

- 在仓库根目录执行命令。
- Python 测试依赖和前端 `node_modules` 已安装。
- 不需要真实 LLM 密钥；回归测试使用固定分段产物。

## 1. 后端分类与缓存回归

```bash
python3 -m pytest \
  backend/tests/test_upload_jobs.py \
  tests/01_decentralized_uploading/test_issue23_upload_lifecycle.py \
  tests/01_decentralized_uploading/test_issue24_persistence_and_ui.py -q
```

预期：

- Li–Mg–H 引用实验和综述证据不进入本文候选。
- `unknown` 不与有效本文类型冲突。
- 旧分段缓存被安全重读或降级。
- 标题冲突测试继续通过。

## 2. 前端临时状态回归

```bash
npm --prefix frontend run test:upload-ui -- \
  ../tests/01_decentralized_uploading/upload-task-workspace.test.tsx
```

预期：

- 分类区域显示“候选尚未汇总”。
- 标题候选不一致仍显示“有冲突”。
- 本文自由材料类型原样展示。

## 3. 原始任务产物回放

使用任务 `9ba7e6d5e33040f192a604759d3d3716` 保存的分段结构化结果调用公开解析详情聚合器。

预期：

- “Subsequent experimental work” 和“There have been few studies”仍可在分段证据中查看。
- 两者不会进入本文论文类型候选。
- 本文结构搜索和计算证据保留为 `theoretical` 候选。
- 分类字段处于“候选尚未汇总”，不显示正式冲突。

若原任务临时数据已过期，使用测试中的固定 Li–Mg–H 产物执行同一回放。

## 4. 完整回归

```bash
python3 -m pytest tests/01_decentralized_uploading backend/tests/test_upload_jobs.py -q
npm --prefix frontend run test:upload-ui
npm --prefix frontend run build
```

预期：全部通过，且构建不产生新的 TypeScript 错误。
