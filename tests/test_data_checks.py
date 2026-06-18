from src.data_checks import run_all_checks


def test_run_all_checks_returns_structured_results() -> None:
    results = run_all_checks(write_report=True)
    assert isinstance(results, dict)
    assert "passed" in results
    assert "failed" in results
    assert "warnings" in results
    assert "assumptions" in results
    assert "report_path" in results
    assert not results["failed"]


def test_qa_report_is_created() -> None:
    results = run_all_checks(write_report=True)
    report_path = results["report_path"]
    assert report_path.exists()
    assert report_path.read_text(encoding="utf-8").startswith("# Data QA Report")
