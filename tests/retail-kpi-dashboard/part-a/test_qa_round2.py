import os
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from kpi import core
from kpi.build import build
from kpi.core import run_scenario, swing
from kpi.data import COLUMNS
from kpi.fmt import change, count, grouped, money, rounded
from kpi.models import ALL, FIRST_WEEK, FLAG_LABELS, LAST_WEEK, UK, Filters, Scenario

N = " "
W = date(2011, 9, 19)
DATA_DIR = Path(os.environ.get("QA_DATA_DIR", core.DATA_DIR))
RULES = [
    "no_data",
    "partial_week",
    "revenue_swing",
    "orders_swing",
    "large_cancellations",
    "top_line",
    "placed_cancelled",
]


def lines(
    day: date,
    n: int = 1,
    price: float = 10.0,
    country: str = UK,
    tag: str = "",
) -> list[tuple[Any, ...]]:
    """n product lines, one invoice each, on a Monday-based week of `day`."""
    when = datetime(day.year, day.month, day.day, 10)
    return [
        (
            f"5{day:%y%m%d}{tag}{i:04d}",
            "20001",
            "MUG",
            1,
            when,
            price,
            float(1000 + i),
            country,
        )
        for i in range(n)
    ]


def built(tmp_path: Path, rows: list[tuple[Any, ...]]) -> Path:
    out = tmp_path / "d"
    build(pd.DataFrame(rows, columns=COLUMNS), out)
    return out


def scen(out: Path, country: str = ALL, week: date = W) -> Scenario:
    return run_scenario(Filters(start=week, end=week, country=country, week=week), out)


def reason(s: Scenario, rule: str) -> str:
    return next(f.reason for f in s.selected.flags if f.rule == rule)


def rules(s: Scenario) -> list[str]:
    return [f.rule for f in s.selected.flags]


# -------------------------------------------------------------- window


def test_base_uses_only_weeks_inside_the_4_week_window(tmp_path: Path) -> None:
    rows = (
        lines(date(2011, 7, 4), price=1000.0)  # 11 weeks back: outside window
        + lines(date(2011, 8, 22), price=200.0)  # exactly 4 weeks back: inside
        + lines(date(2011, 9, 12), price=100.0)
        + lines(date(2011, 9, 19), price=500.0)
    )
    s = scen(built(tmp_path, rows))
    assert s.selected.net_revenue_vs4w == pytest.approx((500 - 150) / 150 * 100)
    assert (
        reason(s, "revenue_swing")
        == "Net revenue +233.3% vs 4-week average (£500 vs £150)"
    )


def test_week_five_back_is_outside_window(tmp_path: Path) -> None:
    rows = (
        lines(date(2011, 8, 15), price=1000.0)  # 5 weeks back
        + lines(date(2011, 9, 12), price=100.0)
        + lines(date(2011, 9, 19), price=500.0)
    )
    s = scen(built(tmp_path, rows))
    assert s.selected.net_revenue_vs4w == pytest.approx(400.0)
    assert "vs 4-week average (£500 vs £100)" in reason(s, "revenue_swing")


def test_empty_weeks_in_window_are_excluded_not_counted_as_zero(
    tmp_path: Path,
) -> None:
    rows = (
        lines(date(2011, 8, 29), price=100.0)
        + lines(date(2011, 9, 12), price=100.0)
        + lines(date(2011, 9, 19), price=500.0)
    )
    s = scen(built(tmp_path, rows))
    assert s.selected.net_revenue_vs4w == pytest.approx(400.0)


def test_two_weeks_after_a_gap_swing_is_back(tmp_path: Path) -> None:
    rows = (
        lines(date(2011, 8, 29), price=100.0)
        + lines(date(2011, 9, 12), price=100.0)
        + lines(date(2011, 9, 19), price=500.0)
    )
    out = built(tmp_path, rows)
    after_gap = scen(out, week=date(2011, 9, 12))
    assert after_gap.selected.net_revenue_vs4w == pytest.approx(0.0)
    assert not {"revenue_swing", "orders_swing"} & set(rules(after_gap))
    s = scen(out)
    assert "revenue_swing" in rules(s)


def test_week_after_no_data_has_value_but_no_swing_flag(tmp_path: Path) -> None:
    rows = lines(date(2011, 8, 29), price=100.0) + lines(date(2011, 9, 12), price=900.0)
    s = scen(built(tmp_path, rows), week=date(2011, 9, 12))
    assert s.selected.net_revenue_vs4w == pytest.approx(800.0)
    assert not {"revenue_swing", "orders_swing"} & set(rules(s))
    gap = scen(built(tmp_path / "x", rows), week=date(2011, 9, 5))
    assert rules(gap) == ["no_data"]


