"""AC-22 — Given the app, when the date range input holds only a start date, the page shows the error "Pick both a start and an end date." and no metric is shown, with no exception."""

from datetime import date

from fixture import app


def test_ac_22_bad_date_input() -> None:
    at = app()
    at.date_input(key="dates").set_value((date(2011, 3, 7),)).run()
    assert not at.exception
    assert "Pick both a start and an end date." in [e.value for e in at.error]
    assert len(at.metric) == 0
