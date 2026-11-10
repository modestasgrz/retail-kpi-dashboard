"""QA round 3 for PART-A: placed and cancelled (DEC-25), drivers (DEC-24), YoY (DEC-23), headline (DEC-26), committed data."""

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from kpi import core
from kpi.build import PRODUCT_WEEKS
from kpi.build import build as build_tables
from kpi.core import run_scenario, top_drivers
from kpi.data import COLUMNS
from kpi.fmt import change, money
from kpi.models import ALL, OUTSIDE_UK, UK, Filters, Flag, Scenario, WeekRow

NONE = float("nan")
W = date(2011, 9, 19)
PAD_WEEKS = [
    date(2011, 8, 22),
    date(2011, 8, 29),
    date(2011, 9, 5),
    date(2011, 9, 12),
    W,
]
Line = tuple[Any, ...]


def at(day: date, hour: int = 10) -> datetime:
    return datetime(day.year, day.month, day.day, hour)


def pad(
    country: str = UK, skip: tuple[date, ...] = (), target_qty: int = 20
) -> list[Line]:
    """Per week 2011-08-22..2011-09-19 one invoice (customer 1) of five 200-pound lines (codes 10001..10005), so no line is a top line."""
    return [
        (
            f"P{w:%m%d}",
            f"1000{n}",
            f"PADDING {'ABCDE'[n - 1]}",
            target_qty if w == W else 20,
            at(w + timedelta(days=2)),
            10.0,
            1,
            country,
        )
        for w in PAD_WEEKS
        if w not in skip
        for n in range(1, 6)
    ]


END: Line = ("E1", "10002", "END MARKER", 1, datetime(2011, 12, 11, 12), 1.0, 2, UK)


def raw(lines: list[Line]) -> pd.DataFrame:
    df = pd.DataFrame(lines, columns=COLUMNS)
    df["Invoice"] = df["Invoice"].astype(str)
    df["StockCode"] = df["StockCode"].astype(str)
    return df


def make(
    tmp_path: Path, lines: list[Line], with_end: bool = True, name: str = "d"
) -> Path:
    out = tmp_path / name
    build_tables(raw(lines + ([END] if with_end else [])), out)
    return out


def scen(
    d: Path, week: date = W, country: str = ALL, start: date | None = None
) -> Scenario:
    return run_scenario(
        Filters(start=start or week, end=week, country=country, week=week), d
    )


def row(d: Path, week: date = W, country: str = ALL) -> WeekRow:
    return scen(d, week, country).selected


def rules(r: WeekRow) -> list[str]:
    return [f.rule for f in r.flags]


def flag(r: WeekRow, rule: str) -> Flag:
    return next(f for f in r.flags if f.rule == rule)


def weekly_row(d: Path, week: date, country: str = ALL) -> pd.Series:
    w = pd.read_parquet(d / "weekly.parquet")
    w["week_start"] = pd.to_datetime(w["week_start"]).dt.date
    return w[(w["filter"] == country) & (w["week_start"] == week)].iloc[0]


def order(
    invoice: str,
    code: str,
    desc: str,
    qty: int,
    price: float,
    cust: Any = 5,
    day: date = date(2011, 9, 20),
    country: str = UK,
) -> Line:
    return (invoice, code, desc, qty, at(day), price, cust, country)


# ---------------------------------------------------------------- DEC-25


def test_partial_quantity_cancellation(tmp_path: Path) -> None:
    d = make(
        tmp_path,
        pad()
        + [
            order("600001", "20001", "MUG RED", 10, 500.0),
            order("C600002", "20001", "MUG RED", -4, 500.0, day=date(2011, 9, 21)),
        ],
    )
    r = row(d)
    assert weekly_row(d, W)["matched_cancelled_value"] == 2000.0
    assert flag(r, "placed_cancelled").reason == (
        f"Placed and cancelled: {money(5000)}, net {money(3000)} (Mug Red, invoice 600001)"
    )
    assert "top_line" not in rules(r)
    assert "large_cancellations" not in rules(r)
    assert r.net_revenue == 4000.0


def test_cancel_more_than_placed_matches_placed_quantity(tmp_path: Path) -> None:
    d = make(
        tmp_path,
        pad()
        + [
            order("600001", "20001", "MUG RED", 4, 500.0),
            order("C600002", "20001", "MUG RED", -10, 500.0, day=date(2011, 9, 21)),
        ],
    )
    assert weekly_row(d, W)["pc_cancelled"] == 2000.0
    assert weekly_row(d, W)["pc_placed"] == 2000.0


def test_split_orders_and_cancellations_sum_per_pair(tmp_path: Path) -> None:
    d = make(
        tmp_path,
        pad()
        + [
            order("600001", "20001", "MUG RED", 6, 500.0),
            order("600003", "20001", "MUG RED", 4, 500.0),
            order("C600002", "20001", "MUG RED", -3, 500.0, day=date(2011, 9, 21)),
            order("C600004", "20001", "MUG RED", -2, 500.0, day=date(2011, 9, 22)),
        ],
    )
    w = weekly_row(d, W)
    assert w["pc_placed"] == 5000.0
    assert w["pc_cancelled"] == 2500.0
    assert w["pc_invoice"] == "600001"


