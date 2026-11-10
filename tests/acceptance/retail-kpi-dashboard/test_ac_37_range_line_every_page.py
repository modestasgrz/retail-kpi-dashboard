"""AC-37 — Given the app on defaults and then on preset "Q4 2011", when each of Overview, Trends, Flagged weeks and Weekly table is opened, then each shows a caption equal to "Range {start} – {end + 6 days} · revenue {money} · orders {count} · flagged weeks {count}" built from the core's totals (Full year: "Range 2010-12-06 – 2011-12-11 · revenue £10 066 085 · orders 19 349 · flagged weeks 9"), the same string on all four pages, and no metric labelled "Range revenue"."""

from datetime import date, timedelta

from fixture import REPO, app

PAGES = ["views/overview.py", "views/trends.py", "views/flags.py", "views/table.py"]
S = "\u202f"


def test_ac_37_range_line_every_page() -> None:
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
        line = f"Range {start} – {LAST_WEEK + timedelta(days=6)} · revenue {money(t.revenue)} · orders {count(t.orders)} · flagged weeks {count(t.flagged_weeks)}"
        if preset == "Full year":
            assert (
                line
                == f"Range 2010-12-06 – 2011-12-11 · revenue £10{S}066{S}085 · orders 19{S}349 · flagged weeks 9"
            )
        for page in PAGES:
            at.switch_page(page).run()
            assert not at.exception, page
            assert line in [c.value for c in at.caption], (preset, page)
            assert "Range revenue" not in [m.label for m in at.metric], page
