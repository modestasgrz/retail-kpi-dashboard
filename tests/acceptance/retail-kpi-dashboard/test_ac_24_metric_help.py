"""AC-24 — Given the app on defaults, then the "Net revenue" metric's help text equals the core's `sources["net_revenue"]` for 2011-11-28, All countries."""

from datetime import date

from fixture import REPO, app, metric


def test_ac_24_metric_help() -> None:
    from kpi.core import run_scenario
    from kpi.models import FIRST_WEEK, LAST_WEEK, Filters

    s = run_scenario(
        Filters(start=FIRST_WEEK, end=LAST_WEEK, week=date(2011, 11, 28)),
        REPO / "data" / "derived",
    )
    at = app()
    assert metric(at, "Net revenue").proto.help == s.sources["net_revenue"]
