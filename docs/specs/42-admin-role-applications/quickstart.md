# 快速验收：管理员资格申请

1. 使用未验证、缺姓名、缺机构、已是管理员账号申请，确认均被拒绝。
2. 使用资料完整普通用户申请，确认保存快照且不能再次提交。
3. 修改当前资料，确认待审核快照不变；撤回后重新申请得到新快照。
4. 管理员尝试审批，确认 403。
5. 超级管理员拒绝但不填原因，确认失败；填写原因后成功且用户可再申请。
6. 批准新申请，确认申请状态和用户角色同时变化。
7. 带原因降级，确认用户可再申请且历史完整。

```bash
cd goserver && go test ./...
python3 -m pytest tests/02_maintenance_and_verification -q
cd frontend && npx vitest run --config ../vitest.config.ts && npm run build
```
