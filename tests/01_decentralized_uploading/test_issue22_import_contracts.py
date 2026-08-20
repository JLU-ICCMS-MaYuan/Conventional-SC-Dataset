import importlib
import inspect
from pathlib import Path


def test_rebuild_helpers_import_through_real_ingest_module():
    helpers = importlib.import_module("backend.scripts.rebuild_from_clean_results")
    store_papers = importlib.import_module("backend.ingest.store_papers")

    assert store_papers.paper_is_experimental is helpers.paper_is_experimental
    assert store_papers.infer_sc_type is helpers.infer_sc_type


def test_python_image_copies_backend_scripts_package():
    root = Path(__file__).resolve().parents[2]
    dockerfile = (root / "docker/python.Dockerfile").read_text(encoding="utf-8")

    assert "COPY backend/ ./backend/" in dockerfile
    assert (root / "backend/scripts/__init__.py").is_file()
    assert (root / "backend/scripts/rebuild_from_clean_results.py").is_file()


def test_paper_is_experimental_accepts_the_production_single_argument_contract():
    from backend.scripts.rebuild_from_clean_results import paper_is_experimental

    assert list(inspect.signature(paper_is_experimental).parameters) == ["paper_type"]
    assert paper_is_experimental(" Experimental ") is True
    assert paper_is_experimental(["theoretical", "e"]) is True
    assert paper_is_experimental("theoretical") is False


def test_infer_sc_type_accepts_optional_pressure_without_changing_material_family():
    from backend.scripts.rebuild_from_clean_results import infer_sc_type

    signature = inspect.signature(infer_sc_type)
    assert list(signature.parameters) == ["elements", "pressure"]
    assert signature.parameters["pressure"].default is None
    assert infer_sc_type({"La": 1, "H": 10}) == "hydride"
    assert infer_sc_type("Ba2Cu3O7", 0.0) == "cuprate"
    assert infer_sc_type({"Fe": 1, "Se": 1}, 12.0) == "iron_based"
    assert infer_sc_type(None) == "others"
