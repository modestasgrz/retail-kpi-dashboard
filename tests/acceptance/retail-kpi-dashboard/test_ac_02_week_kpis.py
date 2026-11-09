"""AC-02 — Given fixture F built, when run_scenario(start 2011-09-05, end 2011-09-19, All countries, week 2011-09-19) runs, then the selected week has revenue 203.00, orders 5, AOV 40.60, units 50, customers 3, new 2, returning 1, cancellation invoices 1, cancellation rate 16.666... ("16.7%"), cancelled value 25.00, revenue after cancellations 178.00, product lines 6, lines without customer id 1."""

from pathlib import Path

import pytest
from fixture import built, scenario


def test_ac_02_week_kpis(tmp_path: Path) -> None:
    from kpi.fmt import pct

    w = scenario(built(tmp_path)).selected
    assert w.revenue == pytest.approx(203.00)
    assert w.orders == 5
    assert w.aov == pytest.approx(40.60)
    assert w.units == 50
    assert w.customers == 3
    assert w.new_customers == 2
    assert w.returning_customers == 1
    assert w.cancellation_invoices == 1
    assert w.cancellation_rate == pytest.approx(100 / 6)
    assert pct(w.cancellation_rate) == "16.7%"
    assert w.cancelled_value == pytest.approx(25.00)
    assert w.net_revenue == pytest.approx(178.00)
    assert w.product_lines == 6
    assert w.lines_without_customer_id == 1
