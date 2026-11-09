"""AC-19 — Given the committed data, app.py in AppTest with no input: no exception; each of the 5 DEC-09 pages opens via switch_page with no exception and shows its title; sidebar preset "Full year", country "All countries", week 2011-11-28; Overview "Revenue" shows "£309 378" with delta "+2.3%"."""

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
    revenue = metric(at, "Revenue")
    assert revenue.value == f"£309{S}378"
    assert revenue.delta == "+2.3%"
    assert at.title[0].value == "Overview"
    for path, title in PAGES:
        at.switch_page(path).run()
        assert not at.exception, path
        assert [t.value for t in at.title] == [title], path
