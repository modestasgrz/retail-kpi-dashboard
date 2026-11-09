import csv
import io
import json
import os
import re
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from kpi import core
from kpi.core import run_scenario, swing, weekly_csv
from kpi.models import ALL, FIRST_WEEK, LAST_WEEK, OUTSIDE_UK, UK, Filters, Scenario

N = " "
RULE_ORDER = [
    "no_data",
    "partial_week",
    "revenue_swing",
    "orders_swing",
    "large_cancellations",
    "top_line",
]
ADDITIVE = [
    "revenue",
    "orders",
    "units",
    "product_lines",
    "lines_without_customer_id",
    "cancellation_invoices",
    "cancelled_value",
    "duplicate_lines",
    "cancellation_lines",
    "adjustment_lines",
    "non_product_lines",
    "non_positive_lines",
]
DATA_DIR = Path(os.environ.get("QA_DATA_DIR", core.DATA_DIR))
SHOWN = [FIRST_WEEK + timedelta(days=7 * i) for i in range(53)]


def full(country: str) -> Scenario:
    return run_scenario(
        Filters(start=FIRST_WEEK, end=LAST_WEEK, country=country, week=LAST_WEEK),
        DATA_DIR,
    )


@pytest.fixture(scope="module")
def weekly() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "weekly.parquet")


@pytest.fixture(scope="module")
def products() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "products.parquet")


@pytest.fixture(scope="module")
def names() -> list[str]:
    return core.countries(DATA_DIR)


@pytest.fixture(scope="module")
def scenarios(names: list[str]) -> dict[str, Scenario]:
    return {c: full(c) for c in names}


def test_derived_files_present_and_free_of_customer_columns(
    weekly: pd.DataFrame, products: pd.DataFrame
) -> None:
    assert {p.name for p in DATA_DIR.iterdir()} >= {
        "weekly.parquet",
        "products.parquet",
        "meta.json",
        "summaries.json",
    }
    for frame in (weekly, products):
        cols = {c.lower() for c in frame.columns}
        assert not {"customer id", "customer_id", "customerid", "customer"} & cols
    assert "Customer ID" not in (DATA_DIR / "meta.json").read_text()


def test_weekly_has_one_row_per_filter_and_week_and_no_nan(
    weekly: pd.DataFrame, names: list[str]
) -> None:
    assert weekly["filter"].nunique() == len(names)
    assert set(weekly["filter"]) == set(names)
    assert not weekly.duplicated(["filter", "week_start"]).any()
    assert weekly.groupby("filter").size().eq(54).all()
    assert weekly["week_start"].min() == pd.Timestamp("2010-11-29")
    assert weekly["week_start"].max() == pd.Timestamp(LAST_WEEK)
    assert (weekly["week_start"].dt.day_of_week == 0).all()
    numeric = weekly.drop(
        columns=["top_line_revenue", "top_line_description", "top_line_invoice"]
    ).select_dtypes("number")
    assert not numeric.isna().any().any()
    assert (numeric >= 0).all().all()


def test_meta_countries_order_and_data_end(names: list[str]) -> None:
    meta = json.loads((DATA_DIR / "meta.json").read_text())
    assert meta["countries"] == names
    assert names[:3] == [ALL, UK, OUTSIDE_UK]
    assert names[3:] == sorted(names[3:], key=str.casefold)
    assert UK not in names[3:] and len(set(names)) == len(names)
    assert meta["data_end"] == "2011-12-09T12:50:00"


def test_every_filter_shows_exactly_53_consecutive_weeks(
    scenarios: dict[str, Scenario],
) -> None:
    for c, s in scenarios.items():
        assert [w.week_start for w in s.weeks] == SHOWN, c
        assert s.totals.weeks == 53, c
        assert s.selected.week_start == LAST_WEEK, c