@pytest.mark.parametrize(
    "cancel",
    [
        order("C600002", "20001", "MUG RED", -10, 499.0, day=date(2011, 9, 21)),
        order(
            "C600002", "20001", "MUG RED", -10, 500.0, cust=NONE, day=date(2011, 9, 21)
        ),
        order("C600002", "20001", "MUG RED", -10, 500.0, cust=6, day=date(2011, 9, 21)),
        order("C600002", "20009", "MUG RED", -10, 500.0, day=date(2011, 9, 21)),
        order("C600002", "20001", "MUG RED", -10, 500.0, day=date(2011, 9, 26)),
        order("C600002", "20001", "MUG RED", -10, 500.0, day=date(2011, 9, 14)),
    ],
    ids=[
        "other_price",
        "no_customer",
        "other_customer",
        "other_code",
        "following_week",
        "previous_week",
    ],
)
def test_no_match_cases(tmp_path: Path, cancel: Line) -> None:
    d = make(tmp_path, pad() + [order("600001", "20001", "MUG RED", 10, 500.0), cancel])
    for week in (date(2011, 9, 12), W, date(2011, 9, 26)):
        w = weekly_row(d, week)
        assert w["matched_cancelled_value"] == 0.0
        assert w["pc_cancelled"] == 0.0
        assert w["pc_invoice"] == ""
    assert "placed_cancelled" not in rules(row(d))


def test_unmatched_cancellation_still_counts_as_large(tmp_path: Path) -> None:
    d = make(
        tmp_path,
        pad()
        + [
            order("600001", "20001", "MUG RED", 10, 500.0),
            order("C600002", "20001", "MUG RED", -10, 499.0, day=date(2011, 9, 21)),
        ],
    )
    r = row(d)
    assert "large_cancellations" in rules(r)
    assert "top_line" in rules(r)


def test_placed_line_without_customer_never_matches(tmp_path: Path) -> None:
    d = make(
        tmp_path,
        pad()
        + [
            order("600001", "20001", "MUG RED", 10, 500.0, cust=NONE),
            order("C600002", "20001", "MUG RED", -10, 500.0, cust=NONE),
        ],
    )
    assert weekly_row(d, W)["matched_cancelled_value"] == 0.0


def test_cancellation_in_following_week_leaves_both_weeks_clean(
    tmp_path: Path,
) -> None:
    d = make(
        tmp_path,
        pad()
        + [
            order("600001", "20001", "MUG RED", 10, 500.0, day=date(2011, 9, 25)),
            order("C600002", "20001", "MUG RED", -10, 500.0, day=date(2011, 9, 26)),
        ],
    )
    assert "placed_cancelled" not in rules(row(d))
    assert "placed_cancelled" not in rules(row(d, date(2011, 9, 26)))


def test_week_boundary_sunday_and_monday(tmp_path: Path) -> None:
    lines = [
        ("600001", "20001", "MUG RED", 10, datetime(2011, 9, 25, 23, 59), 500.0, 5, UK),
        ("C600002", "20001", "MUG RED", -10, datetime(2011, 9, 25, 0, 1), 500.0, 5, UK),
    ]
    d = make(tmp_path, pad() + lines)
    assert weekly_row(d, W)["matched_cancelled_value"] == 5000.0


def test_two_pairs_largest_wins(tmp_path: Path) -> None:
    d = make(
        tmp_path,
        pad()
        + [
            order("600001", "20001", "MUG RED", 6, 500.0),
            order("C600002", "20001", "MUG RED", -6, 500.0),
            order("600003", "20002", "LAMP", 8, 500.0),
            order("C600004", "20002", "LAMP", -8, 500.0),
        ],
    )
    w = weekly_row(d, W)
    assert w["matched_cancelled_value"] == 7000.0
    assert (w["pc_cancelled"], w["pc_description"], w["pc_invoice"]) == (
        4000.0,
        "LAMP",
        "600003",
    )
    assert "Lamp, invoice 600003" in flag(row(d), "placed_cancelled").reason


def test_pair_tie_breaks_by_description_then_invoice(tmp_path: Path) -> None:
    pair_a = [
        order("600009", "20001", "ZEBRA MUG", 6, 500.0),
        order("C600010", "20001", "ZEBRA MUG", -6, 500.0),
    ]
    pair_b = [
        order("600003", "20002", "APPLE MUG", 6, 500.0),
        order("C600004", "20002", "APPLE MUG", -6, 500.0),
    ]
    d = make(tmp_path, pad() + pair_a + pair_b)
    assert weekly_row(d, W)["pc_description"] == "APPLE MUG"
    same_desc = [
        order("600009", "20001", "TWIN MUG", 6, 500.0),
        order("C600010", "20001", "TWIN MUG", -6, 500.0),
        order("600003", "20002", "TWIN MUG", 6, 500.0),
        order("C600004", "20002", "TWIN MUG", -6, 500.0),
    ]
    d2 = make(tmp_path, pad() + same_desc, name="d2")
    assert weekly_row(d2, W)["pc_invoice"] == "600003"


