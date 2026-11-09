"""AC-25 — Given the app on defaults with week 2011-09-19, Overview shows the DEC-14 label and the headline "Revenue and orders jump to an unusually strong week, led by pantry products"; on preset "UK only" the summary is hidden and the note "The saved weekly summary covers all countries, so it is hidden while a country filter is on." is shown."""

from datetime import date

from fixture import app, texts

LABEL = "Weekly summary written by AI in an earlier run; every figure was checked against the computed numbers. This app makes no AI calls."
HEADLINE = "Revenue and orders jump to an unusually strong week, led by pantry products"
NOTE = "The saved weekly summary covers all countries, so it is hidden while a country filter is on."


def test_ac_25_summary_label() -> None:
    at = app()
    at.selectbox(key="week").select(date(2011, 9, 19)).run()
    shown = texts(at)
    assert LABEL in shown
    assert HEADLINE in shown
    at.selectbox(key="preset").select("UK only").run()
    at.selectbox(key="week").select(date(2011, 9, 19)).run()
    hidden = texts(at)
    assert not at.exception
    assert HEADLINE not in hidden
    assert NOTE in hidden
