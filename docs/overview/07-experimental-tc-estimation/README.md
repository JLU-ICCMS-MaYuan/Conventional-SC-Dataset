# 实验性 Tc 估算

## 功能边界

该功能根据用户上传的 VASP CONTCAR 和 PDOS 文件提取氢子晶格与费米能级附近态密度，应用固定经验参数计算 Tc 估算值和解释特征。

该能力由代码明确标记为实验页面，不代表经过科学验证的通用预测模型，也不会自动把结果写入主业务数据库。

## 小功能目录

| 小功能 | 职责 | 依赖 |
| --- | --- | --- |
| [CONTCAR/PDOS Tc 估算](contcar-pdos-tc-estimation.md) | 解析文件、计算耦合与返回估算结果 | pymatgen、NumPy |

## 功能组成

```text
实验性 Tc 估算
└── CONTCAR/PDOS Tc 估算
```

## 关联关系

前端 `/tc-predict` 页面提交 CONTCAR 和多个 PDOS 文件，后端验证必要文件并计算结构及电子特征，最后返回 Tc 估算值。该流程与主材料检索和 RAG 数据相互独立。
