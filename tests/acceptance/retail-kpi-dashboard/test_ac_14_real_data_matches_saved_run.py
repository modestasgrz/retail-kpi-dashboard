"""AC-14 — Given the committed data/derived tables, All countries: week 2011-09-19 and 2011-12-05 match the earlier independent run (values in the spec), and 2011-12-05's set of flag rules is exactly {partial_week, revenue_swing, large_cancellations, top_line}."""

from datetime import date
from typing import Any

from fixture import REPO

S = "\u202f"


def test_ac_14_real_data_matches_saved_run() -> None:
    from kpi.core import run_scenario
    from kpi.fmt import change, count, money, money2, pct
    from kpi.models import FIRST_WEEK, LAST_WEEK, Filters

    def week(d: date) -> Any:
        return run_scenario(
            Filters(start=FIRST_WEEK, end=LAST_WEEK, week=d), REPO / "data" / "derived"
        ).selected

    a = week(date(2011, 9, 19))
    assert money(a.revenue) == f"£328{S}713"
    assert count(a.orders) == "463"
    assert money2(a.aov) == "£709.96"
    assert count(a.customers) == "383"
    assert count(a.new_customers) == "64"
    assert pct(a.cancellation_rate) == "17.0%"
    assert money(a.cancelled_value) == f"£8{S}967"
    assert money(a.net_revenue) == f"£319{S}746"
    assert (a.product_lines, a.lines_without_customer_id) == (13181, 2517)
    assert change(a.revenue_wow) == "+46.8%"
    b = week(date(2011, 12, 5))
    assert money(b.revenue) == f"£483{S}725"
    assert count(b.orders) == "509"
    assert money2(b.aov) == "£950.34"
    assert count(b.customers) == "415"
    assert count(b.new_customers) == "17"
    assert pct(b.cancellation_rate) == "14.3%"
    assert money(b.cancelled_value) == f"£172{S}782"
    assert money(b.net_revenue) == f"£310{S}943"
    assert change(b.revenue_wow) == "+56.4%"
    assert change(b.orders_wow) == "-23.2%"
    assert {f.rule for f in b.flags} == {
        "partial_week",
        "revenue_swing",
        "large_cancellations",
        "top_line",
    }
