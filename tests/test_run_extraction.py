import importlib


def test_run_extraction_can_be_imported_without_side_effects() -> None:
    module = importlib.import_module("src.extraction.run_extraction")
    assert hasattr(module, "run")
    assert hasattr(module, "main")
