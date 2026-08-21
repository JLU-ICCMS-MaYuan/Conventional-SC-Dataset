# 技术研究：社区 Tc 双图个人配置与品质因子

## 决策 1：以 `superconductor_records` 为图表数据源

- **决策**：两个统计接口从 `superconductor_records` 联接 `superconductors` 与 `papers`。
- **理由**：只有该表包含五个独立 Tc 字段及 `show_in_chart`。
- **备选方案**：继续读取 `key_properties.value_max`；无法无歧义支持五字段，拒绝。
- **证据**：`backend/models.py` 的 `SuperconductorRecord` 与 Alembic 初始迁移。

## 决策 2：查询参数使用静态白名单

- **决策**：`tc_field` 映射到服务端常量列名，未知值返回 400。
- **理由**：列名不能作为 SQL 参数绑定，直接拼接用户输入会产生 SQL 注入风险。
- **备选方案**：一次返回五字段；载荷更大且会让缓存和空值语义复杂化，当前不采用。
- **证据**：现有 API 每张图独立请求，单字段响应保持向后兼容。

## 决策 3：按用户 ID 保存浏览器本地配置

- **决策**：使用 `scwiki_chart_preferences:v1:<user.id>`，只保存两个枚举字段。
- **理由**：`User.id` 稳定且不泄露邮箱/JWT；项目已有同类键模式。
- **备选方案**：MySQL/Redis 或邮箱键；违反范围或隐私边界，拒绝。
- **证据**：`AuthContext.tsx` 与 `UploadPage.tsx`。

## 决策 4：用采样折线绘制 S 等值线

- **决策**：对每个 S 档位按压力范围采样 `Tc=S×sqrt(39²+P²)`，在同一 Recharts 坐标系中绘制无点折线。
- **理由**：随响应式坐标域自然缩放，避免静态图失真，也避免依赖 Recharts 内部 axis map。
- **备选方案**：静态背景图或 `Customized` 读取内部 scale；前者不准确，后者版本耦合强。
- **证据**：`ChartScatter.tsx` 使用 Recharts 2.15.2 的 `ScatterChart`。

## 决策 5：不新增前端测试框架

- **决策**：纯函数通过 TypeScript 构建检查，后端白名单/缓存键用 Go 表驱动测试，交互用 quickstart 浏览器验收。
- **理由**：仓库没有前端测试依赖，为单一 Feature 引入完整框架超出范围。
- **备选方案**：新增 Vitest/Playwright；后续可独立建设测试基础设施。
- **证据**：`frontend/package.json` 仅含 build 脚本。
