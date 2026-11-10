"""AC-43 — Given fixture F plus one product line 400100,20001,MUG RED,30,2010-09-21 10:00,2.00,90005,United Kingdom (week 2010-09-20 = 2011-09-19 − 364 days), when week 2011-09-19 is read (All countries), then `net_aov` = 35.60, `net_revenue_wow` = 122.5, `net_revenue_yoy` = (178 − 60) / 60 × 100 (display "+196.7%"), `orders_yoy` = 400.0, `net_aov_yoy` = (35.6 − 60) / 60 × 100 (display "-40.7%"); week 2011-09-12 has `net_revenue_yoy`, `orders_yoy` and `net_aov_yoy` None (no sales in 2010-09-13); and in the committed data week 2011-12-05 (partial) and week 2010-12-27 (base 2009-12-28 had no sales) have `net_revenue_yoy` None."""

from datetime import date, datetime
from pathlib import Path
from typing import Any

import pytest
from fixture import REPO, UK, W1, W2, built, week_row

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


def test_ac_43_year_over_year(tmp_path: Path) -> None:
    from kpi.core import run_scenario
    from kpi.fmt import change
    from kpi.models import FIRST_WEEK, LAST_WEEK, Filters

    data = built(tmp_path, [YOY_LINE])
    w = week_row(data, W2)
    assert w.net_aov == pytest.approx(35.60)
    assert w.net_revenue_wow == pytest.approx(122.5)
    assert w.net_revenue_yoy == pytest.approx((178 - 60) / 60 * 100)
    assert change(w.net_revenue_yoy) == "+196.7%"
    assert w.orders_yoy == pytest.approx(400.0)
    assert w.net_aov_yoy == pytest.approx((35.6 - 60) / 60 * 100)
    assert change(w.net_aov_yoy) == "-40.7%"
    v = week_row(data, W1)
    assert (v.net_revenue_yoy, v.orders_yoy, v.net_aov_yoy) == (None, None, None)
    weeks: dict[date, Any] = {
        x.week_start: x
        for x in run_scenario(
            Filters(start=FIRST_WEEK, end=LAST_WEEK, week=LAST_WEEK),
            REPO / "data" / "derived",
        ).weeks
    }
    assert weeks[date(2011, 12, 5)].net_revenue_yoy is None
    assert weeks[date(2010, 12, 27)].net_revenue_yoy is None
