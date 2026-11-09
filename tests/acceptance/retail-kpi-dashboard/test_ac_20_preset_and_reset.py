"""AC-20 — Given the app on defaults, preset "UK only" makes Overview "Revenue" equal money() of the core's UK revenue for 2011-11-28 and differ from "£309 378"; Reset restores preset "Full year", country "All countries", week 2011-11-28, "Revenue" "£309 378"."""

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
    assert metric(at, "Revenue").value == money(uk.selected.revenue)
    assert metric(at, "Revenue").value != f"£309{S}378"
    at.button(key="reset").click().run()
    assert at.selectbox(key="preset").value == "Full year"
    assert at.selectbox(key="country").value == "All countries"
    assert at.selectbox(key="week").value == week
    assert metric(at, "Revenue").value == f"£309{S}378"
