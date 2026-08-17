# Development pilot 环境报告

**日期**：2026-08-17  
**分支**：`mayuan-RAGtest`  
**状态**：development/provisional；PDF Gate 未通过

## 数据快照

- MySQL：642篇论文、1101条属性记录。
- Qdrant：`paper_chunks` 主集合包含29311个1536维向量；development embedding API 已完成真实查询。
- Neo4j：415个 `Paper` 节点、5000条 `RELATES_TO`、452条 `DEVELOPS_TO`；不存在计划schema中的 Material/Property、STUDIES、HAS_PROPERTY。

## S5 HTTP/SSE 冒烟

| 入口 | HTTP | 完整结束 | 首事件 | 文本TTFT | 总延迟 |
|---|---:|---:|---:|---:|---:|
| FastAPI `python:8000` | 200 | 是 | 0.111秒 | 1.556秒 | 7.778秒 |
| Go代理 `goserver:8080` | 200 | 是 | 0.033秒 | 1.706秒 | 8.361秒 |

每个入口只运行1次，只能证明冒烟可用，不能估计p50/p95。现有事件未返回可靠usage，因此本轮不报告token与成本。

## 20题流程pilot

- A版：首次运行发现3道命令式题面，保留为错误样例。
- B版：题面修订后，8题被工具依赖阻断、3道多跳题待运行、9题可进入development。
- C版：多跳工具修复并运行后，8题被工具依赖阻断、12题可进入development。
- D版：embedding 恢复后，3道混合题被Neo4j材料schema阻断，5道Qdrant题等待临时gold裁决，12题可进入development。
- 所有临时gold均为 `pdf_verified=false`。

原始JSONL、汇总CSV、错误JSONL和metadata分别保存在 `dev-pilot-20260817-a/b/c/d/`，实验目录不可覆盖。

## S1与S4在线tracer

- S1：8道需要文献检索的development题均返回Top-5，成功率8/8，单次延迟0.884至1.396秒，score均按降序返回。
- embedding 输出1536维，与`paper_chunks`集合维度一致。
- 检出重复逻辑chunk：部分Top-5包含相同`(paper_id, chunk_index)`；正式排名前需去重或清理重复point。
- S4物理隔离：LLM-only未调用工具；Qdrant-only只调用`search_literature`；Qdrant+MySQL只调用`search_literature/query_properties`；全工具组只调用允许的Neo4j工具。
- tracer延迟：LLM-only 5.284秒、Qdrant-only 75.114秒、Qdrant+MySQL 12.500秒、全工具组19.801秒。均为单次样本，不代表p50/p95。
- 当前Docker默认DNS不能解析embedding API域名；本轮使用一次性容器host映射完成测试，未修改系统或Compose。

## 修复与验证

- Qdrant：保留原始cosine score，删除错误的 `1-distance` 反转。
- Mentor：`build_graph(tools=...)`支持物理工具隔离；四个生产消融组在Docker运行依赖中通过。
- MySQL：异步URL切换为`asyncmy`，查询保留数值范围、单位、压力、温度、condition和论文信息。
- Neo4j：修复关系过滤Cypher，保留真实边方向与遍历方向；兼容旧`import_label`。
- 离线回归：17 passed，2 skipped；两项skip因系统Python缺少Qdrant/LangGraph依赖，已在生产Docker镜像中以公共接口断言通过。

## 仍未满足

- 当前Neo4j快照不满足目标材料图schema，材料型S3与混合题不能运行。
- 5道Qdrant题的临时gold尚未独立裁决，不能计算有意义的Recall/MRR/nDCG。
- Docker默认DNS仍不能解析当前embedding API域名，正式运行前需修复DNS，不能长期依赖固定IP。
- 未进行两名领域人员的独立标注与裁决。
- 原始PDF未到位，不能将临时gold升级为正式gold。
- 尚未执行四组×20题的完整Mentor消融，因此本报告不包含正式正确性、忠实度、引用、token或成本结论。
