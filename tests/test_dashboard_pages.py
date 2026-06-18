import os
import tempfile
from pathlib import Path

from streamlit.testing.v1 import AppTest


_MPLCONFIGDIR = Path(tempfile.gettempdir()) / "project_portfolio_dashboard_mpl"
_MPLCONFIGDIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPLCONFIGDIR))


def test_late_dashboard_pages_render_without_streamlit_exceptions() -> None:
    for page_name in [
        "Overview",
        "Asset Class",
        "Region & Currency",
        "Public Markets",
        "Private Markets",
        "Liquidity & Commitments",
        "Risk Profile",
        "Workflow & Controls",
    ]:
        app_test = AppTest.from_file("app.py")
        app_test.run(timeout=30)
        app_test.sidebar.radio[0].set_value(page_name)
        app_test.run(timeout=30)
        assert not app_test.exception, f"{page_name} raised: {[exc.value for exc in app_test.exception]}"
