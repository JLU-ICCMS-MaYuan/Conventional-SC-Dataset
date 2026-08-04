# Tc 历史与压力图表

## 功能说明

从公开超导记录生成发现年份与 Tc、压力与 Tc 的统计数据，并在首页绘制交互图表。

## 当前行为

- `/api/papers/stats/chart-data` 只选取明确设置 `show_in_chart` 的记录。
- 数据规则区分实验和理论 Tc，并按既定精度优先级选择展示值。
- 首页使用 Chart.js 绘制年代和压力图，区分数据类型及超导类别。
- 图表包含液氮温度和室温等参考线，并展示 Nobel 学者静态内容。

## 工作流程

首页请求图表数据；后端查询论文和记录并执行筛选规则；前端转换数据集并创建 Chart.js 实例；用户查看提示、图例和参考线。

## 约束

- 未显式公开的记录不会进入图表。
- 统计结果反映数据库当前收录范围，不代表完整学科历史。
- 静态 Nobel 内容不由论文数据库动态生成。

## 代码与测试

- `backend/api/papers.py`
- `backend/chart_rules.py`
- `frontend/src/pages/HomePage.tsx`
- `tests/07_researcher_community_forum/test_chart_rules.py`

## 相关变更记录

当前未发现可链接的已完成 Feature 或 Debug 记录。

## 已知问题

- 当前图表源码能否由缺失的前端工具模块成功构建待核验。
