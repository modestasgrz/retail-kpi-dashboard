"""AC-21 — On defaults and then on preset "Q4 2011", Overview, Trends, Flagged weeks and Weekly table each show strip metrics "Range revenue", "Range orders", "Flagged weeks" with identical values across the four pages, equal to the core's totals for that range."""

from datetime import date

from fixture import REPO, app, metric

PAGES = ["views/overview.py", "views/trends.py", "views/flags.py", "views/table.py"]
STRIP = ["Range revenue", "Range orders", "Flagged weeks"]


def test_ac_21_same_kpi_every_page() -> None:
    from kpi.core import run_scenario
    from kpi.fmt import count, money
    from kpi.models import FIRST_WEEK, LAST_WEEK, Filters

    at = app()
    for preset, start in [("Full year", FIRST_WEEK), ("Q4 2011", date(2011, 10, 3))]:
        at.selectbox(key="preset").select(preset).run()
        t = run_scenario(
            Filters(start=start, end=LAST_WEEK, week=date(2011, 11, 28)),
            REPO / "data" / "derived",
        ).totals
        expected = [money(t.revenue), count(t.orders), count(t.flagged_weeks)]
        for page in PAGES:
            at.switch_page(page).run()
            assert not at.exception, page
            assert [metric(at, label).value for label in STRIP] == expected, (
                preset,
                page,
            )
