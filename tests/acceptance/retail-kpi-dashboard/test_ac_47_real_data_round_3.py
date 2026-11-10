"""AC-47 — Given the committed data, All countries, then week 2011-11-28 has net AOV "£461.71", net revenue YoY "-0.9%", orders YoY "+1.7%", net AOV YoY "-2.6%"; week 2011-12-05's `placed_cancelled` reason is "Placed and cancelled: £168 470, net £0 (Paper Craft , Little Birdie, invoice 581483)"; week 2011-01-17's flag rules are exactly [`placed_cancelled`] with reason "Placed and cancelled: £77 184, net £0 (Medium Ceramic Top Storage Jar, invoice 541431)"; week 2011-09-19's revenue swing reason is "Net revenue +82.0% vs 4-week average (£319 746 vs £175 656)" with first product driver ("Set Of Tea Coffee Sugar Tins Pantry", £8 265 rounded), product `explained_pct` "11.5%" and first country driver ("United Kingdom", £113 442 rounded), country `explained_pct` "90.3%"; and `weekly.parquet` has 105 weeks per filter value (2009-12-07 .. 2011-12-05) with no `Customer ID` column."""

from datetime import date
from typing import Any

import pandas as pd
from fixture import REPO

S = "\u202f"


def test_ac_47_real_data_round_3() -> None:
    from kpi.core import run_scenario
    from kpi.fmt import change, money, money2, pct
    from kpi.models import FIRST_WEEK, LAST_WEEK, Filters

    data = REPO / "data" / "derived"
    s = run_scenario(Filters(start=FIRST_WEEK, end=LAST_WEEK, week=LAST_WEEK), data)
    weeks: dict[date, Any] = {w.week_start: w for w in s.weeks}
    a = weeks[date(2011, 11, 28)]
    assert money2(a.net_aov) == "£461.71"
    assert change(a.net_revenue_yoy) == "-0.9%"
    assert change(a.orders_yoy) == "+1.7%"
    assert change(a.net_aov_yoy) == "-2.6%"
    b = {f.rule: f.reason for f in weeks[date(2011, 12, 5)].flags}
    assert b["placed_cancelled"] == (
        f"Placed and cancelled: £168{S}470, net £0 (Paper Craft , Little Birdie, invoice 581483)"
    )
    c = weeks[date(2011, 1, 17)]
    assert [f.rule for f in c.flags] == ["placed_cancelled"]
    assert c.flags[0].reason == (
        f"Placed and cancelled: £77{S}184, net £0 (Medium Ceramic Top Storage Jar, invoice 541431)"
    )
    swing = next(f for f in weeks[date(2011, 9, 19)].flags if f.rule == "revenue_swing")
    assert swing.reason == (
        f"Net revenue +82.0% vs 4-week average (£319{S}746 vs £175{S}656)"
    )
    by = {d.by: d for d in swing.drivers}
    first = by["product"].items[0]
    assert (first.label, money(first.change)) == (
        "Set Of Tea Coffee Sugar Tins Pantry",
        f"£8{S}265",
    )
    assert pct(by["product"].explained_pct) == "11.5%"
    first = by["country"].items[0]
    assert (first.label, money(first.change)) == ("United Kingdom", f"£113{S}442")
    assert pct(by["country"].explained_pct) == "90.3%"
    weekly = pd.read_parquet(data / "weekly.parquet")
    assert "Customer ID" not in weekly.columns
    sizes = weekly.groupby("filter")["week_start"].agg(["count", "min", "max"])
    assert set(sizes["count"]) == {105}
    assert set(sizes["min"].astype(str).str[:10]) == {"2009-12-07"}
    assert set(sizes["max"].astype(str).str[:10]) == {"2011-12-05"}