def test_largest_placed_line_invoice_ties_earliest(tmp_path: Path) -> None:
    first = order("600002", "20001", "MUG RED", 5, 500.0)
    second = (
        "600001",
        "20001",
        "MUG RED",
        5,
        at(date(2011, 9, 21)),
        500.0,
        5,
        UK,
    )
    d = make(
        tmp_path,
        pad() + [first, second, order("C600003", "20001", "MUG RED", -10, 500.0)],
    )
    assert weekly_row(d, W)["pc_invoice"] == "600002"


def _boundary(tmp_path: Path, cancel_qty: int, price: float, name: str) -> Path:
    return make(
        tmp_path,
        pad()
        + [
            order("600001", "20001", "MUG RED", 20, price),
            order("C600002", "20001", "MUG RED", -cancel_qty, price),
        ],
        name=name,
    )


def test_exactly_25_percent_is_not_placed_cancelled(tmp_path: Path) -> None:
    d = _boundary(tmp_path, 10, 50.0, "exact")
    r = row(d)
    assert r.revenue == 2000.0 and weekly_row(d, W)["pc_cancelled"] == 500.0
    assert "placed_cancelled" not in rules(r)
    assert "large_cancellations" in rules(r)
    assert "top_line" in rules(r)


def test_just_above_25_percent_is_placed_cancelled(tmp_path: Path) -> None:
    d = _boundary(tmp_path, 11, 50.0, "above")
    r = row(d)
    assert "placed_cancelled" in rules(r)
    assert "large_cancellations" not in rules(r)


def test_just_below_25_percent_is_neither_flag(tmp_path: Path) -> None:
    d = _boundary(tmp_path, 9, 50.0, "below")
    assert "placed_cancelled" not in rules(row(d))
    assert "large_cancellations" not in rules(row(d))


def test_top_line_suppressed_only_for_same_invoice_and_description(
    tmp_path: Path,
) -> None:
    big = order("700001", "30001", "BIG VASE", 12, 500.0)
    pair = [
        order("600001", "20001", "MUG RED", 10, 300.0),
        order("C600002", "20001", "MUG RED", -10, 300.0),
    ]
    d = make(tmp_path, pad() + [big] + pair)
    r = row(d)
    assert r.revenue == 10000.0
    assert "placed_cancelled" in rules(r) and "top_line" in rules(r)
    assert "invoice 700001" in flag(r, "top_line").reason

    same_invoice = [
        order("700001", "30001", "BIG VASE", 12, 500.0),
        order("700001", "20001", "MUG RED", 10, 300.0),
        order("C600002", "20001", "MUG RED", -10, 300.0),
    ]
    d2 = make(tmp_path, pad() + same_invoice, name="d2")
    assert {"placed_cancelled", "top_line"} <= set(rules(row(d2)))


def test_top_line_suppressed_when_same_line(tmp_path: Path) -> None:
    d = make(
        tmp_path,
        pad()
        + [
            order("700001", "30001", "BIG VASE", 12, 500.0),
            order("C700002", "30001", "BIG VASE", -12, 500.0),
        ],
    )
    r = row(d)
    assert "top_line" not in rules(r)
    assert flag(r, "placed_cancelled").reason.endswith("(Big Vase, invoice 700001)")


def test_large_cancellations_uses_unmatched_value_when_placed_cancelled_fires(
    tmp_path: Path,
) -> None:
    pair = [
        order("600001", "20001", "MUG RED", 10, 500.0),
        order("C600002", "20001", "MUG RED", -10, 500.0),
    ]
    small = order("C600003", "20002", "LAMP", -8, 50.0, cust=6)
    d = make(tmp_path, pad() + pair + [small])
    r = row(d)
    assert r.cancelled_value == 5400.0 and r.revenue == 6000.0
    assert "placed_cancelled" in rules(r)
    assert "large_cancellations" not in rules(r)


def test_large_cancellations_fires_on_unmatched_remainder(tmp_path: Path) -> None:
    pair = [
        order("600001", "20001", "MUG RED", 10, 500.0),
        order("C600002", "20001", "MUG RED", -10, 500.0),
    ]
    other = order("C600003", "20002", "LAMP", -40, 40.0, cust=6)
    d = make(tmp_path, pad() + pair + [other])
    r = row(d)
    assert r.revenue == 6000.0
    assert {"placed_cancelled", "large_cancellations"} <= set(rules(r))
    assert flag(r, "large_cancellations").reason.startswith(f"{money(6600)} cancelled")


def test_non_product_cancellation_never_matches(tmp_path: Path) -> None:
    d = make(
        tmp_path,
        pad()
        + [
            order("600001", "POST", "POSTAGE", 10, 500.0),
            order("C600002", "POST", "POSTAGE", -10, 500.0),
        ],
    )
    assert weekly_row(d, W)["matched_cancelled_value"] == 0.0


