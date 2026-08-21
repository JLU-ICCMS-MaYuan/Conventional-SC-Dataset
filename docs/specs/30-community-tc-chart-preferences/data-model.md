# 数据模型：社区 Tc 双图个人配置与品质因子

## TcField

枚举值：`experimental_tc`、`anisotropic_eliashberg_tc`、`isotropic_eliashberg_tc`、`allen_dynes_tc`、`mcmillan_tc`。默认 `experimental_tc`，未知值无效。

## ChartPreferences

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `version` | `1` | 固定版本，用于拒绝未知结构 |
| `pressureTcField` | `TcField` | 必填，默认实验值 |
| `yearTcField` | `TcField` | 必填，默认实验值 |

生命周期：登录或账号切换时按 `user.id` 加载；有效选择变更时覆盖当前用户键；恢复默认时删除当前键；匿名状态不持久化。

## PublicChartPoint

| 字段 | 含义 |
| --- | --- |
| `x` / `y` | 压力或年份，以及所选 Tc |
| `formula` | 超导体化学式 |
| `sc_type` | 超导体类型 |
| `type` | `experimental` 或 `theoretical` |
| `paper_id` / `doi` / `year` | 论文导航元数据 |
| `tc_field` | 当前响应使用的 Tc 字段 |

准入：`show_in_chart=true`、论文 Approved、所选 Tc 非空；按图表再要求压力或年份。

## QualityFactorContour

派生对象：`{ s: number, points: Array<{x:number,y:number}> }`。不保存。每个点满足 `y=sqrt(39²+x²)×s`，超出显示域的点可裁剪。
