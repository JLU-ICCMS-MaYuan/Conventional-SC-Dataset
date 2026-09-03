# 契约：AI 生成字段英文输出

**GitHub Issue**：[#85](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/85)

## 服务端语言验证器

提供单一的、纯函数的字段策略和验证入口，供分段结果、汇总草稿、浏览器草稿保存及提交前复用。

- 输入：结构化候选或草稿、作用域（`chunk` / `draft` / `submit`）。
- 输出：通过的值，或包含 JSON 路径、规则名和可展示消息的错误列表。
- 规则：只检测“必须英文”的字段是否包含中日韩 Unicode 字符；不对事实字段执行该检测。

错误示例：

```json
{
  "detail": {
    "code": "generated_field_must_be_english",
    "path": "paper.methodology[0]",
    "message": "AI 生成字段必须使用英文；请重新生成或改为英文。"
  }
}
```

草稿保存和提交返回 400。后台分段或汇总处理记录同一错误码并进入现有失败/重试状态，不能把违规内容写入分段清单或 `partial_draft`。

## 兼容性

接口 JSON 键不改；只收紧其文本值的语言规则。`quote` 和元数据不受影响，因而不破坏中文论文原文展示。
