import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TC_FIELDS = (
    "experimental_tc",
    "anisotropic_eliashberg_tc",
    "isotropic_eliashberg_tc",
    "allen_dynes_tc",
    "mcmillan_tc",
)


def read_source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_go_stats_api_uses_a_closed_tc_field_whitelist():
    source = read_source("goserver/handlers/stats.go")

    whitelist_match = re.search(
        r"var chartTcColumns = map\[string\]string\{(?P<body>.*?)\n\}",
        source,
        re.DOTALL,
    )
    assert whitelist_match, "Go 图表 API 必须声明静态 Tc 字段白名单"
    whitelist = whitelist_match.group("body")
    assert all(f'"{field}":' in whitelist for field in TC_FIELDS)
    assert 'defaultTcField = "experimental_tc"' in source
    assert 'c.JSON(http.StatusBadRequest, gin.H{"error": "不支持的 Tc 字段"})' in source


def test_go_stats_queries_enforce_public_record_boundaries():
    """图表数据边界必须建立在条件化模型上。

    旧断言锁定 superconductor_records，而该表在 20260821_0008 迁移里已删除，
    查询恒返回空数组却无人察觉。这里改为锁定新的 JOIN 链与版本约束。
    """
    source = read_source("goserver/handlers/stats.go")

    # 已删除的表不得再被查询（注释里作为历史说明出现是允许的）
    assert "FROM superconductor_records" not in source
    assert "JOIN superconductor_records" not in source
    assert "FROM key_properties" not in source
    assert "JOIN key_properties" not in source

    assert "FROM tc_results t" in source
    assert "JOIN material_states ms ON ms.id = t.material_state_id" in source
    assert "JOIN superconductors sc ON sc.id = ms.superconductor_id" in source
    assert "FROM paper_material_families pmf" in source
    assert "material_states ms ON ms.id = t.material_state_id" in source
    assert "JOIN paper_material_families" not in source

    # 只公开审核通过、且属于已批准那一版内容的数据
    assert "p.review_status = 'approved'" in source
    assert "t.paper_revision = p.content_revision" in source

    # 两张图各自的必需坐标
    assert "AND ms.pressure_value_gpa IS NOT NULL" in source
    assert "AND p.year IS NOT NULL" in source


def test_go_stats_maps_tc_field_to_tc_method_rows():
    """新模型下 Tc 是 tc_results 的行，tc_field 必须映射到 tc_method 取值。"""
    source = read_source("goserver/handlers/stats.go")

    for method in (
        "experimental", "anisotropic_eliashberg", "isotropic_eliashberg",
        "allen_dynes", "mcmillan",
    ):
        assert f'"{method}"' in source
    assert "t.tc_method = ?" in source
    # 只有区间没有单值的条目取中点，否则永远上不了图
    assert "COALESCE(t.tc_value_k, (t.tc_min_k + t.tc_max_k) / 2)" in source


def test_go_stats_surfaces_query_errors_instead_of_empty_results():
    """查询失败不得伪装成「暂无数据」，否则 schema 漂移无法被发现。"""
    source = read_source("goserver/handlers/stats.go")

    assert source.count("Scan(&rows).Error; err != nil") >= 2
    assert source.count("http.StatusServiceUnavailable") >= 2
    assert '"error": "图表数据暂不可用"' in source


def test_go_stats_cache_is_separated_by_chart_and_tc_field():
    source = read_source("goserver/handlers/stats.go")

    assert 'fmt.Sprintf("chart:approved:%s:%s", chart, field)' in source
    assert 'chartCacheKey("tc_pressure", tcField)' in source
    assert 'chartCacheKey("tc_year", tcField)' in source
    assert '"tc_field": tcField' in source