def test_pair_counts_per_filter_value(tmp_path: Path) -> None:
    d = make(
        tmp_path,
        pad()
        + [
            order("600001", "20001", "MUG RED", 10, 500.0, country="France"),
            order("C600002", "20001", "MUG RED", -10, 500.0, country="France"),
        ],
    )
    assert weekly_row(d, W, "France")["pc_cancelled"] == 5000.0
    assert weekly_row(d, W, OUTSIDE_UK)["pc_cancelled"] == 5000.0
    assert weekly_row(d, W, ALL)["pc_cancelled"] == 5000.0
    assert weekly_row(d, W, UK)["pc_cancelled"] == 0.0


def test_customer_id_not_in_outputs(tmp_path: Path) -> None:
    d = make(
        tmp_path,
        pad() + [order("600001", "20001", "MUG RED", 10, 500.0, cust=48213)],
    )
    for f in d.iterdir():
        assert b"48213" not in f.read_bytes()
    assert "Customer ID" not in pd.read_parquet(d / "weekly.parquet").columns


# ---------------------------------------------------------------- DEC-24


def items(f: Flag, by: str) -> list[tuple[str, float]]:
    return [(i.label, i.change) for dr in f.drivers if dr.by == by for i in dr.items]


def test_contributions_sum_to_total_change(tmp_path: Path) -> None:
    target = [
        order("800001", "20001", "MUG RED", 4, 500.0),
        order("800002", "20002", "LAMP", 2, 500.0),
        order("800003", "20003", "VASE", 1, 500.0),
    ]
    d = make(tmp_path, pad() + target)
    r = row(d)
    f = flag(r, "revenue_swing")
    total = r.net_revenue - 1000.0
    assert total == 3500.0
    prod = items(f, "product")
    assert prod == [("Mug Red", 2000.0), ("Lamp", 1000.0), ("Vase", 500.0)]
    assert sum(v for _, v in prod) == total
    pct_by = {dr.by: dr.explained_pct for dr in f.drivers}
    assert pct_by["product"] == pytest.approx(100.0)
    assert pct_by["country"] == pytest.approx(100.0)
    assert items(f, "country") == [(UK, 3500.0)]


def test_more_than_three_items_keeps_top_three(tmp_path: Path) -> None:
    target = [
        order("800001", "20001", "MUG RED", 4, 500.0),
        order("800002", "20002", "LAMP", 2, 500.0),
        order("800003", "20003", "VASE", 1, 500.0),
        order("800004", "20004", "BOWL", 1, 100.0),
    ]
    d = make(tmp_path, pad() + target)
    f = flag(row(d), "revenue_swing")
    drv = next(x for x in f.drivers if x.by == "product")
    assert [i.label for i in drv.items] == ["Mug Red", "Lamp", "Vase"]
    assert drv.explained_pct == pytest.approx(3500 / 3600 * 100)


def test_fewer_than_three_items(tmp_path: Path) -> None:
    d = make(tmp_path, pad() + [order("800001", "20001", "MUG RED", 4, 500.0)])
    f = flag(row(d), "revenue_swing")
    assert items(f, "product") == [("Mug Red", 2000.0)]
    assert next(x for x in f.drivers if x.by == "product").explained_pct == 100.0


def test_ties_broken_by_label_and_cut_at_three(tmp_path: Path) -> None:
    target = [
        order("800001", "20004", "DELTA", 2, 500.0),
        order("800002", "20003", "CHARLIE", 2, 500.0),
        order("800003", "20002", "BRAVO", 2, 500.0),
        order("800004", "20001", "ALPHA", 2, 500.0),
    ]
    d = make(tmp_path, pad() + target)
    f = flag(row(d), "revenue_swing")
    assert [lab for lab, _ in items(f, "product")] == ["Alpha", "Bravo", "Charlie"]


def test_negative_swing_picks_negative_items(tmp_path: Path) -> None:
    base_extra = [
        (f"Q{i}", "20001", "MUG RED", 10, at(w + timedelta(days=3)), 100.0, 5, UK)
        for i, w in enumerate(PAD_WEEKS[:4])
    ]
    other = order("800009", "20002", "LAMP", 1, 10.0)
    d = make(tmp_path, pad(target_qty=2) + base_extra + [other])
    r = row(d)
    assert r.net_revenue_vs4w is not None and r.net_revenue_vs4w < -40
    f = flag(r, "revenue_swing")
    total = r.net_revenue - 2000.0
    assert items(f, "product") == [
        ("Mug Red", -1000.0),
        ("Padding A", -180.0),
        ("Padding B", -180.0),
    ]
    assert all(v < 0 for _, v in items(f, "country"))
    drv = next(x for x in f.drivers if x.by == "product")
    assert drv.explained_pct == pytest.approx((-1360) / total * 100)
    assert total == pytest.approx(-1890.0)


