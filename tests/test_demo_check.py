from src.demo_check import run_demo_check


def test_run_demo_check_returns_structured_results() -> None:
    results = run_demo_check(write_report=True)
    assert isinstance(results, dict)
    assert "summary" in results
    assert "passed" in results
    assert "failed" in results
    assert "report_path" in results
    assert not results["failed"]


def test_demo_readiness_report_is_created() -> None:
    results = run_demo_check(write_report=True)
    report_path = results["report_path"]
    assert report_path.exists()
    assert report_path.read_text(encoding="utf-8").startswith("# Demo Readiness Report")
