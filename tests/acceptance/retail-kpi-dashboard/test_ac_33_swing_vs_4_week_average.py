"""AC-33 — Given fixture F plus one product line 500100,20001,MUG RED,1,2011-08-30 10:00,2.00,90001,United Kingdom, when week 2011-09-19 is read (All countries), then `net_revenue_vs4w` = (178 − 41) / 41 × 100 (net revenue; base = mean of the previous 4 weeks that had product lines: 2011-09-12 £80 and 2011-08-29 £2), the flag reasons are "Net revenue +334.1% vs 4-week average (£178 vs £41)" and "Orders +233.3% vs 4-week average (5 vs 1.5)"; and `swing(39.94)` is False, `swing(-39.96)` is True, `swing(40.0)` is True, `swing(None)` is False."""

from datetime import datetime
from pathlib import Path

import pytest
from fixture import UK, W2, built, reasons, scenario


def test_ac_33_swing_vs_4_week_average(tmp_path: Path) -> None:
    from kpi.core import swing

    extra = [
        ("500100", "20001", "MUG RED", 1, datetime(2011, 8, 30, 10), 2.00, 90001, UK)
    ]
    w = scenario(built(tmp_path, extra), week=W2, start=W2, end=W2).selected
    assert w.net_revenue_vs4w == pytest.approx((178 - 41) / 41 * 100)
    got = reasons(w)
    assert got["revenue_swing"] == "Net revenue +334.1% vs 4-week average (£178 vs £41)"
    assert got["orders_swing"] == "Orders +233.3% vs 4-week average (5 vs 1.5)"
    assert swing(39.94) is False
    assert swing(-39.96) is True
    assert swing(40.0) is True
    assert swing(None) is False
