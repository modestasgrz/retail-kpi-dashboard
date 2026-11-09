"""AC-32 — Given fixture F plus one product line 500100,20001,MUG RED,1,2011-08-30 10:00,2.00,90001,United Kingdom, then week 2011-09-05 (no sales, previous week had sales) has exactly the flags [no_data] and week 2011-09-12 (previous week had no sales) has no revenue_swing and no orders_swing; and in the committed data (All countries) week 2010-12-27 has exactly [no_data] and week 2011-01-03 has no swing flag."""

from datetime import date, datetime
from pathlib import Path

from fixture import REPO, UK, W0, W1, built, rules, scenario

SWINGS = {"revenue_swing", "orders_swing"}


def test_ac_32_no_swing_around_no_data(tmp_path: Path) -> None:
    from kpi.core import run_scenario
    from kpi.models import FIRST_WEEK, LAST_WEEK, Filters

    extra = [
        ("500100", "20001", "MUG RED", 1, datetime(2011, 8, 30, 10), 2.00, 90001, UK)
    ]
    out = built(tmp_path, extra)
    assert rules(scenario(out, week=W0, start=W0, end=W0).selected) == ["no_data"]
    assert not SWINGS & set(rules(scenario(out, week=W1, start=W1, end=W1).selected))

    def real(week: date) -> list[str]:
        s = run_scenario(
            Filters(start=FIRST_WEEK, end=LAST_WEEK, week=week),
            REPO / "data" / "derived",
        )
        return rules(s.selected)

    assert real(date(2010, 12, 27)) == ["no_data"]
    assert not SWINGS & set(real(date(2011, 1, 3)))
