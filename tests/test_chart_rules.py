from types import SimpleNamespace

from backend.chart_rules import (
    include_in_tc_pressure_chart,
    include_in_tc_year_chart,
    representative_tc,
)


def test_representative_tc_prefers_experimental_then_highest_fidelity_theory():
    record = SimpleNamespace(
        experimental_tc=None,
        anisotropic_eliashberg_tc=280,
        isotropic_eliashberg_tc=260,
        allen_dynes_tc=270,
        mcmillan_tc=250,
    )
    assert representative_tc(record) == 280


def test_pressure_chart_requires_show_in_chart_pressure_and_tc():
    record = SimpleNamespace(show_in_chart=True, pressure_gpa=200, allen_dynes_tc=270, paper_id=None)
    assert include_in_tc_pressure_chart(record) is True

    hidden = SimpleNamespace(show_in_chart=False, pressure_gpa=200, allen_dynes_tc=270, paper_id=None)
    no_pressure = SimpleNamespace(show_in_chart=True, pressure_gpa=None, allen_dynes_tc=270, paper_id=None)
    no_tc = SimpleNamespace(show_in_chart=True, pressure_gpa=200, allen_dynes_tc=None, paper_id=None)
    assert include_in_tc_pressure_chart(hidden) is False
    assert include_in_tc_pressure_chart(no_pressure) is False
    assert include_in_tc_pressure_chart(no_tc) is False


def test_year_chart_requires_paper_id():
    database_record = SimpleNamespace(show_in_chart=True, pressure_gpa=200, allen_dynes_tc=270, paper_id=None)
    paper_record = SimpleNamespace(show_in_chart=True, pressure_gpa=200, allen_dynes_tc=270, paper_id=1)
    assert include_in_tc_year_chart(database_record) is False
    assert include_in_tc_year_chart(paper_record) is True
