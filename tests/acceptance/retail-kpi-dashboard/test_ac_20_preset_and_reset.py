"""AC-20 — Given the app on defaults, when preset "UK only" is chosen, then the Overview "Net revenue" metric equals `money()` of the core's United Kingdom net revenue for 2011-11-28 and differs from "£306 112"; when Reset is clicked, then preset is "Full year", country "All countries", week 2011-11-28 and "Net revenue" shows "£306 112" again."""

from datetime import date

from fixture import REPO, app, metric

S = "\u202f"


def test_ac_20_preset_and_reset() -> None:
    from kpi.core import run_scenario
    from kpi.fmt import money
    from kpi.models import FIRST_WEEK, LAST_WEEK, Filters

    week = date(2011, 11, 28)
    uk = run_scenario(
        Filters(start=FIRST_WEEK, end=LAST_WEEK, country="United Kingdom", week=week),
        REPO / "data" / "derived",
    )
    at = app()
    at.selectbox(key="preset").select("UK only").run()
    assert not at.exception
    assert metric(at, "Net revenue").value == money(uk.selected.net_revenue)
    assert metric(at, "Net revenue").value != f"£306{S}112"
    at.button(key="reset").click().run()
    assert at.selectbox(key="preset").value == "Full year"
    assert at.selectbox(key="country").value == "All countries"
    assert at.selectbox(key="week").value == week
    assert metric(at, "Net revenue").value == f"£306{S}112"
