from backend.services.space_groups import all_space_groups, lookup_number


def test_table_contains_exactly_the_230_space_groups():
    groups = all_space_groups()

    assert len(groups) == 230
    assert [entry["number"] for entry in groups] == list(range(1, 231))
    assert all(set(entry) == {"number", "symbol"} for entry in groups)


def test_international_symbols_map_to_canonical_numbers():
    expected = {
        "Fm-3m": 225,
        "I4/mmm": 139,
        "P6_3/mmc": 194,
        "Fd-3m": 227,
        "P-3m1": 164,
        "P1": 1,
    }

    for symbol, number in expected.items():
        assert lookup_number(symbol) == number


def test_lookup_strips_surrounding_whitespace():
    assert lookup_number("  Fm-3m\t") == 225


def test_lookup_rejects_unknown_symbols():
    assert lookup_number("P-3m") is None
    assert lookup_number("") is None