def test_net_revenue_returning_new_and_rates_hold_for_every_filter_and_week(
    scenarios: dict[str, Scenario],
) -> None:
    for c, s in scenarios.items():
        for w in s.weeks:
            tag = (c, w.week_start)
            assert w.net_revenue == pytest.approx(
                w.revenue - w.cancelled_value, abs=1e-6
            ), tag
            assert w.returning_customers >= 0, tag
            assert w.new_customers <= w.customers, tag
            assert w.returning_customers == w.customers - w.new_customers, tag
            assert w.cancelled_value >= -1e-9, tag
            assert w.revenue >= 0 and w.orders >= 0 and w.units >= 0, tag
            assert w.lines_without_customer_id <= w.product_lines, tag
            assert w.orders <= w.product_lines, tag
            assert w.customers <= w.product_lines - w.lines_without_customer_id, tag
            if w.orders:
                assert w.aov == pytest.approx(w.revenue / w.orders), tag
            else:
                assert w.aov is None and w.revenue == 0, tag
            if w.orders + w.cancellation_invoices:
                assert w.cancellation_rate is not None
                assert 0 <= w.cancellation_rate <= 100, tag
            else:
                assert w.cancellation_rate is None, tag


def test_totals_equal_sum_of_weeks_for_every_filter(
    scenarios: dict[str, Scenario],
) -> None:
    for c, s in scenarios.items():
        t = s.totals
        assert t.revenue == pytest.approx(sum(w.revenue for w in s.weeks)), c
        assert t.net_revenue == pytest.approx(
            t.revenue - t.cancelled_value, abs=1e-5
        ), c
        assert t.orders == sum(w.orders for w in s.weeks), c
        assert t.flagged_weeks == sum(1 for w in s.weeks if w.flags), c
        assert len(s.flags) == sum(len(w.flags) for w in s.weeks), c


@pytest.mark.parametrize("column", ADDITIVE)
def test_single_country_rows_sum_to_all_countries(
    weekly: pd.DataFrame, names: list[str], column: str
) -> None:
    singles = [c for c in names if c not in (ALL, OUTSIDE_UK)]
    everything = weekly[weekly["filter"] == ALL].set_index("week_start")[column]
    summed = weekly[weekly["filter"].isin(singles)].groupby("week_start")[column].sum()
    pd.testing.assert_series_equal(
        everything, summed, check_names=False, check_dtype=False, atol=1e-6, rtol=0
    )


@pytest.mark.parametrize("column", ADDITIVE)
def test_uk_plus_outside_uk_equals_all(weekly: pd.DataFrame, column: str) -> None:
    def pick(name: str) -> pd.Series:
        return weekly[weekly["filter"] == name].set_index("week_start")[column]

    pd.testing.assert_series_equal(
        pick(UK) + pick(OUTSIDE_UK),
        pick(ALL),
        check_names=False,
        check_dtype=False,
        atol=1e-6,
        rtol=0,
    )


def test_customers_are_bounded_not_additive(
    weekly: pd.DataFrame, names: list[str]
) -> None:
    def pick(name: str, column: str) -> pd.Series:
        return weekly[weekly["filter"] == name].set_index("week_start")[column]

    for column in ("customers", "new_customers"):
        a, u, o = pick(ALL, column), pick(UK, column), pick(OUTSIDE_UK, column)
        assert (a <= u + o).all()
        assert (a >= u).all() and (a >= o).all()
    singles = [c for c in names if c not in (ALL, OUTSIDE_UK)]
    biggest = (
        weekly[weekly["filter"].isin(singles)].groupby("week_start")["customers"].max()
    )
    assert (pick(ALL, "customers") >= biggest).all()


def test_products_table_reconciles_with_weekly(
    weekly: pd.DataFrame, products: pd.DataFrame
) -> None:
    keys = ["filter", "week_start"]
    by_week = products.groupby(keys)[["revenue", "units"]].sum()
    base = weekly.set_index(keys)[["revenue", "units"]]
    joined = base.join(by_week.add_suffix("_p"), how="left").fillna(0)
    assert (joined["revenue"] - joined["revenue_p"]).abs().max() < 1e-6
    assert (joined["units"] == joined["units_p"]).all()
    assert not products.duplicated([*keys, "stock_code"]).any()
    assert (products["revenue"] > 0).all()
    assert products["description"].notna().all()
    assert products["week_start"].min() >= pd.Timestamp("2010-11-29")


