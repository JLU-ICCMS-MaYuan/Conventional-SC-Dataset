# 实施任务：社区图表数据源迁移到条件化模型，并恢复背景分区与家族筛选

**输入**：[spec.md](spec.md)、[plan.md](plan.md)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：后端数据源迁移

**目的**：让图表查询建立在条件化模型上，并让 schema 漂移无法再被静默吞掉。

- [x] T001 [US1] 在 `goserver/handlers/stats.go` 把 `chartTcColumns` 的映射目标从 `sr.<列名>` 改为 `tc_results.tc_method` 取值（`experimental_tc` → `experimental` 等），保持对外白名单与默认值不变
- [x] T002 [US1] 新增 `chartApprovedJoin` 常量：`tc_results` JOIN `material_states` JOIN `superconductors` JOIN `papers`（含 `review_status = 'approved'` 与 `paper_revision = content_revision`），LEFT JOIN `material_families`
- [x] T003 [US1] 新增 `chartTcValueExpr` 常量 `COALESCE(t.tc_value_k, (t.tc_min_k + t.tc_max_k) / 2)`，让只有区间的条目按中点上图
- [x] T004 [US1] 重写 `TcPressureChart`：改用新 JOIN、按 `tc_method` 参数化过滤、输出 `family_id`/`family_name`
- [x] T005 [US1] 重写 `TcYearChart`：同上，压强字段改为可空指针（年份图允许无压强）
- [x] T006 [US1] 新增 `chartResultType`，把 `result_kind` 归一到实验/计算，取代已删除的 `article_type='e'` 判定
- [x] T007 [US1] 两处 `Raw(...).Scan(&rows)` 加 `.Error` 检查，失败时 `log.Printf` 并返回 HTTP 503，且不写缓存
- [x] T008 [US1] 新增 `chartFamilyID` / `chartFamilyName` 处理 NULL 家族，回落到 `family_id = 0` 的「其他」
- [x] T009 [US1] 修正家族列扫描：直接声明在两个 row 结构体上，不用匿名嵌入（GORM `Scan` 不填充嵌入字段，否则家族恒 NULL）
- [x] T010 [US1] `go build ./...` 通过

## 阶段 2：前端视觉编码

**目的**：分类维度从硬编码 7 类改为动态材料家族目录，且颜色循环撞色时仍可区分。

- [x] T011 [US3] 重写 `frontend/src/lib/scatterConfig.ts`：删除 `SC_TYPE_CONFIG`/`EXP_COLOR`/`THEORY_COLOR`/`getPointColor`，改为 `buildFamilyStyles`（7 符号 × 8 色按目录顺序确定性分配）+ `familyStyleOf`
- [x] T012 [US3] 在同文件定义 `UNCLASSIFIED_FAMILY_ID = 0` 与「其他」固定档位，不参与循环分配
- [x] T013 [US2] 品质因子公式与档位下沉到 `scatterConfig.ts`（`QUALITY_FACTOR_REFERENCE_TC`、`QUALITY_FACTOR_LEVELS`、`qualityFactorTc`），等值线与色带共用同一实现
- [x] T014 [US2] 定义 `QUALITY_FACTOR_BAND_COLORS`（6 区间）与空数据固定坐标域 `EMPTY_PRESSURE_DOMAIN` / `EMPTY_TC_DOMAIN` / `EMPTY_YEAR_DOMAIN`
- [x] T015 [US3] 重写 `frontend/src/components/ChartScatter.tsx` 的 props 与 series 构建：按 (家族 × 实验/计算) 分组，家族定形状与描边色，实验/计算定实心/空心
- [x] T016 [US3] Tooltip 增加「材料家族」一行；图例改为家族可点击切换，标注「实验（实心）」「计算（空心）」

## 阶段 3：背景分区与空数据渲染

**目的**：没有数据点时也要看到坐标系与品质因子区域划分。

- [x] T017 [US2] 在 `ChartScatter.tsx` 新增 `QualityFactorBands`，用 recharts `Customized` 取内部比例尺，在相邻等值线之间画 `<polygon>` 色带（`ReferenceArea` 只能画轴对齐矩形，跟不了曲线）
- [x] T018 [US2] 色带置于 `CartesianGrid` 之前，避免盖住刻度线；边界按显示域裁剪
- [x] T019 [US2] 坐标轴改为必填 `xDomain`/`yDomain` 并加 `allowDataOverflow`，保证空数据时坐标系照常渲染
- [x] T020 [US2] 空数据时在图内绝对定位提示（`pointerEvents: none`），不隐藏图表本体
- [x] T021 [US2] 修复 `ReferenceLine` 被 React Fragment 包裹导致 77 K / 300 K 参考线不显示——recharts 按子元素类型分派渲染，改为并列条件渲染
- [x] T022 [US2] `share.tsx` 删除 `pressureData.length === 0` / `yearData.length === 0` 早退分支，改为恒渲染 `ChartScatter` 并传 `emptyHint`
- [x] T023 [US2] 年份图不传 `qualityFactorContours`（S 依赖压强，年份轴上无物理意义），但保留参考线