def test_frontend_preferences_are_versioned_validated_and_user_scoped():
    source = read_source("frontend/src/lib/chartPreferences.ts")

    assert all(f"'{field}'" in source for field in TC_FIELDS)
    assert "DEFAULT_TC_FIELD: TcField = 'experimental_tc'" in source
    # v2 加入家族多选；键名带版本号，v1 旧值读不到即回落默认
    assert "scwiki_chart_preferences:v2:${userId}" in source
    assert "TC_FIELDS.includes" in source
    assert "value.version !== 2" in source
    assert "localStorage.removeItem(chartPreferencesKey(userId))" in source
    assert "email" not in source.lower()
    assert "token" not in source.lower()


def test_family_selection_defaults_to_all_and_validates_stored_shape():
    source = read_source("frontend/src/lib/chartPreferences.ts")

    # null = 全部，让新增家族自动可见，而不是被旧偏好永久排除
    assert "pressureFamilies: null" in source
    assert "yearFamilies: null" in source
    assert "isFamilySelection" in source


def test_community_page_has_independent_tc_fields_and_no_server_preference_write():
    source = read_source("frontend/src/pages/share.tsx")

    assert "pressureTcField" in source and "yearTcField" in source
    assert "/api/papers/stats/tc-pressure?tc_field=" in source
    assert "/api/papers/stats/tc-year?tc_field=" in source
    assert "readChartPreferences(user.id)" in source
    assert "writeChartPreferences(user.id" in source
    assert "clearChartPreferences(user.id)" in source
    assert "/api/chart-preferences" not in source
    assert "DEFAULT_CHART_PREFERENCES" in source


def test_community_chart_layout_is_responsive_and_states_are_independent():
    source = read_source("frontend/src/pages/share.tsx")

    assert "repeat(2, minmax(0, 1fr))" in source
    assert "gridTemplateColumns: { xs: 'minmax(0, 1fr)', lg:" in source
    assert source.count("minWidth: 0") >= 2
    assert "pressureLoading" in source and "yearLoading" in source
    assert "pressureError" in source and "yearError" in source


def test_empty_data_still_renders_axes_and_background():
    """没有数据点时不得用 Alert 顶掉图表，否则坐标系与品质因子分区都看不到。"""
    source = read_source("frontend/src/pages/share.tsx")

    # 旧的空数据早退分支必须消失
    assert "pressureData.length === 0" not in source
    assert "yearData.length === 0" not in source
    # 空数据用固定坐标域，保证背景分区画得满
    assert "EMPTY_PRESSURE_DOMAIN" in source
    assert "EMPTY_TC_DOMAIN" in source
    assert "EMPTY_YEAR_DOMAIN" in source
    assert "emptyHint=" in source

    chart = read_source("frontend/src/components/ChartScatter.tsx")
    assert "visibleData.length === 0" in chart
    assert "allowDataOverflow" in chart


def test_quality_factor_bands_shade_regions_between_contours():
    """背景分区靠 Customized 在数据空间画多边形：ReferenceArea 只能画轴对齐矩形。"""
    chart = read_source("frontend/src/components/ChartScatter.tsx")
    config = read_source("frontend/src/lib/scatterConfig.ts")

    assert "Customized" in chart
    assert "QualityFactorBands" in chart
    assert "<polygon" in chart
    assert "QUALITY_FACTOR_BAND_COLORS" in config
    # 6 个区间：<0.2 / 0.2–0.5 / 0.5–1 / 1–2 / 2–3 / >3
    assert len(re.findall(r"'#[0-9a-fA-F]{6}'", config[config.index("QUALITY_FACTOR_BAND_COLORS"):])) >= 6

    # 年份图不画品质因子分区（S 依赖压强）
    share = read_source("frontend/src/pages/share.tsx")
    assert share.count("qualityFactorContours") == 1