def test_vs4w_none_without_any_earlier_week_with_lines(tmp_path: Path) -> None:
    s = scen(built(tmp_path, lines(W, price=500.0)))
    assert s.selected.net_revenue_vs4w is None
    assert s.selected.orders_vs4w is None
    assert not {"revenue_swing", "orders_swing"} & set(rules(s))


def test_vs4w_none_when_only_week_with_lines_is_five_back(tmp_path: Path) -> None:
    rows = lines(date(2011, 8, 15)) + lines(W)
    s = scen(built(tmp_path, rows))
    assert s.selected.net_revenue_vs4w is None


def test_no_data_week_has_no_swing_even_with_base(tmp_path: Path) -> None:
    rows = lines(date(2011, 9, 5), n=3) + lines(date(2011, 9, 19), n=3)
    out = built(tmp_path, rows)
    s = scen(out, week=date(2011, 9, 12))
    assert rules(s) == ["no_data"]
    assert s.selected.net_revenue_vs4w == pytest.approx(-100.0)


# -------------------------------------------------------------- first shown week


def test_first_shown_week_uses_hidden_base_weeks(tmp_path: Path) -> None:
    rows = (
        lines(date(2010, 11, 8), price=300.0)
        + lines(date(2010, 11, 15), price=100.0)
        + lines(date(2010, 11, 29), price=200.0)
        + lines(FIRST_WEEK, price=60.0)
    )
    s = scen(built(tmp_path, rows), week=FIRST_WEEK)
    assert s.selected.net_revenue_vs4w == pytest.approx(-70.0)
    assert (
        reason(s, "revenue_swing")
        == "Net revenue -70.0% vs 4-week average (£60 vs £200)"
    )
    assert s.weeks[0].week_start == FIRST_WEEK


def test_first_shown_week_after_empty_hidden_week_has_no_swing(
    tmp_path: Path,
) -> None:
    rows = lines(date(2010, 11, 22), price=300.0) + lines(FIRST_WEEK, price=60.0)
    s = scen(built(tmp_path, rows), week=FIRST_WEEK)
    assert s.selected.net_revenue_vs4w == pytest.approx(-80.0)
    assert not {"revenue_swing", "orders_swing"} & set(rules(s))


def test_build_has_105_weeks_per_filter(tmp_path: Path) -> None:
    rows = lines(W, country="Germany") + lines(W)
    out = built(tmp_path, rows)
    w = pd.read_parquet(out / "weekly.parquet")
    sizes = w.groupby("filter").size()
    assert set(sizes) == {105}
    assert pd.to_datetime(w["week_start"]).min() == pd.Timestamp("2009-12-07")
    assert pd.to_datetime(w["week_start"]).max() == pd.Timestamp(LAST_WEEK)


def test_hidden_week_lines_not_counted_in_totals(tmp_path: Path) -> None:
    rows = lines(date(2010, 11, 8), n=5) + lines(FIRST_WEEK, n=2)
    s = run_scenario(
        Filters(start=FIRST_WEEK, end=FIRST_WEEK, country=ALL, week=FIRST_WEEK),
        built(tmp_path, rows),
    )
    assert s.totals.orders == 2
    assert s.totals.weeks == 1


# -------------------------------------------------------------- formatting in reasons


def test_revenue_base_thousands_grouping(tmp_path: Path) -> None:
    rows = lines(date(2011, 9, 12), price=12345.0) + lines(W, price=30000.0)
    s = scen(built(tmp_path, rows))
    assert reason(s, "revenue_swing") == (
        f"Net revenue +143.0% vs 4-week average (£30{N}000 vs £12{N}345)"
    )