## 阶段 4：家族多选组合

**目的**：默认显示全部，用户可把多种超导体组合显示在一张图里。

- [x] T024 [US3] `share.tsx` 加载 `/api/classification-catalogs`（复用 `lib/classifications.ts` 的 `loadClassificationCatalogs`），失败时退化为仅「其他」档位
- [x] T025 [US3] 用 `FamilySelection = number[] | null` 表示选择，`null` 展开为目录全集，使新增家族自动可见
- [x] T026 [US3] 新增 `renderFamilySelector`：MUI 多选 + 勾选框，全选时 `renderValue` 显示「全部」；带 `labelId` 保证可访问名
- [x] T027 [US3] `toggleFamily` 让图例点击与多选下拉共享同一份状态，双向同步
- [x] T028 [US3] `frontend/src/lib/chartPreferences.ts` 提到 v2：键名 `scwiki_chart_preferences:v2:<id>`，新增 `pressureFamilies`/`yearFamilies` 与 `isFamilySelection` 校验；全选存 `null`
- [x] T029 [US3] 「恢复默认」一并复位家族选择
- [x] T030 [US3] `frontend/src/components/ChartGroupEditor.tsx` 删除 `SC_TYPE_OPTIONS`/`SC_TYPE_LABEL_MAP`，改用目录；「超导类型」下拉改为「材料家族」，表头「类型」改为「材料家族」
- [x] T031 [US3] 修正 `ChartGroupEditor` 把 `state_kind`（theoretical/experimental/mixed/unknown）误当分类维度：改取 `material_state.material_family`
- [x] T032 [US3] `share.tsx` 的 `buildGroupPoints` 从 `type ?? custom_type` 解析家族 id（沿用既有列，不加表结构）
- [x] T033 `tsc --noEmit` 通过

## 阶段 5：测试

- [x] T034 改写 `tests/07_.../test_issue30_tc_chart_preferences.py::test_go_stats_queries_enforce_public_record_boundaries`：旧表断言 → 新 JOIN 链 + approved + revision 约束
- [x] T035 新增 `test_go_stats_maps_tc_field_to_tc_method_rows`、`test_go_stats_surfaces_query_errors_instead_of_empty_results`
- [x] T036 改写 `test_experiment_and_calculation_do_not_rely_on_color_alone` 断言新的形状+实心/空心双通道编码
- [x] T037 新增 `test_empty_data_still_renders_axes_and_background`、`test_quality_factor_bands_shade_regions_between_contours`、`test_family_dimension_is_dynamic_and_multi_selectable`、`test_family_selection_defaults_to_all_and_validates_stored_shape`
- [x] T038 `test_pickard_quality_factor_formula_and_reference_lines` 跟随公式下沉到 `scatterConfig.ts`
- [x] T039 `test_frontend_preferences_are_versioned_validated_and_user_scoped` 更新为 v2
- [x] T040 新增 `tests/07_researcher_community_forum/community-charts.test.tsx`（9 项）：空数据坐标轴/色带/参考线/图内提示、家族图例与多选、Hg 点上图、取消家族后背景仍在
- [x] T041 `vitest.config.ts` 的 `include` 加入 `tests/07_researcher_community_forum/**/*.test.tsx`
- [x] T042 在测试中 stub `ResizeObserver` 与 `getBoundingClientRect`——jsdom 下 `ResponsiveContainer` 量到 0 尺寸会完全不出图
- [x] T043 `goserver/handlers/stats_test.go` 扩充：`tc_field → tc_method` 映射、`chartResultType`、家族 NULL 回落、CHECK 约束子集、禁止嵌入结构体承载家族列
- [x] T044 删除孤儿测试 `tests/test_chart_rules.py`（依赖 `4e04034` 已删除的 `backend/services/chart_rules.py`，import 即失败）

## 阶段 6：验证与文档

- [x] T045 `bash scripts/run-tests.sh go` 通过
- [x] T046 `bash scripts/run-tests.sh` 后端 116 项通过
- [x] T047 `pytest tests/07_researcher_community_forum` 25 项通过
- [x] T048 前端 vitest：`community-charts.test.tsx` 9 项通过（`tests/07_researcher_community_forum/news-feed.test.tsx` 1 项失败为既有问题，与本次改动无关）
- [x] T049 重启 goserver 并清 `chart:*` 缓存后 curl 实测：两个接口返回 Hg 数据点，`family_id = 8`、`family_name = 单质超导体`
- [x] T050 curl 验证 `allen_dynes_tc`/`mcmillan_tc` 返回 `[]`（该方法无数据），非法字段返回 HTTP 400
- [x] T051 重写 `docs/overview/03_.../tc-history-and-pressure-charts.md`（原文仍在描述已删除的 `superconductor_records`），补记 `show_in_chart` 能力缺失与三种 `tc_method` 不上图两个已知缺口

