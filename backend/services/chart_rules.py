TC_FIELDS = (
    "experimental_tc",
    "anisotropic_eliashberg_tc",
    "isotropic_eliashberg_tc",
    "allen_dynes_tc",
    "mcmillan_tc",
)


def representative_tc(record):
    for field in TC_FIELDS:
        value = getattr(record, field, None)
        if value is not None:
            return value
    return None


def include_in_tc_pressure_chart(record) -> bool:
    return (
        bool(getattr(record, "show_in_chart", False))
        and getattr(record, "pressure_gpa", None) is not None
        and representative_tc(record) is not None
    )


def include_in_tc_year_chart(record) -> bool:
    return include_in_tc_pressure_chart(record) and getattr(record, "paper_id", None) is not None