@pytest.mark.parametrize(
    ("base_orders", "text"),
    [
        (
            [1000, 1001, 1000, 1000],
            f"1{N}000",
        ),  # mean 1000.25: whole number at ≥ 10 (round 3)
        ([1000, 1000, 1001, 1001], f"1{N}001"),  # 1000.5 half-up, not half-even
        ([1001, 1001, 1001, 1000], f"1{N}001"),  # 1000.75
        ([1000, 1000, 1000, 1000], f"1{N}000"),
    ],
)
def test_orders_base_whole_number_half_up_with_grouping(
    tmp_path: Path, base_orders: list[int], text: str
) -> None:
    rows: list[tuple[Any, ...]] = []
    for i, n in enumerate(base_orders):
        rows += lines(date(2011, 8, 22) + timedelta(days=7 * i), n=n, price=1.0)
    rows += lines(W, n=3000, price=1.0)
    s = scen(built(tmp_path, rows))
    base = Decimal(sum(base_orders)) / 4
    expected_change = change((3000 - float(base)) / float(base) * 100)
    assert reason(s, "orders_swing") == (
        f"Orders {expected_change} vs 4-week average (3{N}000 vs {text})"
    )


def test_orders_reason_matches_helper_formatting() -> None:
    assert grouped(rounded(1000.25, "0.1")) == f"1{N}000.3"
    assert count(3000) == f"3{N}000"
    assert money(12345) == f"£12{N}345"


@pytest.mark.parametrize(
    ("value", "flagged"),
    [
        (39.949, False),
        (39.95, True),
        (-39.95, True),
        (-39.949, False),
        (40.0, True),
        (1e9, True),
        (0.0, False),
    ],
)
def test_swing_rounding_edge(value: float, flagged: bool) -> None:
    assert swing(value) is flagged


@pytest.mark.parametrize(
    ("now", "flagged"),
    [
        (139.94, False),
        (139.95, True),
        (140.0, True),
        (60.0, True),
        (60.05, True),
        (60.06, False),
    ],
)
def test_revenue_swing_threshold_through_build(
    tmp_path: Path, now: float, flagged: bool
) -> None:
    rows = lines(date(2011, 9, 12), price=100.0) + lines(W, price=now)
    s = scen(built(tmp_path, rows))
    assert ("revenue_swing" in rules(s)) is flagged


def test_swing_flags_ordered_between_partial_and_cancellations(
    tmp_path: Path,
) -> None:
    rows = lines(date(2011, 9, 12), price=100.0) + lines(W, price=500.0)
    s = scen(built(tmp_path, rows))
    got = rules(s)
    assert got == sorted(got, key=RULES.index)
    assert got == ["partial_week", "revenue_swing", "top_line"]


# -------------------------------------------------------------- single country


def test_single_country_uses_its_own_sparse_base(tmp_path: Path) -> None:
    rows = (
        lines(date(2011, 8, 22), price=100.0, country="Germany")
        + lines(date(2011, 9, 12), price=300.0, country="Germany")
        + lines(date(2011, 9, 5), price=5000.0)
        + lines(date(2011, 8, 29), price=5000.0)
        + lines(W, price=50.0, country="Germany")
    )
    out = built(tmp_path, rows)
    s = scen(out, country="Germany")
    assert s.selected.net_revenue_vs4w == pytest.approx((50 - 200) / 200 * 100)
    assert (
        reason(s, "revenue_swing")
        == "Net revenue -75.0% vs 4-week average (£50 vs £200)"
    )


def test_single_country_previous_week_empty_for_that_country_no_swing(
    tmp_path: Path,
) -> None:
    rows = (
        lines(date(2011, 8, 29), price=100.0, country="Germany")
        + lines(date(2011, 9, 12), price=5000.0)
        + lines(W, price=500.0, country="Germany")
    )
    out = built(tmp_path, rows)
    de = scen(out, country="Germany")
    assert de.selected.net_revenue_vs4w == pytest.approx(400.0)
    assert not {"revenue_swing", "orders_swing"} & set(rules(de))
    assert "revenue_swing" in rules(scen(out, country=ALL))


def test_single_country_without_any_base_is_none(tmp_path: Path) -> None:
    rows = lines(date(2011, 9, 12)) + lines(W, country="Germany")
    s = scen(built(tmp_path, rows), country="Germany")
    assert s.selected.net_revenue_vs4w is None
    assert s.selected.orders_vs4w is None


def test_data_end_is_a_date_from_latest_line(tmp_path: Path) -> None:
    rows = lines(date(2011, 9, 12)) + lines(W) + lines(date(2011, 9, 21))
    s = scen(built(tmp_path, rows))
    assert s.data_end == date(2011, 9, 21)
    assert type(s.data_end) is date


def test_partial_week_still_gets_swing_against_average(tmp_path: Path) -> None:
    rows = lines(date(2011, 9, 12), price=100.0) + lines(date(2011, 9, 19), price=500.0)
    s = scen(built(tmp_path, rows))
    assert s.data_end == date(2011, 9, 19)
    assert rules(s)[:2] == ["partial_week", "revenue_swing"]


