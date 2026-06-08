# 摘要修改意见落实记录

来源意见：`articles/comments_response.md`

## 已落实的核心修改

- 删除摘要中把 `screenshots from source articles`、`review status of each record` 作为核心对象或创新点的写法。
- 将论文处理对象从笼统的 `superconductivity literature` 改为 `superconductors and superconducting systems`。
- 将 `element-search modes` 改为 `superconductor-search modes`，同时保留周期表入口作为实现路径。
- 将 `compound-specific literature browsing` 和 `DOI-driven paper submission` 改写为面向指定超导体系的 DOI 连接、DOI-based paper submission。
- 明确 `batch import` 的含义：从约定格式表格或文本中批量导入多条超导论文和物理参数记录。
- 将 `JSON import/export utilities` 改写为 `JSON-format superconducting-data import and export`。
- 删除 `experimental Tc-prediction page` 中对本功能“实验性”的负面暗示，改为结构文件和 PDOS 输入驱动的 Tc prediction page。
- 删除摘要中管理员/超级管理员流程作为创新点的表达，将审核与权限流程放入正文，定位为质量控制和系统治理基础设施。
- 将截图能力改为“visual attachments / structural and source-traceable information”，并在正文中说明未来显示方向应强调晶体结构可视化，而不是把截图上传作为论文贡献点。

## 输出文件

- 英文 LaTeX：`final_paper/main.tex`
- 中文 LaTeX：`final_paper/main_zh.tex`

## 写作边界

本文仍保持 PaperSpine 已确认的定位：资源型/数据库型/科研软件系统论文，不声称提出新超导机制，也不声称 Tc 预测模型已经完成系统验证。
