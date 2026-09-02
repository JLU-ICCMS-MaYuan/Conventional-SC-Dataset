# 验收指引：引用图谱

**GitHub Issue**：[ #81](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/81)

## 前置条件

1. Docker Compose 已启动 MySQL、Redis、Python、Worker、Go 和 GROBID。
2. 已有至少三篇可审核样本：A 被 B、C 引用，且 B 也引用 A；另准备一个尚未收录目标的引用。
3. 使用管理员账号和普通读者账号各一次。

## 场景 1：解析和延迟匹配

1. 上传 B 的 PDF，等待解析任务完成并打开校对数据。
2. 确认参考文献展示 DOI、题名、年份和原始引文；GROBID 不可用时确认显示解析状态而不是空引用结论。
3. 审核 B。若 A 已审核，确认 B 的引用记录匹配到 A。
4. 对引用尚未入库的论文重复上传并审核目标，确认旧引用自动匹配。

预期：只有真实已匹配记录形成图边；重复引文不增加 A 的下游论文计数。

## 场景 2：分类概览和展开

1. 打开“脉络”，选择 Material family 和常规/非常规筛选。
2. 确认节点短标题、年份、圆点大小和里程碑标记可见。
3. 搜索 B 标题并固定到图中。
4. 对 A 展开下游：首次只出现五篇或更少，并显示“尚有 N 篇”；继续加载下一页。
5. 对 C 展开上游，确认 A 只有一个节点，三条引用边均保留。

预期：分类使用论文级字段；`unknown` 不在常规/非常规筛选中但能被标题搜索；没有重复节点。

## 场景 3：人工里程碑

1. 管理员把 A 标记为 `origin` 和 `breakthrough`。
2. 普通用户读取图谱，确认看到两个标记。
3. 普通用户尝试写入同一路径，确认收到 403。

## 自动化验证

```bash
python -m pytest backend/tests/test_citation_graph.py tests/02_maintenance_and_verification/test_issue81_citation_graph_schema.py -q
cd frontend && npm run test:upload-ui -- tests/01_decentralized_uploading/upload-task-editor-layout.test.tsx tests/03_data_search_and_database_discovery/english-ui-sweep.test.tsx
cd frontend && npm run build
cd goserver && go test ./...
docker compose -f docker/compose.yaml config
```

在具备 Docker 环境时，再确认 `grobid` healthcheck 为 healthy。
