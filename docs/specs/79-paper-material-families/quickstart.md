# 快速验收：论文级 Material family 多选分类

**GitHub Issue**：[#79](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/79)

## 自动验证

```bash
python -m pytest tests/01_decentralized_uploading/test_issue51_classification_workflow.py tests/01_decentralized_uploading/test_issue51_legacy_contract.py tests/02_maintenance_and_verification/test_issue79_paper_material_family_schema.py
go test ./goserver/handlers/...
npm --prefix frontend run test:upload-ui -- upload-task-editor-classification admin-edit-page paper-detail-form-parity
npm --prefix frontend run build
```

预期：命令全部退出 0；测试覆盖多 family、空列表校验、状态级字段移除、More type labels 保留和迁移去重。

## 人工验收

1. 打开 ready 状态上传任务，确认 Paper type 和理论子分类控件与原来一致。
2. 在论文级 Material family 中选择一个目录项并自由输入第二项，保存后刷新，确认两项回填。
3. 新增两个材料状态，确认状态卡片无 Material family，More type labels 仍可分别多选。
4. 清空论文级 family 后保存草稿，确认保存成功；随后提交，确认收到明确的必填提示并定位论文级控件。
5. 恢复至少一项并提交；管理员编辑页确认顶层 family 列表回填，批准后公开详情展示全部项。
6. 对已批准论文修改科学数据，确认升版并退回 pending，既有 family 关联随版本级联保留；随后用当前 family 选择批准并确认关联整体替换。

## 迁移验收

1. 在迁移前准备：同论文两个状态使用同一 family；另一论文两个状态使用不同 family。
2. 执行 `alembic upgrade head`。
3. 确认第一篇论文关联一项、第二篇关联两项，原审核状态不变，状态表不再有 `material_family_id`。
4. 对含多个 family 的数据库尝试 downgrade，确认明确拒绝且数据不变。
