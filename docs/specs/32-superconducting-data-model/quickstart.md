# 快速验收：全新空库的条件化超导数据模型

## 前置条件

- 只使用可销毁的隔离空 MySQL 8.4。
- `DATABASE_URL` 明确指向该测试库，不得指向两个现有数据库。
- #33 的论文血缘 revision 位于 #32 revision 之前。
- 数据库用户具备测试库 DDL 权限。

## 1. 静态模型测试

```bash
cd /home/mayuan/code/SC-Wiki
python3 -m pytest tests/02_maintenance_and_verification/test_issue32_schema.py -q
cd goserver
go test ./models -run ScientificSchema
```

预期：表名、列、DECIMAL 精度、外键、CHECK、索引和生成列一致；科学子实体无审核列。

## 2. 从完全空库升级

```bash
cd /home/mayuan/code/SC-Wiki
alembic upgrade head
alembic current
```

预期建立材料状态、结构、双上下文、纵向 Tc、属性定义、`superconductor_properties` 和三类
Evidence 连接；不建立 `key_properties`，临时旧科学表在 head 不存在。

## 3. 约束场景

1. LaH10 与 LaD10 使用不同 `composition_key`。
2. 同一材料和压力可插入两个状态。
3. 跨论文/revision 的状态、上下文和 Evidence 连接被拒绝。
4. 理论 Tc 只有理论上下文，实验 Tc 只有实验上下文。
5. 同方法可保存多条非代表 Tc，第二条代表 Tc 被拒绝。
6. 普通物性保留 `name_raw/value_raw/unit_raw`，规范字段可空。
7. 子科学表不存在审核状态、审核人和审核时间。

## 4. 现有数据 guard

仅在另一可销毁测试库中先插入任意业务记录，再尝试目标 revision。

预期：迁移在 DDL 收缩和数据转换前失败，并说明不支持现有库迁移。

## 5. 空库可逆性

```bash
alembic downgrade 20260821_0007
alembic upgrade head
```

预期：仅在空测试库完成；不得用于两个现有数据库。

## 6. 最终回归

```bash
python3 -m pytest tests/02_maintenance_and_verification -q
cd goserver && go test ./...
git diff --check
```

没有隔离 MySQL 时必须明确报告集成测试未执行，不得用 SQLite 代替。