def test_family_dimension_is_dynamic_and_multi_selectable():
    """分类维度改为 material_families 目录，含用户自建家族；硬编码 7 类不得残留。"""
    config = read_source("frontend/src/lib/scatterConfig.ts")
    share = read_source("frontend/src/pages/share.tsx")

    for legacy in ("hydride", "cuprate", "iron_based", "nickel_based"):
        assert legacy not in config
        assert legacy not in share

    assert "buildFamilyStyles" in config
    assert "loadClassificationCatalogs" in share
    # 多选下拉，默认全部
    assert "multiple" in share
    assert "renderFamilySelector" in share
    assert "'全部'" in share


def test_both_charts_share_one_tc_domain_of_500k():
    """纵轴由两图共用且上界 500 K：不共用的话「对齐」只剩几何意义，无法比对 Tc 高度。"""
    config = read_source("frontend/src/lib/scatterConfig.ts")
    share = read_source("frontend/src/pages/share.tsx")

    assert "EMPTY_TC_DOMAIN: [number, number] = [0, 500]" in config
    # 两图都传同一个常量，而不是各自写字面量
    assert share.count("yDomain={EMPTY_TC_DOMAIN}") == 2


def test_chart_controls_and_legend_have_fixed_size():
    """对齐靠固定尺寸：控件文本长度不得影响图表纵向位置。

    宽度与高度必须同时固定 —— 只固定高度会让长文本在定高容器里被裁切。
    """
    share = read_source("frontend/src/pages/share.tsx")
    chart = read_source("frontend/src/components/ChartScatter.tsx")

    # 控件区定高，且两图都用同一常量
    assert "CHART_CONTROLS_HEIGHT" in share
    assert share.count("height: CHART_CONTROLS_HEIGHT") == 2

    # 家族选择框固定宽度而非 minWidth，且不超过 200 px
    assert "minWidth: 220" not in share
    width_match = re.search(r"FAMILY_SELECTOR_WIDTH = (\d+)", share)
    assert width_match, "家族选择框必须声明固定宽度常量"
    assert int(width_match.group(1)) <= 200
    assert "width: FAMILY_SELECTOR_WIDTH" in share

    # 超长折叠 + 空值提示；displayEmpty 是必需的，否则 MUI 跳过 renderValue
    assert "已选 ${ids.length} 项" in share
    assert "'未选择'" in share
    assert "displayEmpty" in share

    # 图例区定高，否则家族项数变化会把两张卡片底边推错位
    assert "LEGEND_AREA_HEIGHT" in chart
    assert "height: LEGEND_AREA_HEIGHT" in chart


def test_community_page_has_no_chart_group_selector():
    """组合入口已由材料家族多选取代；社区页不得残留组合选择器与其状态。"""
    share = read_source("frontend/src/pages/share.tsx")

    assert "renderGroupSelector" not in share
    assert "ChartGroupEditor" not in share
    assert "/api/chart-groups" not in share
    assert "(无组合)" not in share
    assert "buildGroupPoints" not in share
    assert "showBackground" not in share
    # 组合概念移除后不再区分组合内点与背景点
    assert "isInGroup" not in share
    assert "isCustom" not in share

    chart = read_source("frontend/src/components/ChartScatter.tsx")
    assert "showBackground" not in chart
    assert "isInGroup" not in chart
    assert "BACKGROUND_OPACITY" not in chart

    # 组合功能本身保留：管理端入口不得被一起删掉
    admin = read_source("frontend/src/pages/AdminPage.tsx")
    assert "ChartGroupEditor" in admin


def test_year_chart_fills_temperature_gradient():
    """年份图按纵轴温度着色：边界是水平线，用 linearGradient 而非逐段多边形。"""
    config = read_source("frontend/src/lib/scatterConfig.ts")
    chart = read_source("frontend/src/components/ChartScatter.tsx")
    share = read_source("frontend/src/pages/share.tsx")

    assert "TEMPERATURE_LOW_COLOR" in config
    assert "TEMPERATURE_HIGH_COLOR" in config
    assert "TemperatureBands" in chart
    assert "<linearGradient" in chart
    assert 'url(#tc-temperature-gradient)' in chart

    # 只有年份图开启温度渐变，只有压力图开启品质因子分区
    assert share.count("temperatureBands") == 1
    assert share.count("qualityFactorContours") == 1


