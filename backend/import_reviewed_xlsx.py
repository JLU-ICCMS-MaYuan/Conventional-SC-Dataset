"""
Deprecated reviewed-XLSX import script.

The old implementation wrote Compound/PaperData rows. The MySQL redesign uses
papers and superconductor_records, so reviewed spreadsheet import must be
re-mapped before it can be used again.
"""


def main() -> None:
    raise SystemExit(
        "reviewed XLSX import is not available for the redesigned MySQL schema yet; "
        "convert the file to mysql-redesign-v1 JSON and use backend.import_data."
    )


if __name__ == "__main__":
    main()