def test_products_all_equals_sum_of_countries_per_stock_code(
    products: pd.DataFrame, names: list[str]
) -> None:
    singles = [c for c in names if c not in (ALL, OUTSIDE_UK)]
    keys = ["week_start", "stock_code"]
    a = products[products["filter"] == ALL].groupby(keys)["revenue"].sum()
    b = products[products["filter"].isin(singles)].groupby(keys)["revenue"].sum()
    pd.testing.assert_series_equal(a, b, check_names=False, atol=1e-6, rtol=0)


def test_only_one_empty_week_and_it_is_flagged_no_data(
    scenarios: dict[str, Scenario],
) -> None:
    all_weeks = scenarios[ALL].weeks
    empty = [w.week_start for w in all_weeks if w.product_lines == 0]
    assert empty == [date(2010, 12, 27)]
    for w in all_weeks:
        has = "no_data" in [f.rule for f in w.flags]
        assert has is (w.product_lines == 0), w.week_start
    nxt = next(w for w in all_weeks if w.week_start == date(2011, 1, 3))
    assert nxt.revenue_wow is None and nxt.orders_wow is None
    zero = next(w for w in all_weeks if w.week_start == date(2010, 12, 27))
    assert (zero.aov, zero.revenue_wow) == (None, -100.0)


def test_first_shown_week_has_a_change_base(scenarios: dict[str, Scenario]) -> None:
    first = scenarios[ALL].weeks[0]
    assert first.week_start == FIRST_WEEK
    assert first.revenue_wow is not None and first.orders_wow is not None


def test_partial_week_only_on_last_week_for_every_filter(
    scenarios: dict[str, Scenario],
) -> None:
    for c, s in scenarios.items():
        partial = [f for f in s.flags if f.rule == "partial_week"]
        assert [f.week_start for f in partial] == [LAST_WEEK], c
        assert partial[0].reason == "Data ends 2011-12-09; the week is missing days", c


def test_flags_follow_rule_order_and_their_definitions(
    scenarios: dict[str, Scenario],
) -> None:
    for c, s in scenarios.items():
        for w in s.weeks:
            got = [f.rule for f in w.flags]
            assert got == sorted(got, key=RULE_ORDER.index), (c, w.week_start)
            assert len(got) == len(set(got))
            assert all(f.week_start == w.week_start for f in w.flags)
            assert ("revenue_swing" in got) is swing(w.revenue_wow), (c, w.week_start)
            assert ("orders_swing" in got) is swing(w.orders_wow), (c, w.week_start)
            big = w.revenue > 0 and w.cancelled_value >= 0.25 * w.revenue - 1e-9
            if "large_cancellations" in got:
                assert big, (c, w.week_start)
            for f in w.flags:
                assert f.reason and f.reason == f.reason.strip()
                assert not re.search(r"\d [\d]{3}\b", f.reason), f.reason


def test_flag_reasons_use_narrow_nbsp_for_thousands(
    scenarios: dict[str, Scenario],
) -> None:
    reason = next(
        f.reason
        for f in scenarios[ALL].flags
        if f.rule == "large_cancellations" and f.week_start == LAST_WEEK
    )
    assert reason == f"£172{N}782 cancelled against £483{N}725 revenue (35.7%)"


def test_top_lists_are_sorted_bounded_and_consistent(
    scenarios: dict[str, Scenario],
) -> None:
    for c, s in scenarios.items():
        for ranked in (s.top_products, s.top_countries):
            assert len(ranked) <= 5, c
            revs = [r.revenue for r in ranked]
            assert revs == sorted(revs, reverse=True), c
            assert all(r > 0 for r in revs), c
            assert all(r.label == r.label.strip() and r.label for r in ranked), c
        assert sum(r.revenue for r in s.top_countries) <= s.selected.revenue + 1e-6, c
        assert sum(r.revenue for r in s.top_products) <= s.selected.revenue + 1e-6, c
        if c not in (ALL, OUTSIDE_UK, UK):
            assert [r.label for r in s.top_countries] == (
                [c] if s.selected.revenue else []
            ), c
    assert UK not in [r.label for r in scenarios[OUTSIDE_UK].top_countries]
    assert scenarios[ALL].top_countries[0].label == UK


