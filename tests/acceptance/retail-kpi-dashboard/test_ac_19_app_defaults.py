"""AC-19 — Given the committed data, when `app.py` runs in AppTest with no input, then there is no exception, each of the 5 pages of DEC-09 opens via `switch_page(<file>)` with no exception and shows its title as `st.title`, the sidebar preset is "Full year", country "All countries", week 2011-11-28 (the last full week; 2011-12-05 is partial), and the Overview metric "Net revenue" shows "£306 112" with delta "+3.7%"."""

from datetime import date

from fixture import app, metric

S = "\u202f"
PAGES = [
    ("views/overview.py", "Overview"),
    ("views/trends.py", "Trends"),
    ("views/flags.py", "Flagged weeks"),
    ("views/table.py", "Weekly table"),
    ("views/methodology.py", "Methodology & data"),
]


def test_ac_19_app_defaults() -> None:
    at = app()
    assert not at.exception
    assert at.selectbox(key="preset").value == "Full year"
    assert at.selectbox(key="country").value == "All countries"
    assert at.selectbox(key="week").value == date(2011, 11, 28)
    revenue = metric(at, "Net revenue")
    assert revenue.value == f"£306{S}112"
    assert revenue.delta == "+3.7%"
    assert at.title[0].value == "Overview"
    for path, title in PAGES:
        at.switch_page(path).run()
        assert not at.exception, path
        assert [t.value for t in at.title] == [title], path