def test_product_only_cancelled_in_base_weeks(tmp_path: Path) -> None:
    cancel = order("C800001", "20009", "OLD TEA", -10, 50.0, day=date(2011, 9, 14))
    target = order("800002", "20001", "MUG RED", 4, 500.0)
    d = make(tmp_path, pad() + [cancel, target])
    r = row(d)
    products = pd.read_parquet(d / "products.parquet")
    z = products[(products["stock_code"] == "20009") & (products["filter"] == ALL)]
    assert list(z["revenue"]) == [0.0] and list(z["cancelled_value"]) == [500.0]
    assert r.net_revenue_vs4w == pytest.approx((3000 - 875) / 875 * 100)
    f = flag(r, "revenue_swing")
    prod = items(f, "product")
    assert prod[0] == ("Mug Red", 2000.0)
    assert prod[1][0] == "Old Tea" and prod[1][1] == pytest.approx(125.0)
    assert sum(v for _, v in prod) == pytest.approx(2125.0)


def test_product_cancelled_this_week_lowers_its_contribution(tmp_path: Path) -> None:
    target = [
        order("800001", "20001", "MUG RED", 4, 500.0),
        order("800002", "20002", "LAMP", 4, 500.0),
        order("C800003", "20002", "LAMP", -2, 500.0, cust=9),
    ]
    d = make(tmp_path, pad() + target)
    prod = items(flag(row(d), "revenue_swing"), "product")
    assert prod == [("Mug Red", 2000.0), ("Lamp", 1000.0)]


def test_label_uses_latest_week_description(tmp_path: Path) -> None:
    old = order("800001", "20001", "MUG OLD NAME", 1, 100.0, day=date(2011, 9, 7))
    new = order("800002", "20001", "MUG NEW NAME", 4, 500.0)
    d = make(tmp_path, pad() + [old, new])
    prod = items(flag(row(d), "revenue_swing"), "product")
    assert prod[0][0] == "Mug New Name"


def _countries(tmp_path: Path) -> Path:
    target = [
        order("800001", "20001", "MUG RED", 4, 500.0, country="Germany"),
        order("800002", "20002", "LAMP", 2, 500.0, country="Spain"),
        order("800003", "20003", "VASE", 10, 500.0, country=UK),
    ]
    return make(tmp_path, pad(country="France") + target)


def test_outside_uk_excludes_united_kingdom(tmp_path: Path) -> None:
    d = _countries(tmp_path)
    r = row(d, country=OUTSIDE_UK)
    f = flag(r, "revenue_swing")
    assert items(f, "country") == [("Germany", 2000.0), ("Spain", 1000.0)]
    assert [x.by for x in f.drivers] == ["product", "country"]
    assert items(f, "product") == [("Mug Red", 2000.0), ("Lamp", 1000.0)]
    assert flag(r, "orders_swing").drivers[0].by == "country"
    assert [lab for lab, _ in items(flag(r, "orders_swing"), "country")] == [
        "Germany",
        "Spain",
    ]
    assert items(flag(r, "orders_swing"), "product") == []


def test_all_countries_includes_united_kingdom(tmp_path: Path) -> None:
    d = _countries(tmp_path)
    f = flag(row(d), "revenue_swing")
    assert items(f, "country") == [(UK, 5000.0), ("Germany", 2000.0), ("Spain", 1000.0)]
    assert items(f, "product")[0] == ("Vase", 5000.0)


def test_single_country_orders_swing_has_no_drivers(tmp_path: Path) -> None:
    d = make(
        tmp_path,
        pad(country="France")
        + [
            order("800001", "20001", "MUG RED", 4, 500.0, country="France"),
            order("800002", "20001", "MUG RED", 4, 500.0, country="France"),
        ],
    )
    r = row(d, country="France")
    assert flag(r, "orders_swing").drivers == []
    f = flag(r, "revenue_swing")
    assert [x.by for x in f.drivers] == ["product"]


def test_uk_filter_has_product_drivers_only(tmp_path: Path) -> None:
    d = make(tmp_path, pad() + [order("800001", "20001", "MUG RED", 4, 500.0)])
    r = row(d, country=UK)
    assert [x.by for x in flag(r, "revenue_swing").drivers] == ["product"]
    assert "orders_swing" not in rules(r) or flag(r, "orders_swing").drivers == []


def test_explained_pct_none_when_total_is_zero() -> None:
    w, base = date(2011, 9, 19), [date(2011, 9, 12)]
    values = pd.Series(
        [10.0, 10.0],
        index=pd.MultiIndex.from_tuples([(w, "a"), (base[0], "a")]),
    )
    result = top_drivers("product", values, w, base, {}, 0.0)
    assert result.explained_pct is None and result.items == []


def test_non_swing_flags_have_no_drivers(tmp_path: Path) -> None:
    d = make(
        tmp_path,
        pad()
        + [
            order("600001", "20001", "MUG RED", 10, 500.0),
            order("C600002", "20001", "MUG RED", -10, 500.0),
        ],
    )
    for f in row(d).flags:
        if f.rule not in ("revenue_swing", "orders_swing"):
            assert f.drivers == []


# ---------------------------------------------------------------- DEC-23


def yoy_data(tmp_path: Path, base: Line | None, **kw: Any) -> Path:
    return make(tmp_path, pad() + ([base] if base else []), **kw)


def base_line(day: datetime, qty: int = 10, price: float = 6.0) -> Line:
    return ("400100", "20001", "MUG RED", qty, day, price, 90005, UK)


