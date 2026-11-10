"""AC-34 — Given the committed data, when `run_scenario` runs for the full year, All countries, then exactly 9 weeks are flagged: 2010-12-20, 2010-12-27, 2011-01-17, 2011-04-25, 2011-05-09, 2011-05-16, 2011-09-19, 2011-11-07, 2011-12-05; and week 2011-11-28 has no flag."""

from datetime import date

from fixture import REPO

FLAGGED = [
    "2010-12-20",
    "2010-12-27",
    "2011-01-17",
    "2011-04-25",
    "2011-05-09",
    "2011-05-16",
    "2011-09-19",
    "2011-11-07",
    "2011-12-05",
]


def test_ac_34_nine_flagged_weeks() -> None:
    from kpi.core import run_scenario
    from kpi.models import FIRST_WEEK, LAST_WEEK, Filters

    s = run_scenario(
        Filters(start=FIRST_WEEK, end=LAST_WEEK, week=date(2011, 11, 28)),
        REPO / "data" / "derived",
    )
    assert [str(w.week_start) for w in s.weeks if w.flags] == FLAGGED
    assert s.totals.flagged_weeks == 9
    assert s.selected.flags == []
