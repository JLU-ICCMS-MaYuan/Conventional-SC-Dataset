from types import SimpleNamespace

from backend.api.papers import _build_ris_content, _papers_response


def _paper():
    superconductor = SimpleNamespace(
        chemical_formula="LaH10",
        elements_list=["H", "La"],
    )
    kp = SimpleNamespace(
        id=1,
        paper_id=1,
        superconductor_id=1,
        superconductor=superconductor,
        material="LaH10",
        name="critical_temperature",
        name_raw="Tc",
        name_note=None,
        value_min=250.0,
        value_max=250.0,
        value_raw=None,
        unit="K",
        pressure_gpa=170,
        temperature_k=None,
        condition_json=None,
        condition_note=None,
        is_primary=True,
        superconductor_type="hydride",
        article_type="e",
        source_label="clean_results",
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
        summary=None,
        paper_type="experimental",
        keywords_tags=None,
        methodology=None,
        key_finding=None,
        rationale=None,
        review_status="approved",
        review_comment=None,
        reviewed_by_user_id=None,
        reviewed_at=None,
        uploaded_by_user_id=None,
        created_at=None,
        updated_at=None,
        key_properties=[kp],
    )


def test_share_export_json_includes_key_properties():
    response = _papers_response([_paper()], "json", "sc-wiki-test")
    body = response.body.decode("utf-8")

    assert response.media_type == "application/json"
    assert "sc-wiki-test.json" in response.headers["content-disposition"]
    assert '"chemical_formula": "LaH10"' in body
    assert '"key_properties"' in body
    assert '"critical_temperature"' in body


def test_share_export_ris_includes_citation_and_formula():
    content = _build_ris_content([_paper()])

    assert "TY  - JOUR" in content
    assert "DO  - 10.0000/example" in content
    assert "N1  - 化学式 LaH10" in content
