"""AC-17 — Given fixture F built and range 2011-09-05..2011-09-19, weekly_csv(scenario) is UTF-8 with the DEC-12 header, 3 data rows in week order, and the 2011-09-19 row has revenue_gbp 203.00, orders 5, revenue_wow_pct 153.75, flags "revenue_swing; orders_swing; top_line"."""

import csv
import io
from pathlib import Path

from fixture import built, scenario

HEADER = "week_start,revenue_gbp,orders,aov_gbp,units,customers,new_customers,returning_customers,cancellation_invoices,cancellation_rate_pct,cancelled_value_gbp,net_revenue_gbp,product_lines,lines_without_customer_id,revenue_wow_pct,orders_wow_pct,flags"


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
