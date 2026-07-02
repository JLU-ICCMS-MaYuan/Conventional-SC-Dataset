from backend import crud, models
from backend.api.papers import get_tc_pressure_chart_data, get_tc_year_chart_data, get_user_ranking


def _user(db_session, email, name):
    item = models.User(
        email=email,
        password_hash="!",
        real_name=name,
        role="user",
        is_approved=True,
        is_email_verified=True,
    )
    db_session.add(item)
    db_session.flush()
    return item


def _paper(db_session, user, title, year=2024):
    item = models.Paper(
        title=title,
        year=year,
        authors=[user.real_name],
        uploaded_by_user_id=user.id,
        review_status="approved",
    )
    db_session.add(item)
    db_session.flush()
    return item


def test_user_ranking_orders_researcher_contributions(db_session):
    first = _user(db_session, "first@example.com", "First Researcher")
    second = _user(db_session, "second@example.com", "Second Researcher")
    _paper(db_session, first, "A")
    _paper(db_session, second, "B")
    _paper(db_session, second, "C")
    db_session.commit()

    ranking = get_user_ranking(db_session)

    assert ranking[:2] == [
        {"name": "Second Researcher", "count": 2},
        {"name": "First Researcher", "count": 1},
    ]


def test_chart_metrics_include_only_visible_community_records(db_session):
    user = _user(db_session, "chart@example.com", "Chart Researcher")
    paper = _paper(db_session, user, "Chart Paper", year=2025)
    superconductor = crud.get_or_create_superconductor(db_session, "LaH10")
    visible = models.SuperconductorRecord(
        superconductor_id=superconductor.id,
        paper_id=paper.id,
        source_label="paper",
        pressure_gpa=200.0,
        allen_dynes_tc=250.0,
        show_in_chart=True,
        article_type="t",
        superconductor_type="hydride",
    )
    hidden = models.SuperconductorRecord(
        superconductor_id=superconductor.id,
        paper_id=paper.id,
        source_label="paper",
        pressure_gpa=100.0,
        allen_dynes_tc=120.0,
        show_in_chart=False,
        article_type="t",
    )
    db_session.add_all([visible, hidden])
    db_session.commit()

    pressure_points = get_tc_pressure_chart_data(db_session)
    year_points = get_tc_year_chart_data(db_session)

    assert pressure_points == [
        {
            "x": 200.0,
            "y": 250.0,
            "type": "theoretical",
            "year": 2025,
            "label": "LaH10",
            "sc_type": "hydride",
            "formula": "LaH10",
            "space_group": None,
            "source_label": "paper",
        }
    ]
    assert year_points == [
        {
            "x": 2025,
            "y": 250.0,
            "formula": "LaH10",
            "doi": None,
            "source_label": "paper",
        }
    ]