def test_sources_cover_all_ten_kpis_for_every_filter(
    scenarios: dict[str, Scenario],
) -> None:
    keys = {
        "revenue",
        "orders",
        "aov",
        "units",
        "customers",
        "new_customers",
        "returning_customers",
        "cancellation_rate",
        "cancelled_value",
        "net_revenue",
    }
    for c, s in scenarios.items():
        assert keys <= set(s.sources), c
        assert all(s.sources[k].strip() for k in keys), c


def test_range_subset_is_consistent_with_full_range() -> None:
    wide = full(ALL)
    narrow = run_scenario(
        Filters(
            start=date(2011, 9, 12),
            end=date(2011, 9, 26),
            country=ALL,
            week=date(2011, 9, 19),
        ),
        DATA_DIR,
    )
    by_week = {w.week_start: w for w in wide.weeks}
    assert [w.model_dump() for w in narrow.weeks] == [
        by_week[w.week_start].model_dump() for w in narrow.weeks
    ]
    assert narrow.totals.revenue == pytest.approx(sum(w.revenue for w in narrow.weeks))


def test_csv_full_year_has_53_rows_matching_scenario() -> None:
    s = full(ALL)
    table = list(csv.reader(io.StringIO(weekly_csv(s).decode("utf-8"))))
    assert len(table) == 54
    assert [r[0] for r in table[1:]] == [str(d) for d in SHOWN]
    assert {len(r) for r in table} == {17}
    for r, w in zip(table[1:], s.weeks, strict=True):
        assert float(r[1]) == pytest.approx(w.revenue, abs=0.0051)
        assert int(r[2]) == w.orders
        assert r[16] == "; ".join(f.rule for f in w.flags)
        assert (r[3] == "") is (w.aov is None)
        assert (r[14] == "") is (w.revenue_wow is None)
    assert "-0.00" not in weekly_csv(s).decode()


def test_saved_summaries_are_clean_and_match_weeks(
    scenarios: dict[str, Scenario],
) -> None:
    data = json.loads((DATA_DIR / "summaries.json").read_text(encoding="utf-8"))
    assert len(data) == 52
    assert set(data) <= {str(d) for d in SHOWN}
    assert "2010-12-27" not in data
    for week, item in data.items():
        assert set(item) == {"headline", "text"}, week
        assert item["headline"].strip() == item["headline"] and item["headline"], week
        assert item["text"].strip() == item["text"] and item["text"], week
        for part in (item["headline"], item["text"]):
            assert not re.search(r"\[F\d*\]", part), week
            assert not re.search(r"\d,\d{3}(?!\d)", part), week
            assert not re.search(r"\d \d{3}(?!\d)", part), week
            assert "\r" not in part and "\n\n\n" not in part
        assert not item["headline"].startswith("#")
    shown = {w.week_start for w in scenarios[ALL].weeks}
    assert {d for d in SHOWN if str(d) in data} <= shown


def test_summary_only_for_all_countries_and_weeks_with_sales() -> None:
    for week in (date(2011, 9, 19), date(2010, 12, 6), date(2011, 12, 5)):
        base = Filters(start=week, end=week, country=ALL, week=week)
        assert run_scenario(base, DATA_DIR).summary is not None
        for c in (UK, OUTSIDE_UK, "France"):
            assert (
                run_scenario(base.model_copy(update={"country": c}), DATA_DIR).summary
                is None
            )
    empty = date(2010, 12, 27)
    assert (
        run_scenario(
            Filters(start=empty, end=empty, country=ALL, week=empty), DATA_DIR
        ).summary
        is None
    )