---

# B 组任务

**Spec**：US4–US6、FR-014…FR-025、SC-001…SC-006

**Research**：R7–R13

B 组为纯前端改动，无后端文件涉及。

## 阶段 7：常量与标签（Foundational，无 UI 依赖）

**目的**：先把被多处引用的常量与标签改到位，避免后续阶段反复改同一文件。

- [x] T052 [US6] 在 `frontend/src/lib/scatterConfig.ts` 把 `EMPTY_TC_DOMAIN` 由 `[0, 300]` 改为 `[0, 500]`（FR-016、R11），并更新其注释说明该值被两图共用
- [x] T053 [US6] 在 `frontend/src/lib/scatterConfig.ts` 把 `QUALITY_FACTOR_BAND_COLORS` 定为「高 S 暖色、低 S 冷色」的 6 档红→黄→绿色阶（FR-021、R9）
- [x] T054 [P] [US6] 在 `frontend/src/lib/scatterConfig.ts` 新增年份图温度渐变常量（低温蓝、高温红的起止色与不透明度）（FR-023、R10）
- [x] T055 [P] [US6] 在 `frontend/src/lib/chartPreferences.ts` 把 `TC_FIELD_LABELS` 五个值改为英文（FR-025、R13），键名 `TC_FIELDS` 不动

## 阶段 8：布局对齐（US4、US5）

**目的**：让两图在任何选择状态下对齐。高度与宽度必须一起改（R7 与 R8 耦合），否则长文本在固定高度容器内被裁切。

**独立验收**：在选中 1/3/6/9 项四种状态下，两图绘图区顶边与卡片底边不发生相对偏移。

- [x] T056 [US5] 在 `frontend/src/pages/share.tsx` 的 `renderFamilySelector` 把 `minWidth: 220` 改为固定 `width`（≤ 200 px）（FR-017）
- [x] T057 [US5] 在 `frontend/src/pages/share.tsx` 的 `renderFamilySelector` 的 `renderValue` 增加折叠摘要分支：全选返回「全部」、空选返回「未选择」、文本过长返回 `已选 N 项`（FR-018、R8）
- [x] T058 [US4] 在 `frontend/src/pages/share.tsx` 给两图的控件区容器设固定高度，取值需容纳单行控件且不裁切（FR-014、R7）
- [x] T059 [US4] 在 `frontend/src/components/ChartScatter.tsx` 给图例区容器设固定高度，容纳最大家族数时的行数（FR-015、R7）
- [x] T060 [US6] 在 `frontend/src/components/ChartScatter.tsx` 把「当前纵轴」提示前缀改为英文（FR-025）

## 阶段 9：移除组合选择器（US6）

**目的**：移除社区页的 chart group 入口并收敛数据点样式。保留 `/api/chart-groups`、`ChartGroupEditor` 组件与 `AdminPage` 入口。

**独立验收**：`/share` 渲染结果与源码均无组合选择器；管理页 `ChartGroupEditor` 仍可打开。

- [x] T061 [US6] 在 `frontend/src/pages/share.tsx` 删除 `renderGroupSelector` 及其两处调用（FR-019）
- [x] T062 [US6] 在 `frontend/src/pages/share.tsx` 删除组合相关状态与函数：`groups`、`chart1`、`chart2`、`editorOpen`、`editingGroupId`、`loadAllGroups`、`refreshGroups`、`buildGroupPoints`、`isAdmin`，以及 `ChartGroupEditor` 的 import 与 JSX 引用（FR-019、R12）
- [x] T063 [US6] 在 `frontend/src/pages/share.tsx` 清理因上一步产生的无用 import：`Edit`、`ContentCopy`、`FileDownload` 图标与 `Tooltip`（若不再使用）
- [x] T064 [US6] 在 `frontend/src/pages/share.tsx` 把 `chart1Data` / `chart2Data` 简化为只含 `buildBgPoints` 结果，并移除 `showBackground` 传参（FR-020）
- [x] T065 [US6] 在 `frontend/src/components/ChartScatter.tsx` 移除 `showBackground` prop 与 `bgSeries`/`groupSeries` 双分支，收敛为单一前景 series（FR-020、R12）
- [x] T066 [US6] 在 `frontend/src/components/ChartScatter.tsx` 与 `frontend/src/pages/share.tsx` 的 `DataPoint` 接口移除 `isInGroup`、`isCustom` 字段及其赋值（FR-020）
- [x] T067 [US6] 确认 `BACKGROUND_OPACITY` 在 `frontend/src/lib/scatterConfig.ts` 是否仍被引用；若已无引用则删除该常量（YAGNI）