def test_yoy_base_is_exactly_364_days_earlier(tmp_path: Path) -> None:
    assert W - timedelta(days=364) == date(2010, 9, 20)
    for i, (when, hit) in enumerate(
        [
            (datetime(2010, 9, 20, 0, 0), True),
            (datetime(2010, 9, 26, 23, 59), True),
            (datetime(2010, 9, 19, 23, 59), False),
            (datetime(2010, 9, 27, 0, 0), False),
            (datetime(2010, 9, 13, 10), False),
        ]
    ):
        d = yoy_data(tmp_path, base_line(when), name=f"d{i}")
        r = row(d)
        assert (r.net_revenue_yoy is not None) is hit, when
        if hit:
            assert r.net_revenue_yoy == pytest.approx((1000 - 60) / 60 * 100)
            assert r.orders_yoy == 0.0
            assert r.net_aov_yoy == pytest.approx((1000 - 60) / 60 * 100)


def test_yoy_none_for_partial_week(tmp_path: Path) -> None:
    lines = pad(skip=()) + [base_line(datetime(2010, 9, 21, 10))]
    d = make(tmp_path, lines, with_end=False)
    r = row(d)
    assert "partial_week" in rules(r)
    assert (r.net_revenue_yoy, r.orders_yoy, r.net_aov_yoy) == (None, None, None)
    assert r.net_revenue_wow is not None


def test_yoy_present_when_data_ends_on_sunday(tmp_path: Path) -> None:
    end = ("E2", "10002", "END", 1, datetime(2011, 9, 25, 23, 0), 1.0, 2, UK)
    d = make(
        tmp_path,
        pad() + [base_line(datetime(2010, 9, 21, 10)), end],
        with_end=False,
    )
    r = row(d)
    assert "partial_week" not in rules(r)
    assert r.net_revenue_yoy is not None


def test_yoy_none_when_base_has_zero_sales(tmp_path: Path) -> None:
    d = yoy_data(tmp_path, base_line(datetime(2010, 9, 21, 10), price=0.0))
    r = row(d)
    assert r.net_revenue_yoy is None and r.orders_yoy is None and r.net_aov_yoy is None


def test_yoy_none_when_base_net_is_negative(tmp_path: Path) -> None:
    cancel = (
        "C400101",
        "20001",
        "MUG RED",
        -10,
        datetime(2010, 9, 22, 10),
        30.0,
        7,
        UK,
    )
    d = make(
        tmp_path,
        pad() + [base_line(datetime(2010, 9, 21, 10)), cancel],
        name="neg2",
    )
    r = row(d)
    assert r.net_revenue_yoy is None
    assert r.orders_yoy == 0.0
    assert r.net_aov_yoy is None


def test_yoy_none_when_base_week_has_only_cancellations(tmp_path: Path) -> None:
    cancel = (
        "C400101",
        "20001",
        "MUG RED",
        -10,
        datetime(2010, 9, 22, 10),
        30.0,
        7,
        UK,
    )
    d = make(tmp_path, pad() + [cancel])
    r = row(d)
    assert (r.net_revenue_yoy, r.orders_yoy, r.net_aov_yoy) == (None, None, None)


def test_yoy_none_when_this_week_has_no_sales(tmp_path: Path) -> None:
    d = make(
        tmp_path,
        pad(skip=(W,)) + [base_line(datetime(2010, 9, 21, 10))],
    )
    r = row(d)
    assert r.product_lines == 0
    assert (r.net_revenue_yoy, r.orders_yoy, r.net_aov_yoy) == (None, None, None)
    assert r.net_aov is None and r.aov is None
    assert rules(r) == ["no_data"]


def test_yoy_orders_and_aov_values(tmp_path: Path) -> None:
    base = [
        base_line(datetime(2010, 9, 21, 10)),
        ("400101", "20002", "LAMP", 1, datetime(2010, 9, 22, 10), 40.0, 90006, UK),
    ]
    d = make(tmp_path, pad() + base)
    r = row(d)
    assert r.orders_yoy == pytest.approx(-50.0)
    assert r.net_revenue_yoy == pytest.approx((1000 - 100) / 100 * 100)
    assert r.net_aov_yoy == pytest.approx((1000 - 50) / 50 * 100)


def test_yoy_per_country_filter(tmp_path: Path) -> None:
    france_old = (
        "400100",
        "20001",
        "MUG RED",
        10,
        datetime(2010, 9, 21, 10),
        6.0,
        3,
        "France",
    )
    france_new = order("800001", "20001", "MUG RED", 5, 30.0, cust=3, country="France")
    d = make(tmp_path, pad() + [france_old, france_new])
    assert row(d, country=UK).net_revenue_yoy is None
    assert row(d, country="France").net_revenue_yoy == pytest.approx(
        150 / 60 * 100 - 100
    )
    assert row(d).net_revenue_yoy == pytest.approx((1150 - 60) / 60 * 100)


