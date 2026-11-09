"""AC-23 — Given the app on defaults, when week 2011-09-19 is picked, Overview "Revenue" shows "£328 713" with delta "+46.8%" and "Orders" shows "463"."""

from datetime import date

from fixture import app, metric

S = "\u202f"


def test_ac_23_week_picker() -> None:
    at = app()
    at.selectbox(key="week").select(date(2011, 9, 19)).run()
    assert not at.exception
    assert metric(at, "Revenue").value == f"£328{S}713"
    assert metric(at, "Revenue").delta == "+46.8%"
    assert metric(at, "Orders").value == "463"
