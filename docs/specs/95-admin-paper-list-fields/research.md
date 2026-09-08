# 技术研究

## 决策一：展示适配缺失，修复前端边界

- 决策：不删除数据库中合法的 JSON 包装，改管理页解码显示、编码提交。
- 理由：Go models.Paper 的 Authors、KeywordsTags、Methodology 为 *string；paperUpdatesFromBody 原样取值，UpdatePaper 用 GORM Updates 写入，不能依赖后端自动把数组变 JSON。
- 证据：frontend/src/pages/AdminPaperEditPage.tsx 原直接显示字符串或 JSON.stringify 数组；goserver/models/models.go、goserver/handlers/admin.go。
- 备选：后端一律改数组会扩大接口与所有调用者影响，本需求不采用。

## 决策二：沿用控件形式，保留完整标点

- 决策：作者标签；关键词、研究方法每行一项，只按换行切分。
- 理由：UploadTaskEditor 已有相同控件形式，但其 fromLines 同时按逗号拆分；长方法描述和倒置作者名含逗号，管理页不沿用该切分规则。
- 备选：三字段都做标签会使长方法难编辑；直接替换中括号会损坏材料名，均不采用。

## 决策三：原值与编辑缓冲分离

- 决策：共用 PaperEditView 的读取解析，未编辑原字符串/空值不变；多行文本在保存时才去首尾空白和空行。
- 理由：每次敲回车就过滤空项再拼回字符串会吃掉换行。保留原值也避免无编辑保存重写历史数据。
- 兼容范围：已有数组、JSON 文本、普通文本与空值；解析仅一层，失败时保留原文本，不猜测双重编码，不开展批量迁移。
- 备选：每次加载全部归一化再保存会修改未编辑原值，拒绝。

## 决策四：两层验证

页面测试保留真实编辑组件，用 API 替身模拟当前文本列响应和失败；另用 Go 真实 UpdatePaper、GORM 与临时 SQLite 验证文本保存和清空，不将前端请求断言冒充真实持久化。

## 实现核查：作者输入确认

MUI 默认行为在重复作者按 Enter 时可能保留输入。页面显式处理 Enter 和失焦确认，清空待确认姓名；中文输入法选词回车不新增标签，完成选词后的 Enter 才确认。以实际用户交互回归验证，不依赖控件默认行为推断。
