"""AC-44 — Given fixture F plus one cancellation line C500012,20001,MUG RED,-30,2011-09-21 10:00,2.00,90002,United Kingdom (cancels the 500003 Mug Red line of the same customer, week and price), when week 2011-09-19 is read (All countries), then net revenue is 118.00, the flag rules are exactly [`revenue_swing`, `orders_swing`, `placed_cancelled`] (no `top_line`: its line is the placed-and-cancelled one; no `large_cancellations`: all £85 cancelled is matched), the `placed_cancelled` reason is "Placed and cancelled: £60, net £0 (Mug Red, invoice 500003)" and the revenue swing reason is "Net revenue +47.5% vs 4-week average (£118 vs £80)"; and AC-08's weeks still give its results."""

from datetime import datetime
from pathlib import Path

import pytest
from fixture import UK, W2, built, reasons, rules, week_row

CANCEL = (
    "C500012",
    "20001",
    "MUG RED",
    -30,
    datetime(2011, 9, 21, 10),
    2.00,
    90002,
    UK,
)


def test_ac_44_placed_and_cancelled(tmp_path: Path) -> None:
    w = week_row(built(tmp_path, [CANCEL]), W2)
    assert w.net_revenue == pytest.approx(118.00)
    assert rules(w) == ["revenue_swing", "orders_swing", "placed_cancelled"]
    got = reasons(w)
    assert got["placed_cancelled"] == (
        "Placed and cancelled: £60, net £0 (Mug Red, invoice 500003)"
    )
    assert got["revenue_swing"] == "Net revenue +47.5% vs 4-week average (£118 vs £80)"
