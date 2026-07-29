import os
import tempfile
from pathlib import Path

from streamlit.testing.v1 import AppTest


_MPLCONFIGDIR = Path(tempfile.gettempdir()) / "project_portfolio_dashboard_mpl"
_MPLCONFIGDIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPLCONFIGDIR))


EXPECTED_PAGES = [
    "Overview",
    "Asset Class",
    "Region & Currency",
    "Public Markets",
    "Private Markets",
    "Liquidity & Commitments",
    "Risk Profile",
    "Document Intake",
    "Workflow & Controls",
]

EXPECTED_TAB_LABELS = {
    "Overview": {"Summary"},
    "Document Intake": set(),
    "Asset Class": {"Trend", "By Month", "By Category", "Data Table"},
    "Region & Currency": {"Trend", "By Month", "By Category", "Data Table"},
    "Public Markets": {"Overview", "Performance", "Sector & Market Cap", "Sector", "Market Cap", "Holdings"},
    "Private Markets": {"NAV Trend", "Commitments", "Cashflows", "Fund Table"},
    "Liquidity & Commitments": {"Overview", "Capital Calls", "Distributions", "Cash Accounts"},
    "Risk Profile": {"Overview", "Volatility", "Drawdown", "Stress Test", "Correlation"},
    "Workflow & Controls": {
        "Pipeline Summary",
        "Document Ingestion",
        "Extraction Results",
        "Validation Results",
        "Review Queue",
        "Approved Updates",
    },
}


def test_late_dashboard_pages_render_without_streamlit_exceptions() -> None:
    for page_name in EXPECTED_PAGES:
        app_test = AppTest.from_file("app.py")
        app_test.run(timeout=30)
        for button in app_test.sidebar.button:
            if button.label == page_name:
                button.click()
                break
        app_test.run(timeout=30)
        assert not app_test.exception, f"{page_name} raised: {[exc.value for exc in app_test.exception]}"


def test_sidebar_navigation_matches_delivery_structure() -> None:
    app_test = AppTest.from_file("app.py")
    app_test.run(timeout=30)
    button_labels = [button.label for button in app_test.sidebar.button]
    assert button_labels == EXPECTED_PAGES


def test_each_page_exposes_expected_tabs_and_title() -> None:
    expected_titles = {
        "Overview": "Family Office Portfolio Overview",
        "Document Intake": "Document Intake",
        "Asset Class": "Asset Class Allocation & Performance",
        "Region & Currency": "Region & Currency Exposure",
        "Public Markets": "Public Markets Monitoring",
        "Private Markets": "Private Markets Monitoring",
        "Liquidity & Commitments": "Liquidity & Commitments",
        "Risk Profile": "Risk Profile",
        "Workflow & Controls": "Workflow & Controls",
    }

    for page_name in EXPECTED_PAGES:
        app_test = AppTest.from_file("app.py")
        app_test.run(timeout=30)
        for button in app_test.sidebar.button:
            if button.label == page_name:
                button.click()
                break
        app_test.run(timeout=30)

        title_values = [item.value for item in app_test.title]
        assert expected_titles[page_name] in title_values, f"{page_name} title mismatch: {title_values}"

        tab_labels = {tab.label for tab in app_test.tabs}
        assert EXPECTED_TAB_LABELS[page_name].issubset(tab_labels), (
            f"{page_name} tabs missing. expected subset={EXPECTED_TAB_LABELS[page_name]}, actual={tab_labels}"
        )
