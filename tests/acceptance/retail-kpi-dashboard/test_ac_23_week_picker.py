"""AC-23 — Given the app on defaults, when week 2011-09-19 is picked, then Overview "Net revenue" shows "£319 746" with delta "+43.9%" and "Orders" shows "463"."""

from datetime import date

from fixture import app, metric

S = "\u202f"


def test_ac_23_week_picker() -> None:
    at = app()
    at.selectbox(key="week").select(date(2011, 9, 19)).run()
    assert not at.exception
    assert metric(at, "Net revenue").value == f"£319{S}746"
    assert metric(at, "Net revenue").delta == "+43.9%"
    assert metric(at, "Orders").value == "463"
