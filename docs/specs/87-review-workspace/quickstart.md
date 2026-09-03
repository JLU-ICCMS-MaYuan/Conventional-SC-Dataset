# 快速验证：管理员文献处理历史

**Feature**：[spec.md](spec.md)

## 前置条件

```bash
make start
```

使用管理员、超级管理员和普通上传者三个账号；准备一篇新上传论文和一篇已有审核意见的论文。

## 场景 1：编辑页元数据

1. 管理员打开论文编辑页。
2. 检查“上传者”和“物性记录: N”。

预期：上传者来自真实详情接口；物性数量对应当前版本
`superconductor_properties`，不显示默认 `-` 或错误的 0。

## 场景 2：处理记录

1. 管理员点击“处理记录”。
2. 检查上传、修改、审核事件顺序和字段。
3. 以普通用户访问历史 URL。

预期：管理员看到时间线及每次审核意见；普通用户收到 403，不能查看内部历史。

## 场景 3：写入和去重

1. 上传一篇新论文。
2. 在编辑页改动论文级和科学数据后点击一次“保存修改”。
3. 再次直接保存不改动的数据。
4. 由两位管理员先后退回、通过。

预期：时间线依次新增上传、一次修改、两次审核；无改动保存不增加事件。

## 自动化验证

```bash
scripts/run-tests.sh go
scripts/run-tests.sh backend
cd frontend && npx vitest run --config ../vitest.config.ts ../tests/02_identity_governance/
cd frontend && npm run build
```

预期：迁移、上传、审核、修改、统计、删除、权限和页面测试通过；生产构建无类型错误。

## 本次验证记录（2026-09-03）

- 处理历史相关的 Python 元数据、迁移链、上传分类兼容和 fresh-schema 静态回归：`22 passed, 4 skipped`。
- 上传工作流：`18 passed`；已覆盖新上传及重试只写一条 `uploaded`。
- Go 处理历史、详情和删除/统计相关测试通过；前端编辑页：`10 passed`；生产构建通过。
- `backend/tests/test_scientific_draft_rewrite.py` 的 13 个隔离 MySQL 用例和迁移的真实数据保留用例因未提供 `FRESH_MYSQL_DATABASE_URL` 跳过。未验证项包括旧审核事件迁移、上传回填、MySQL 外键索引保留、科学数据同值保存和跨端操作标识去重。
- 本次复核的历史元数据、上传与分类兼容用例：`37 passed, 1 skipped`；数据库依赖集合：`1 passed, 14 skipped`。跳过项均由缺少隔离 MySQL URL 造成，不代表已通过真实迁移验收。