def test_yoy_in_csv_empty_when_none(tmp_path: Path) -> None:
    d = make(tmp_path, pad())
    csv_text = core.weekly_csv(scen(d)).decode()
    last = csv_text.strip().split("\n")[-1].split(",")
    assert last[-3:] == ["", "", ""]


# ---------------------------------------------------------------- DEC-26


def test_headline_n_a_both_and_no_flags(tmp_path: Path) -> None:
    d = make(tmp_path, pad())
    s = scen(d)
    assert (
        s.headline
        == "Net revenue £1\u202f000, +0.0% vs last week, n/a vs same week last year; no flags."
    )


def test_headline_exactly_one_flag(tmp_path: Path) -> None:
    extra = ("P0919", "20001", "MUG RED", 13, at(date(2011, 9, 21)), 30.0, 1, UK)
    d = make(tmp_path, pad() + [extra])
    r = row(d)
    assert rules(r) == ["top_line"], rules(r)
    assert scen(d).headline.endswith("; 1 flag.")
    assert "1 flags" not in scen(d).headline


def test_headline_plural_flags(tmp_path: Path) -> None:
    d = make(tmp_path, pad() + [order("600001", "20001", "MUG RED", 10, 500.0)])
    r = row(d)
    assert len(r.flags) >= 2
    assert scen(d).headline.endswith(f"; {len(r.flags)} flags.")


def test_headline_n_a_last_week_when_previous_week_empty(tmp_path: Path) -> None:
    d = make(tmp_path, pad(skip=(date(2011, 9, 12),)))
    h = scen(d).headline
    assert ", n/a vs last week, n/a vs same week last year; no flags." in h


def test_headline_partial_week_suffix(tmp_path: Path) -> None:
    d = make(tmp_path, pad(), with_end=False)
    r = row(d)
    assert "partial_week" in rules(r)
    assert scen(d).headline == (
        f"Net revenue {money(1000)} (partial week), {change(0.0)} vs last week, n/a vs same week last year; 1 flag."
    )


def test_headline_no_sales(tmp_path: Path) -> None:
    d = make(tmp_path, pad(skip=(W,)))
    assert scen(d).headline == "No sales this week."


def test_headline_negative_net_revenue(tmp_path: Path) -> None:
    d = make(
        tmp_path,
        pad(skip=(W,))
        + [
            order("600001", "20001", "MUG RED", 1, 10.0),
            order("C600002", "20002", "LAMP", -5, 100.0, cust=9),
        ],
    )
    assert scen(d).headline.startswith(f"Net revenue {money(-490)},")


def test_headline_uses_selected_week_in_longer_range(tmp_path: Path) -> None:
    d = make(tmp_path, pad())
    s = scen(d, W, start=date(2011, 8, 22))
    assert s.headline == scen(d, W).headline
    assert len(s.weeks) == 5


# ---------------------------------------------------------------- committed data

DERIVED = Path(core.DATA_DIR)
FILTERS = [ALL, UK, OUTSIDE_UK]


def test_real_no_customer_id_column_or_values() -> None:
    allowed = {"customers", "new_customers", "lines_without_customer_id"}
    for name in ("weekly", "products"):
        frame = pd.read_parquet(DERIVED / f"{name}.parquet")
        for col in frame.columns:
            low = col.lower().replace("_", " ")
            assert low != "customer id" and "customerid" not in low
            assert "customer" not in low or col in allowed, col
        for col in frame.select_dtypes(include=["object", "str"]).columns:
            assert not frame[col].astype(str).str.match(r"^\d{5}\.0$").any(), col
    for f in ("meta.json", "summaries.json"):
        assert "customer id" not in (DERIVED / f).read_text().lower()


def test_real_no_customer_id_in_pc_columns() -> None:
    weekly = pd.read_parquet(DERIVED / "weekly.parquet")
    for col in ("pc_invoice", "pc_description", "top_line_invoice"):
        assert not weekly[col].astype(str).str.fullmatch(r"1[2-8]\d{3}(\.0)?").any()


def test_real_products_cancelled_value_reconciles_with_weekly() -> None:
    weekly = pd.read_parquet(DERIVED / "weekly.parquet")
    products = pd.read_parquet(DERIVED / "products.parquet")
    per_week = products.groupby(["filter", "week_start"])["cancelled_value"].sum()
    w = weekly.set_index(["filter", "week_start"])["cancelled_value"]
    shown = set(pd.to_datetime(products["week_start"]).unique())
    assert shown <= set(PRODUCT_WEEKS) and len(shown) >= 56
    assert len(PRODUCT_WEEKS) == 53 + 4
    joined = per_week.to_frame("p").join(w.rename("w"), how="left")
    assert joined["w"].notna().all()
    assert np.allclose(joined["p"], joined["w"], atol=0.01)
    missing = w.loc[
        [i for i in w.index if pd.Timestamp(i[1]) in set(PRODUCT_WEEKS)]
    ].index.difference(per_week.index)
    assert (w.loc[missing] == 0).all()


