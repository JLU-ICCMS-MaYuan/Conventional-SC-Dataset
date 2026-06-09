"""
Deprecated batch-upload parser.

The legacy parser emitted Compound/PaperData-shaped fragments. Batch upload is
kept as a product entrypoint, but the parser needs a new mapping to
papers/superconductor_records before it should write data again.
"""

from pathlib import Path


def process_file(content: bytes, filename: str):
    raise NotImplementedError(
        "batch upload parser is not available for the redesigned MySQL schema yet"
    )


def create_example_xlsx(path: str | Path):
    raise NotImplementedError(
        "batch upload example is not available until the new records-based import format is finalized"
    )
