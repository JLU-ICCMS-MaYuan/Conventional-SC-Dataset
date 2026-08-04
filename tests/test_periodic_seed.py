from backend.scripts.init_db import seed_periodic_table_elements
from backend.models import PeriodicTableElement


def test_seed_periodic_table_elements_is_idempotent(db_session):
    seed_periodic_table_elements(db_session)
    seed_periodic_table_elements(db_session)

    assert db_session.query(PeriodicTableElement).count() == 118
    hydrogen = db_session.query(PeriodicTableElement).filter_by(symbol="H").one()
    assert hydrogen.atomic_number == 1
    assert hydrogen.english_name == "Hydrogen"
    assert hydrogen.chinese_name == "氢"