def test_real_products_revenue_reconciles_with_weekly() -> None:
    weekly = pd.read_parquet(DERIVED / "weekly.parquet")
    products = pd.read_parquet(DERIVED / "products.parquet")
    per_week = products.groupby(["filter", "week_start"])["revenue"].sum()
    w = weekly.set_index(["filter", "week_start"])["revenue"]
    assert np.allclose(per_week, w.loc[per_week.index], atol=0.01)


def contributions(
    frame: pd.DataFrame, item: str, value: pd.Series, week: date, base: list[date]
) -> float:
    by = value.groupby([frame["week_start"], frame[item]]).sum().unstack(fill_value=0)
    by = by.reindex([week, *base], fill_value=0)
    return float((by.iloc[0] - by.iloc[1:].mean()).sum())


def swing_cases(country: str) -> list[tuple[WeekRow, Flag, list[date], float]]:
    """Every revenue swing flag of the full year with its base weeks and the true change net revenue - mean(base net revenue)."""
    data = core.load(DERIVED, max(f.stat().st_mtime_ns for f in DERIVED.iterdir()))
    s = run_scenario(
        Filters(
            start=date(2010, 12, 6),
            end=date(2011, 12, 5),
            country=country,
            week=date(2011, 12, 5),
        ),
        DERIVED,
    )
    weekly = data.weekly[data.weekly["filter"] == country].set_index("week_start")
    net = weekly["revenue"] - weekly["cancelled_value"]
    out = []
    for w in s.weeks:
        for f in w.flags:
            if f.rule == "revenue_swing":
                base = [
                    b
                    for n in range(1, 5)
                    if weekly["product_lines"].loc[
                        b := w.week_start - timedelta(days=7 * n)
                    ]
                    > 0
                ]
                out.append(
                    (
                        w,
                        f,
                        base,
                        float(
                            net.loc[w.week_start] - np.mean([net.loc[b] for b in base])
                        ),
                    )
                )
    return out


@pytest.mark.parametrize("country", FILTERS)
def test_real_product_driver_sums_equal_net_change(country: str) -> None:
    data = core.load(DERIVED, max(f.stat().st_mtime_ns for f in DERIVED.iterdir()))
    cases = swing_cases(country)
    assert cases
    for w, f, base, total in cases:
        p = data.products[
            (data.products["filter"] == country)
            & data.products["week_start"].isin([w.week_start, *base])
        ]
        full = contributions(
            p, "stock_code", p["revenue"] - p["cancelled_value"], w.week_start, base
        )
        assert full == pytest.approx(total, abs=0.01), (w.week_start, country)
        drv = next(d for d in f.drivers if d.by == "product")
        got = sum(i.change for i in drv.items)
        assert len(drv.items) <= 3
        assert all(i.change * total > 0 for i in drv.items)
        mags = [abs(i.change) for i in drv.items]
        assert mags == sorted(mags, reverse=True)
        assert drv.explained_pct == pytest.approx(got / total * 100)


@pytest.mark.parametrize("country", [ALL, OUTSIDE_UK])
def test_real_country_driver_explained_pct_uses_true_change(country: str) -> None:
    for _, f, _, total in swing_cases(country):
        drv = next(d for d in f.drivers if d.by == "country")
        got = sum(i.change for i in drv.items)
        assert drv.explained_pct == pytest.approx(got / total * 100)
        assert all(i.change * total > 0 for i in drv.items)
        assert country == ALL or all(i.label != UK for i in drv.items)


def test_real_flags_have_drivers_only_on_swings() -> None:
    s = run_scenario(
        Filters(start=date(2010, 12, 6), end=date(2011, 12, 5), week=date(2011, 12, 5)),
        DERIVED,
    )
    for f in s.flags:
        if f.rule == "revenue_swing":
            assert [d.by for d in f.drivers] == ["product", "country"]
        elif f.rule == "orders_swing":
            assert [d.by for d in f.drivers] == ["country"]
        else:
            assert f.drivers == []


def test_real_105_weeks_per_filter_and_pc_consistency() -> None:
    weekly = pd.read_parquet(DERIVED / "weekly.parquet")
    assert (weekly.groupby("filter").size() == 105).all()
    assert (weekly["matched_cancelled_value"] >= weekly["pc_cancelled"] - 1e-9).all()
    assert (weekly["pc_placed"] >= weekly["pc_cancelled"] - 1e-9).all()
    assert (weekly["matched_cancelled_value"] <= weekly["cancelled_value"] + 0.01).all()
    meta = json.loads((DERIVED / "meta.json").read_text())
    assert meta["countries"][:3] == [ALL, UK, OUTSIDE_UK]


def test_real_headline_has_fixed_shape_every_week() -> None:
    shape = re.compile(
        r"^(No sales this week\.|Net revenue -?£[\d\s]+( \(partial week\))?, (n/a|[+-][\d\s.]+%) vs last week, (n/a|[+-][\d\s.]+%) vs same week last year; (no flags|1 flag|\d+ flags)\.)$"
    )
    for w in (
        date(2010, 12, 27),
        date(2011, 1, 17),
        date(2011, 11, 28),
        date(2011, 12, 5),
    ):
        h = run_scenario(Filters(start=w, end=w, week=w), DERIVED).headline
        assert shape.match(h), h
