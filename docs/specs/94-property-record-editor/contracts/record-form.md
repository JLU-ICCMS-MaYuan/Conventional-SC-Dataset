# 记录表单契约

## AI 输出与数据传递

现有分段和汇总内部输出的每条实验 Tc 增加：

```json
{
  "result_kind": "experimental",
  "tc_method": "experimental",
  "tc_value_k": 4.2,
  "value_raw": "4.2 K",
  "experimental_conditions": {
    "description": "Resistivity was measured using a four-probe setup at zero applied field."
  }
}
```

缺失方向不补写。两条 Tc 各自携带条件，汇总不得仅因为同材料状态/同方法而合并。
既有转换生成 measured_tc 记录，把实验条件对象原样传递到 payload；
正式草稿 API 仍只使用 property_modules，不新增 tc_results 公共字段。

## 人工输入与校验

实验条件显示一个多行输入框，绑定 payload.experimental_conditions.description。
description 存在时必须是字符串；不要求六个方面齐全或单位数值化。错误定位到该字段。
老对象未编辑时不变，编辑后保留旧字段并更新 description；只读态禁用输入。

## 记录折叠

记录标题、下拉选项与只读标签不显示 vN，内部版本不变。
每条记录独立切换、支持 Enter/Space，折叠不调用数据 onChange。
默认展开，复制/新增记录展开；既有记录的状态随稳定键保留。
收起时显示结果摘要及服务端校验/定义加载错误提示。模块层原有折叠继续可用。
