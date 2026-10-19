from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


def test_dashboard_runs_and_clears_stale_results():
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    assert not app.exception
    app.button[0].click().run()
    assert not app.exception
    assert app.metric[0].value == "100 / 100"
    assert app.metric[2].value == "0"
    app.sidebar.selectbox[1].select("unauthorized").run()
    assert not app.metric
    app.button[0].click().run()
    assert not app.exception
    assert float(app.metric[0].value.split(" / ")[0]) < 100
    assert int(app.metric[2].value) > 0
    assert app.error


def test_dashboard_handles_no_tool_scenario():
    app = AppTest.from_file(str(APP), default_timeout=20).run()
    app.sidebar.selectbox[0].select("retrieval-02").run()
    app.button[0].click().run()
    assert not app.exception
    assert app.metric[0].value == "100 / 100"
