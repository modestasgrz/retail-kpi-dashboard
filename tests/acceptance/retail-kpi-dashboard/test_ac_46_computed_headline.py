"""AC-46 — Given fixture F plus the AC-43 line, when week 2011-09-19 is read (All countries), then `scenario.headline` is "Net revenue £178, +122.5% vs last week, +196.7% vs same week last year; 3 flags."; week 2011-09-05 gives "No sales this week."; and in the committed data week 2011-11-28 gives "Net revenue £306 112, +3.7% vs last week, -0.9% vs same week last year; no flags." and week 2011-12-05 gives "Net revenue £310 943 (partial week), +1.6% vs last week, n/a vs same week last year; 2 flags." """

from datetime import date, datetime
from pathlib import Path
from typing import Any

from fixture import REPO, UK, W0, W2, built, scenario

S = "\u202f"
YOY_LINE = (
    "400100",
    "20001",
    "MUG RED",
    30,
    datetime(2010, 9, 21, 10),
    2.00,
    90005,
    UK,
)


def test_ac_46_computed_headline(tmp_path: Path) -> None:
    from kpi.core import run_scenario
    from kpi.models import FIRST_WEEK, LAST_WEEK, Filters

    data = built(tmp_path, [YOY_LINE])
    assert scenario(data, week=W2).headline == (
        "Net revenue £178, +122.5% vs last week, +196.7% vs same week last year; 3 flags."
    )
    assert scenario(data, week=W0).headline == "No sales this week."

    def real(week: date) -> str:
        s: Any = run_scenario(
            Filters(start=FIRST_WEEK, end=LAST_WEEK, week=week),
            REPO / "data" / "derived",
        )
        return str(s.headline)

    assert real(date(2011, 11, 28)) == (
        f"Net revenue £306{S}112, +3.7% vs last week, -0.9% vs same week last year; no flags."
    )
    assert real(date(2011, 12, 5)) == (
        f"Net revenue £310{S}943 (partial week), +1.6% vs last week, n/a vs same week last year; 2 flags."
    )
