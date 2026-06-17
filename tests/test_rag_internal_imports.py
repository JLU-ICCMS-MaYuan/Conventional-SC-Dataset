import importlib


def test_internal_rag_runtime_imports():
    modules = [
        "backend.rag.config",
        "backend.rag.database",
        "backend.rag.vectordb",
        "backend.rag.search.engine",
        "backend.rag.rag.engine",
    ]

    for module_name in modules:
        module = importlib.import_module(module_name)
        assert module is not None


def test_internal_rag_public_functions_importable():
    from backend.rag.config import get_rag_settings
    from backend.rag.search.engine import search
    from backend.rag.rag.engine import ask

    settings = get_rag_settings()
    assert settings.rag_data_root.name == "Conventional-SC-Dataset-talk"
    assert callable(search)
    assert callable(ask)
