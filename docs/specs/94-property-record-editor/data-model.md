# 数据模型

不新增表或列。实验条件仍属于本条 property_modules[].records[]，并保存到 property_records.payload_json。

| 字段 | 含义与约束 |
| --- | --- |
| definition_key / definition_version | 保留原始绑定；版本仅从普通标题隐藏 |
| payload.experimental_conditions | 测量 Tc 必须包含对象，与 calculation_conditions 互斥 |
| payload.experimental_conditions.description | 可选自由文本；空字符串有效，非字符串提交应定位报错 |
| 旧六字段及 extensions | 老记录原始信息，展示适配后保留；新文本不重复生成这些字段 |
| record_key | 稳定记录身份；折叠以此绑定，复制生成新键 |

无 description 的历史对象只在读取界面时转换，不在数据库自动改写。
有 description（包括空字符串）时以其为当前显示与编辑文本。
折叠状态只存 React 本地状态，不写入 payload、导出文件或服务器。
