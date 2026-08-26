from backend.services.space_groups import (
    CRYSTAL_SYSTEMS,
    all_space_groups,
    crystal_system_for_number,
    lookup_number,
    numbers_for_crystal_system,
)


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


def test_crystal_systems_lists_the_seven_systems_in_order_plus_unknown():
    assert CRYSTAL_SYSTEMS == (
        "triclinic",
        "monoclinic",
        "orthorhombic",
        "tetragonal",
        "trigonal",
        "hexagonal",
        "cubic",
        "unknown",
    )


def test_crystal_system_for_number_covers_all_range_boundaries():
    expected = {
        1: "triclinic",
        2: "triclinic",
        3: "monoclinic",
        15: "monoclinic",
        16: "orthorhombic",
        74: "orthorhombic",
        75: "tetragonal",
        142: "tetragonal",
        143: "trigonal",
        167: "trigonal",
        168: "hexagonal",
        194: "hexagonal",
        195: "cubic",
        227: "cubic",
        230: "cubic",
    }

    for number, system in expected.items():
        assert crystal_system_for_number(number) == system


def test_crystal_system_for_number_rejects_out_of_range_and_invalid_input():
    assert crystal_system_for_number(0) is None
    assert crystal_system_for_number(231) is None
    assert crystal_system_for_number("abc") is None
    assert crystal_system_for_number(None) is None


def test_numbers_for_crystal_system_returns_the_static_ranges():
    assert numbers_for_crystal_system("cubic") == range(195, 231)
    assert numbers_for_crystal_system("triclinic") == range(1, 3)
    assert numbers_for_crystal_system("Cubic") == range(195, 231)


def test_numbers_for_crystal_system_rejects_unknown_names():
    assert numbers_for_crystal_system("unknown") is None
    assert numbers_for_crystal_system("not-a-system") is None
    assert numbers_for_crystal_system("") is None
