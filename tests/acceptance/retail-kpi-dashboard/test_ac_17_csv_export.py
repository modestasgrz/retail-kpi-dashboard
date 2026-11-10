"""AC-17 — Given fixture F built and range 2011-09-05..2011-09-19, when `weekly_csv(scenario)` runs, then the UTF-8 text has the header of DEC-12, 3 data rows in week order, and the 2011-09-19 row has revenue_gbp 203.00, orders 5, revenue_wow_pct 153.75, flags "revenue_swing; orders_swing; top_line", net_aov_gbp 35.60, net_revenue_wow_pct 122.50 and an empty net_revenue_yoy_pct."""

import csv
import io
from pathlib import Path

from fixture import built, scenario

HEADER = "week_start,revenue_gbp,orders,aov_gbp,units,customers,new_customers,returning_customers,cancellation_invoices,cancellation_rate_pct,cancelled_value_gbp,net_revenue_gbp,product_lines,lines_without_customer_id,revenue_wow_pct,orders_wow_pct,flags,net_aov_gbp,net_revenue_wow_pct,net_revenue_yoy_pct,orders_yoy_pct,net_aov_yoy_pct"


def test_ac_17_csv_export(tmp_path: Path) -> None:
    from kpi.core import weekly_csv

    text = weekly_csv(scenario(built(tmp_path))).decode("utf-8")
    assert text.splitlines()[0] == HEADER
    rows = list(csv.DictReader(io.StringIO(text)))
    assert [r["week_start"] for r in rows] == ["2011-09-05", "2011-09-12", "2011-09-19"]
    last = rows[2]
    assert last["revenue_gbp"] == "203.00"
    assert last["orders"] == "5"
    assert last["revenue_wow_pct"] == "153.75"
    assert last["flags"] == "revenue_swing; orders_swing; top_line"
    assert last["net_aov_gbp"] == "35.60"
    assert last["net_revenue_wow_pct"] == "122.50"
    assert last["net_revenue_yoy_pct"] == ""
