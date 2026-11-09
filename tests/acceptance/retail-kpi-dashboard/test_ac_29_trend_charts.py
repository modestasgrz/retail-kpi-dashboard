"""AC-29 — Given the app on defaults, Trends shows 4 Plotly charts with no exception."""

from fixture import app


def test_ac_29_trend_charts() -> None:
    at = app()
    at.switch_page("views/trends.py").run()
    assert not at.exception
    assert len(at.get("plotly_chart")) == 4
