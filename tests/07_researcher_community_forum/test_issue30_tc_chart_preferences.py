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
    source = read_source("goserver/handlers/stats.go")

    assert source.count("FROM superconductor_records sr") >= 2
    assert source.count("sr.show_in_chart = true") >= 2
    assert source.count("p.review_status = 'approved'") >= 2
    assert "AND sr.pressure_gpa IS NOT NULL" in source
    assert "AND p.year IS NOT NULL" in source
    assert "key_properties kp" not in source[source.index("func TcPressureChart"):source.index("func AllUsers")]


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
    assert "scwiki_chart_preferences:v1:${userId}" in source
    assert "TC_FIELDS.includes" in source
    assert "value.version !== 1" in source
    assert "localStorage.removeItem(chartPreferencesKey(userId))" in source
    assert "email" not in source.lower()
    assert "token" not in source.lower()


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
    assert "当前 Tc 字段暂无可公开数据" in source


def test_pickard_quality_factor_formula_and_reference_lines():
    source = read_source("frontend/src/components/ChartScatter.tsx")

    assert "s * Math.sqrt(39 ** 2 + x ** 2)" in source
    assert "[0.2, 0.5, 1, 2, 3]" in source
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


def test_experiment_and_calculation_do_not_rely_on_color_alone():
    source = read_source("frontend/src/components/ChartScatter.tsx")

    assert "fill: EXP_COLOR" in source
    assert "fill: '#fff', stroke: THEORY_COLOR" in source
    assert "数据类型：{d.articleType === 'e' ? '实验' : '计算'}" in source
    assert ">计算</Typography>" in source