## 阶段 10：背景填充（US6）

**目的**：压力图换配色，年份图加温度渐变，两图各加背景色图例。

**独立验收**：压力图 6 档暖冷色带 + S 图例；年份图蓝红渐变 + 温度图例。

- [x] T068 [US6] 在 `frontend/src/components/ChartScatter.tsx` 新增 `TemperatureBands`：在 `Customized` 内用 `<defs><linearGradient>` 画覆盖绘图区的矩形，沿 Y 轴由蓝到红（FR-023、R10）
- [x] T069 [US6] 在 `frontend/src/components/ChartScatter.tsx` 新增控制温度渐变的 prop，并在 `frontend/src/pages/share.tsx` 仅为年份图开启（FR-023）
- [x] T070 [US6] 在 `frontend/src/components/ChartScatter.tsx` 为年份图增加温度色条图例（FR-024）
- [x] T071 [US6] 在 `frontend/src/components/ChartScatter.tsx` 确认品质因子等值线为绿色虚线、参考线为深红点划线，不符则调整（FR-022）

## 阶段 11：测试

- [x] T072 [US4] 在 `tests/07_researcher_community_forum/community-charts.test.tsx` 新增测试：在选中 1/3/6/9 项四种状态下，两图绘图区顶边坐标一致（SC-001）
- [x] T073 [US5] 在 `tests/07_researcher_community_forum/community-charts.test.tsx` 新增测试：家族选择框宽度不随选中项数量变化，两图一致（SC-002）
- [x] T074 [P] [US5] 在 `tests/07_researcher_community_forum/community-charts.test.tsx` 新增测试：超长选择显示 `已选 N 项`，全选显示「全部」，空选显示「未选择」（FR-018）
- [x] T075 [P] [US6] 在 `tests/07_researcher_community_forum/community-charts.test.tsx` 新增测试：页面无「组合」下拉与编辑/复制/导出/新建按钮（SC-003）
- [x] T076 [P] [US6] 在 `tests/07_researcher_community_forum/community-charts.test.tsx` 新增测试：两图纵轴上界为 500（SC-004）
- [x] T077 [P] [US6] 在 `tests/07_researcher_community_forum/community-charts.test.tsx` 新增测试：Tc 字段五个选项为英文且不含中日韩字符（SC-005）
- [x] T078 [P] [US6] 在 `tests/07_researcher_community_forum/community-charts.test.tsx` 新增测试：年份图存在 `linearGradient` 渐变填充，两图各有背景色图例（SC-006）
- [x] T079 在 `tests/07_researcher_community_forum/community-charts.test.tsx` 更新既有 9 项中受 B 组影响的断言（组合下拉相关描述、纵轴域）
- [x] T080 在 `tests/07_researcher_community_forum/test_issue30_tc_chart_preferences.py` 同步受影响断言：`EMPTY_TC_DOMAIN` 值、`TC_FIELD_LABELS` 英文、`showBackground` 移除、`qualityFactorContours` 计数

## 阶段 12：验证与文档

- [x] T081 `cd frontend && ./node_modules/.bin/tsc --noEmit -p tsconfig.json` 通过
- [x] T082 `cd frontend && ./node_modules/.bin/vitest run --config ../vitest.config.ts` 通过（`tests/07_researcher_community_forum/news-feed.test.tsx` 1 项既有失败除外）
- [x] T083 `source scripts/lib-local.sh && "$PY_BIN/python" -m pytest tests/07_researcher_community_forum -q` 通过
- [x] T084 `bash scripts/run-tests.sh go` 与 `bash scripts/run-tests.sh` 通过，确认后端无回退
- [x] T085 按 `quickstart.md` 场景 1–6 逐项浏览器验收，记录实际结果
- [x] T086 回写 `docs/overview/03_Superconductivity_Data_Search_and_Database_Discovery/tc-history-and-pressure-charts.md`：纵轴 0–500 K、配色语义、组合入口移除、Tc 标签英文、年份图温度渐变

## 依赖与并行

- 阶段 7 是 Foundational：T052–T055 的常量被后续所有阶段引用，必须先完成。
- 阶段 8 与阶段 9 都改 `share.tsx`，**必须串行**（同文件）。
- 阶段 9 与阶段 10 都改 `ChartScatter.tsx`，**必须串行**（同文件）。
- 阶段 11 的 T074–T078 标 `[P]`：同为新增独立 `it` 块，互不依赖，但与 T072/T073 同文件，实际写入需串行。
- 阶段 12 依赖全部实现阶段完成。

## MVP 范围

US4（对齐）+ US5（固定宽度）构成 MVP：这两项解决当前最影响读图的缺陷。US6 的六个子项（移除组合、配色、英文、渐变、纵轴、图例）为体验增强，可独立后续交付。