def test_tc_field_labels_are_english():
    """Tc 字段标签与纵轴提示用英文；键名属 API 契约，不得改动。"""
    preferences = read_source("frontend/src/lib/chartPreferences.ts")
    chart = read_source("frontend/src/components/ChartScatter.tsx")

    for label in (
        "Experimental Tc", "Anisotropic Eliashberg Tc", "Isotropic Eliashberg Tc",
        "Allen-Dynes Tc", "McMillan Tc",
    ):
        assert f"'{label}'" in preferences

    # 旧中文标签不得残留
    for legacy in ("实验 Tc", "各向异性 Eliashberg Tc", "各向同性 Eliashberg Tc"):
        assert legacy not in preferences

    # 键名不变，否则破坏后端白名单与已存偏好
    assert all(f"'{field}'" in preferences for field in TC_FIELDS)

    assert "Y axis: {tcFieldLabel}" in chart
    assert "当前纵轴" not in chart


def test_pickard_quality_factor_formula_and_reference_lines():
    source = read_source("frontend/src/components/ChartScatter.tsx")
    # 公式与档位下沉到 scatterConfig，等值线与分区共用同一个实现
    config = read_source("frontend/src/lib/scatterConfig.ts")

    assert "QUALITY_FACTOR_REFERENCE_TC = 39" in config
    assert "s * Math.sqrt(QUALITY_FACTOR_REFERENCE_TC ** 2 + pressureGPa ** 2)" in config
    assert "QUALITY_FACTOR_LEVELS: readonly number[] = [0.2, 0.5, 1, 2, 3]" in config

    assert "qualityFactorTc(s, x)" in source
    assert "<ReferenceLine y={77}" in source
    assert "<ReferenceLine y={300}" in source
    assert "<LabelList dataKey=\"sLabel\"" in source
    assert "qualityFactorContours" in source

    # S=1 必须在常压通过 MgB2 基准点 (0 GPa, 39 K)。
    assert math.isclose(math.sqrt(39**2 + 0**2), 39.0, abs_tol=1e-12)
    # 抽样验证曲线反代 S 的误差，覆盖实现所用的压力范围。
    for s in (0.2, 0.5, 1.0, 2.0, 3.0):
        for pressure in (0.0, 50.0, 200.0, 400.0):
            tc = s * math.sqrt(39**2 + pressure**2)
            recovered = tc / math.sqrt(39**2 + pressure**2)
            assert math.isclose(recovered, s, abs_tol=1e-12)


def test_reference_lines_are_not_wrapped_in_fragment():
    """recharts 按子元素类型分派渲染，Fragment 内的 ReferenceLine 不被识别。

    77 K / 300 K 参考线曾因此在两张图上都静默消失。
    """
    source = read_source("frontend/src/components/ChartScatter.tsx")

    for line in ("<ReferenceLine y={77}", "<ReferenceLine y={300}"):
        index = source.index(line)
        # 参考线必须由条件表达式直接返回，前面紧跟 && 而非 Fragment 开标签
        preceding = source[max(0, index - 60):index]
        assert "&&" in preceding
        assert "<>" not in preceding


def test_experiment_and_calculation_do_not_rely_on_color_alone():
    """双通道编码：家族定形状+描边色，实验/计算定实心/空心。

    家族数量可由用户增长，配色必然循环撞色，所以形状必须承担区分职责。
    """
    source = read_source("frontend/src/components/ChartScatter.tsx")

    assert "fill: style.color, stroke: style.color" in source
    assert "fill: '#fff', stroke: style.color" in source
    assert "shape: style.symbol" in source
    assert "数据类型：{d.articleType === 'e' ? '实验' : '计算'}" in source
    assert "实验（实心）" in source
    assert "计算（空心）" in source
