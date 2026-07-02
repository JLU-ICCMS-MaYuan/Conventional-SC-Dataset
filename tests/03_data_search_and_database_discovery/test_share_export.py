from types import SimpleNamespace

from backend.api.papers import _build_ris_content, _papers_response


def _paper():
    superconductor = SimpleNamespace(
        chemical_formula="LaH10",
        elements_list=["H", "La"],
    )
    record = SimpleNamespace(
        id=1,
        superconductor_id=1,
        superconductor=superconductor,
        source_label="example",
        pressure_gpa=170,
        space_group_symbol="Fm-3m",
        space_group_number=225,
        crystal_structure="hydride",
        thermodynamically_stable=True,
        dynamically_stable=True,
        energy_above_hull=0,
        mcmillan_tc=None,
        allen_dynes_tc=None,
        isotropic_eliashberg_tc=None,
        anisotropic_eliashberg_tc=None,
        experimental_tc=250,
        article_type="experimental",
        superconductor_type="hydride",
        lambda_value=None,
        omega_log=None,
        n_ef_total=None,
        element_n_ef=None,
        pseudopotential_type=None,
        pseudopotential_name=None,
        exchange_correlation_functional=None,
        calculation_code=None,
        k_grid=None,
        q_grid=None,
        energy_cutoff_value=None,
        energy_cutoff_unit=None,
        show_in_chart=True,
        s_factor=None,
        method=None,
        note=None,
    )
    return SimpleNamespace(
        id=1,
        doi="10.0000/example",
        title="Example superconductor",
        authors=["A. Researcher"],
        journal="SC Journal",
        volume="1",
        pages="1-2",
        year=2026,
        abstract=None,
        review_status="approved",
        review_comment=None,
        reviewed_by_user_id=None,
        reviewed_at=None,
        uploaded_by_user_id=None,
        created_at=None,
        updated_at=None,
        records=[record],
    )


def test_share_export_json_includes_records():
    response = _papers_response([_paper()], "json", "sc-wiki-test")
    body = response.body.decode("utf-8")

    assert response.media_type == "application/json"
    assert "sc-wiki-test.json" in response.headers["content-disposition"]
    assert '"chemical_formula": "LaH10"' in body
    assert '"records"' in body


def test_share_export_ris_includes_citation_and_formula():
    content = _build_ris_content([_paper()])

    assert "TY  - JOUR" in content
    assert "DO  - 10.0000/example" in content
    assert "N1  - 化学式 LaH10" in content