# -------------------------------------------------------------- real data


def full(country: str) -> Scenario:
    return run_scenario(
        Filters(start=FIRST_WEEK, end=LAST_WEEK, country=country, week=LAST_WEEK),
        DATA_DIR,
    )


@pytest.fixture(scope="module")
def weekly() -> pd.DataFrame:
    w = pd.read_parquet(DATA_DIR / "weekly.parquet")
    w["week_start"] = pd.to_datetime(w["week_start"]).dt.date
    return w


def test_flag_labels_keys_are_all_rule_names() -> None:
    assert list(FLAG_LABELS) == RULES
    assert all(isinstance(v, str) and v for v in FLAG_LABELS.values())


def test_real_data_end_is_2011_12_09() -> None:
    s = full(ALL)
    assert s.data_end == date(2011, 12, 9)
    assert type(s.data_end) is date


def test_real_weekly_has_105_weeks_per_filter(weekly: pd.DataFrame) -> None:
    sizes = weekly.groupby("filter").size()
    assert set(sizes) == {105}
    assert weekly["week_start"].min() == date(2009, 12, 7)


def test_real_vs4w_and_swing_flags_recomputed_independently(
    weekly: pd.DataFrame,
) -> None:
    for name, g in weekly.groupby("filter"):
        s = full(str(name))
        by_week = g.set_index("week_start")
        for w in s.weeks:
            prev = [w.week_start - timedelta(days=7 * n) for n in range(1, 5)]
            base = by_week.loc[prev]
            base = base[base["product_lines"] > 0].assign(
                net=lambda b: b["revenue"] - b["cancelled_value"]
            )
            now = by_week.loc[w.week_start]
            now = pd.concat(
                [now, pd.Series({"net": now["revenue"] - now["cancelled_value"]})]
            )
            for field, col in (
                ("net_revenue_vs4w", "net"),
                ("orders_vs4w", "orders"),
            ):
                got = getattr(w, field)
                if base.empty or base[col].mean() <= 0:
                    assert got is None, (name, w.week_start, field)
                else:
                    exp = (now[col] - base[col].mean()) / base[col].mean() * 100
                    assert got == pytest.approx(exp, abs=1e-9), (name, w.week_start)
            prev_lines = by_week["product_lines"].loc[w.week_start - timedelta(days=7)]
            ok = now["product_lines"] > 0 and prev_lines > 0
            for rule, val in (
                ("revenue_swing", w.net_revenue_vs4w),
                ("orders_swing", w.orders_vs4w),
            ):
                exp_flag = (
                    ok and val is not None and abs(float(rounded(val, "0.1"))) >= 40.0
                )
                assert (rule in [f.rule for f in w.flags]) is bool(exp_flag), (
                    name,
                    w.week_start,
                    rule,
                )


def test_real_flagged_reasons_use_independent_base(weekly: pd.DataFrame) -> None:
    g = weekly[weekly["filter"] == ALL].set_index("week_start")
    s = full(ALL)
    seen = 0
    for w in s.weeks:
        for f in w.flags:
            if f.rule not in ("revenue_swing", "orders_swing"):
                continue
            seen += 1
            base = g.loc[[w.week_start - timedelta(days=7 * n) for n in range(1, 5)]]
            base = base[base["product_lines"] > 0]
            if f.rule == "revenue_swing":
                net = base["revenue"] - base["cancelled_value"]
                tail = f"({money(w.net_revenue)} vs {money(float(net.mean()))})"
                head = f"Net revenue {change(w.net_revenue_vs4w)} vs 4-week average "
            else:
                mean = float(base["orders"].mean())
                tail = f"({count(w.orders)} vs {grouped(rounded(mean, '1' if mean >= 10 else '0.1'))})"
                head = f"Orders {change(w.orders_vs4w)} vs 4-week average "
            assert f.reason == head + tail
    assert seen >= 9


def test_real_nine_flagged_weeks_and_gap_neighbours() -> None:
    s = full(ALL)
    flagged = [w.week_start for w in s.weeks if w.flags]
    assert len(flagged) == 9
    by = {w.week_start: w for w in s.weeks}
    assert [f.rule for f in by[date(2010, 12, 27)].flags] == ["no_data"]
    assert not {"revenue_swing", "orders_swing"} & {
        f.rule for f in by[date(2011, 1, 3)].flags
    }
