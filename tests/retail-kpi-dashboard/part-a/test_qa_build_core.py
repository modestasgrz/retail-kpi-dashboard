import csv
import io
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from kpi import core, download
from kpi.build import build
from kpi.core import run_scenario, weekly_csv
from kpi.data import COLUMNS, clean, read
from kpi.fmt import money2
from kpi.models import ALL, FIRST_WEEK, LAST_WEEK, OUTSIDE_UK, UK, Filters, Scenario

N = " "
W = date(2011, 9, 19)
PREV = date(2011, 9, 12)


def raw(rows: list[tuple[Any, ...]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=COLUMNS)


def row(
    invoice: str,
    when: datetime,
    qty: int = 1,
    price: float = 10.0,
    code: str = "20001",
    desc: str | None = "MUG",
    customer: float | None = 1.0,
    country: str = UK,
) -> tuple[Any, ...]:
    return (invoice, code, desc, qty, when, price, customer, country)


def at(day: int, hour: int = 10, month: int = 9) -> datetime:
    return datetime(2011, month, day, hour)


def built(tmp_path: Path, rows: list[tuple[Any, ...]], name: str = "d") -> Path:
    out = tmp_path / name
    build(raw(rows), out)
    return out


def scen(
    out: Path,
    country: str = ALL,
    week: date = W,
    start: date | None = None,
    end: date | None = None,
) -> Scenario:
    return run_scenario(
        Filters(start=start or week, end=end or week, country=country, week=week), out
    )


def rules(s: Scenario) -> list[str]:
    return [f.rule for f in s.selected.flags]


# ------------------------------------------------------------ bucket priority


@pytest.mark.parametrize(
    ("invoice", "code", "qty", "price", "bucket"),
    [
        ("500001", "85123A", 1, 1.0, "product"),
        ("500001", "85123a", 1, 1.0, "product"),
        ("500001", "85123AB", 1, 1.0, "product"),
        ("500001", "20001", 1, 0.01, "product"),
        ("500001", "POST", 1, 1.0, "non_product"),
        ("500001", "DCGS0001", 1, 1.0, "non_product"),
        ("500001", "M", 1, 1.0, "non_product"),
        ("500001", "2000", 1, 1.0, "non_product"),
        ("500001", "200011", 1, 1.0, "non_product"),
        ("500001", "85123A1", 1, 1.0, "non_product"),
        ("500001", " 85123A", 1, 1.0, "non_product"),
        ("500001", "85123 A", 1, 1.0, "non_product"),
        ("500001", "20001", 0, 1.0, "non_positive"),
        ("500001", "20001", -1, 1.0, "non_positive"),
        ("500001", "20001", 1, 0.0, "non_positive"),
        ("500001", "20001", 1, -0.01, "non_positive"),
        ("500001", "POST", 0, 0.0, "non_product"),
        ("C500001", "20001", -1, 1.0, "cancellation"),
        ("C500001", "20001", 1, 1.0, "cancellation"),
        ("C500001", "POST", -1, 1.0, "cancellation"),
        ("C500001", "20001", -1, 0.0, "cancellation"),
        ("A500001", "20001", 1, 1.0, "adjustment"),
        ("A500001", "B", 1, 1.0, "adjustment"),
        ("a500001", "20001", 1, 1.0, "product"),
        ("c500001", "20001", -1, 1.0, "non_positive"),
    ],
)
def test_bucket_first_match_wins(
    invoice: str, code: str, qty: int, price: float, bucket: str
) -> None:
    df = clean(raw([row(invoice, at(20), qty, price, code)]))
    assert df["bucket"].tolist() == [bucket]


def test_duplicate_beats_every_other_bucket_and_keeps_first_occurrence() -> None:
    lines = [
        row("C1", at(20), -1, 5.0),
        row("C1", at(20), -1, 5.0),
        row("2", at(20), 1, 0.0),
        row("2", at(20), 1, 0.0),
        row("3", at(20), 1, 1.0, code="POST"),
        row("3", at(20), 1, 1.0, code="POST"),
    ]
    assert clean(raw(lines))["bucket"].tolist() == [
        "cancellation",
        "duplicate",
        "non_positive",
        "duplicate",
        "non_product",
        "duplicate",
    ]


def test_duplicate_needs_all_eight_columns_equal() -> None:
    base = row("1", at(20))
    variants = [
        row("2", at(20)),
        row("1", at(20), code="20002"),
        row("1", at(20), desc="OTHER"),
        row("1", at(20), qty=2),
        row("1", at(21)),
        row("1", at(20), price=11.0),
        row("1", at(20), customer=2.0),
        row("1", at(20), country="France"),
    ]
    buckets = clean(raw([base, *variants]))["bucket"].tolist()
    assert buckets == ["product"] * 9


def test_duplicate_with_missing_customer_and_description_collapses() -> None:
    line = row("1", at(20), customer=None, desc=None)
    assert clean(raw([line, line]))["bucket"].tolist() == ["product", "duplicate"]


def test_strip_description_and_country_but_not_inner_spaces() -> None:
    df = clean(raw([row("1", at(20), desc="  MUG  RED \t", country=" France\n")]))
    assert df["Description"].tolist() == ["MUG  RED"]
    assert df["Country"].tolist() == ["France"]


def test_strip_happens_before_duplicate_check() -> None:
    a = row("1", at(20), desc="MUG")
    b = row("1", at(20), desc=" MUG ")
    assert clean(raw([a, b]))["bucket"].tolist() == ["product", "duplicate"]


def test_clean_does_not_mutate_input_and_handles_int_invoice() -> None:
    df = raw([row("1", at(20))])
    df["Invoice"] = 500001
    before = df.copy()
    out = clean(df)
    pd.testing.assert_frame_equal(df, before)
    assert out["Invoice"].tolist() == ["500001"]
    assert "bucket" not in df.columns


# ---------------------------------------------------------- read(): 2 sheets


def test_read_concatenates_sheets_and_overlap_becomes_duplicates(
    tmp_path: Path,
) -> None:
    sheet1 = raw([row("1", at(20)), row("2", at(21))])
    sheet2 = raw([row("2", at(21)), row("3", at(22))])
    sheet2 = sheet2[list(reversed(COLUMNS))]
    sheet1["Invoice"] = sheet1["Invoice"].astype(str)
    path = tmp_path / "x.xlsx"
    with pd.ExcelWriter(path) as writer:
        sheet1.to_excel(writer, sheet_name="Year 2009-2010", index=False)
        sheet2.to_excel(writer, sheet_name="Year 2010-2011", index=False)
    df = read(path)
    assert list(df.columns) == COLUMNS
    assert len(df) == 4
    assert clean(df)["bucket"].tolist() == [
        "product",
        "product",
        "duplicate",
        "product",
    ]
    out = tmp_path / "d"
    build(df, out)
    w = pd.read_parquet(out / "weekly.parquet")
    row_w = w[(w["filter"] == ALL) & (w["week_start"] == pd.Timestamp(W))].iloc[0]
    assert (row_w["orders"], row_w["revenue"], row_w["duplicate_lines"]) == (3, 30.0, 1)


# ------------------------------------------------------- build on odd inputs


def test_every_filter_has_57_weeks_and_week_bounds(tmp_path: Path) -> None:
    out = built(tmp_path, [row("1", at(20)), row("2", at(21), country="France")])
    w = pd.read_parquet(out / "weekly.parquet")
    sizes = w.groupby("filter").size()
    assert set(sizes) == {57}
    assert w["week_start"].min() == pd.Timestamp("2010-11-08")
    assert w["week_start"].max() == pd.Timestamp(LAST_WEEK)
    assert set(sizes.index) == set(
        json.loads((out / "meta.json").read_text())["countries"]
    )


def test_lines_only_in_one_week_leave_other_weeks_empty(tmp_path: Path) -> None:
    out = built(tmp_path, [row("1", at(20), qty=2, price=5.0)])
    s = scen(out, start=FIRST_WEEK, end=LAST_WEEK)
    assert len(s.weeks) == 53
    live = [w for w in s.weeks if w.product_lines]
    assert [w.week_start for w in live] == [W]
    empty = next(w for w in s.weeks if w.week_start == date(2011, 9, 12))
    assert (empty.revenue, empty.orders, empty.aov, empty.cancellation_rate) == (
        0.0,
        0,
        None,
        None,
    )
    assert empty.revenue_wow is None
    assert [f.rule for f in empty.flags] == ["no_data"]
    nxt = next(w for w in s.weeks if w.week_start == date(2011, 9, 26))
    assert nxt.revenue_wow == pytest.approx(-100.0)
    assert [f.rule for f in nxt.flags] == ["no_data"]
    assert s.totals.weeks == 53
    assert s.totals.flagged_weeks == 53
    assert s.totals.revenue == pytest.approx(10.0)


def test_week_boundaries_sunday_night_and_monday_midnight(tmp_path: Path) -> None:
    rows = [
        row("1", datetime(2010, 11, 7, 23, 59), price=1.0),
        row("2", datetime(2010, 11, 8, 0, 0), price=2.0, desc="B"),
        row("3", datetime(2011, 12, 11, 23, 59), price=4.0, desc="C"),
        row("4", datetime(2011, 12, 12, 0, 0), price=8.0, desc="D"),
        row("5", datetime(2011, 9, 25, 23, 59), price=16.0, desc="E"),
        row("6", datetime(2011, 9, 26, 0, 0), price=32.0, desc="F"),
    ]
    out = built(tmp_path, rows)
    w = pd.read_parquet(out / "weekly.parquet")
    a = w[w["filter"] == ALL].set_index("week_start")["revenue"]
    assert a[pd.Timestamp("2010-11-08")] == 2.0
    assert a[pd.Timestamp("2011-12-05")] == 4.0
    assert a[pd.Timestamp("2011-09-19")] == 16.0
    assert a[pd.Timestamp("2011-09-26")] == 32.0
    assert a.sum() == 2.0 + 4.0 + 16.0 + 32.0
    meta = json.loads((out / "meta.json").read_text())
    assert meta["data_end"] == "2011-12-12T00:00:00"
    s = scen(out, week=LAST_WEEK)
    assert "partial_week" not in rules(s)


def test_first_week_change_uses_hidden_base_week(tmp_path: Path) -> None:
    rows = [
        row("1", datetime(2010, 12, 1, 9), price=100.0),
        row("2", datetime(2010, 12, 7, 9), price=150.0),
    ]
    s = scen(built(tmp_path, rows), week=FIRST_WEEK)
    assert s.selected.revenue == 150.0
    assert s.selected.revenue_wow == pytest.approx(50.0)


def test_customer_first_seen_before_window_is_returning(tmp_path: Path) -> None:
    rows = [
        row("1", datetime(2010, 3, 1, 9), customer=5.0),
        row("2", at(20), customer=5.0),
        row("3", at(20), customer=6.0, desc="B"),
    ]
    s = scen(built(tmp_path, rows))
    assert (
        s.selected.customers,
        s.selected.new_customers,
        s.selected.returning_customers,
    ) == (2, 1, 1)


def test_customer_after_window_does_not_make_earlier_new(tmp_path: Path) -> None:
    rows = [
        row("1", at(20), customer=5.0),
        row("2", datetime(2012, 3, 1, 9), customer=5.0),
    ]
    s = scen(built(tmp_path, rows))
    assert s.selected.new_customers == 1


def test_cancellation_only_history_does_not_make_customer_returning(
    tmp_path: Path,
) -> None:
    rows = [
        row("C1", at(13), qty=-1, customer=5.0),
        row("2", at(20), customer=5.0),
    ]
    s = scen(built(tmp_path, rows))
    assert (s.selected.customers, s.selected.new_customers) == (1, 1)


def test_customer_with_only_cancellation_is_not_counted(tmp_path: Path) -> None:
    rows = [row("1", at(20), customer=1.0), row("C2", at(21), qty=-1, customer=9.0)]
    s = scen(built(tmp_path, rows))
    assert s.selected.customers == 1
    assert s.selected.cancellation_invoices == 1


def test_all_customer_ids_missing(tmp_path: Path) -> None:
    rows = [
        row("1", at(20), customer=None),
        row("2", at(21), customer=None, desc="B"),
        row("C3", at(22), qty=-1, customer=None),
    ]
    out = built(tmp_path, rows)
    s = scen(out)
    w = s.selected
    assert (w.customers, w.new_customers, w.returning_customers) == (0, 0, 0)
    assert (w.product_lines, w.lines_without_customer_id, w.orders) == (2, 2, 2)
    assert w.revenue == 20.0
    assert "0 have none" not in s.sources["customers"]
    assert "(2 have none)" in s.sources["customers"]
    assert weekly_csv(s).decode().splitlines()[1].split(",")[5:8] == ["0", "0", "0"]


def test_customer_ids_are_nowhere_in_output_files(tmp_path: Path) -> None:
    out = built(tmp_path, [row("1", at(20), customer=18287.0, desc="Z")])
    for f in out.iterdir():
        assert "18287" not in f.read_bytes().decode("latin-1")
    for name in ("weekly.parquet", "products.parquet"):
        cols = [c.lower() for c in pd.read_parquet(out / name).columns]
        assert not {"customer id", "customer_id", "customerid"} & set(cols)


def test_country_and_description_whitespace_and_empty(tmp_path: Path) -> None:
    rows = [
        row("1", at(20), country="France", desc=" MUG "),
        row("2", at(21), country=" France ", desc="MUG"),
        row("3", at(22), country="   ", desc="  "),
        row("4", at(23), country="", desc=None, code="20002"),
    ]
    out = built(tmp_path, rows)
    assert core.countries(out) == [ALL, UK, OUTSIDE_UK, "France"]
    all_ = scen(out)
    assert (all_.selected.revenue, all_.selected.product_lines) == (40.0, 4)
    fr = scen(out, country="France")
    assert (fr.selected.revenue, fr.selected.orders) == (20.0, 2)
    assert scen(out, country=OUTSIDE_UK).selected.revenue == 40.0
    assert next(r.label for r in all_.top_products) == "MUG"
    assert [r.label for r in all_.top_countries] == ["France"]


def test_country_order_is_plain_sorted_after_three_fixed(tmp_path: Path) -> None:
    names = [
        "Zimbabwe",
        "EIRE",
        "Côte d'Ivoire",
        "european community",
        "Austria",
        "RSA",
    ]
    rows = [row(str(i), at(20), country=n, desc=f"D{i}") for i, n in enumerate(names)]
    out = built(tmp_path, rows)
    assert core.countries(out)[:3] == [ALL, UK, OUTSIDE_UK]
    assert core.countries(out)[3:] == sorted(names, key=str.casefold)


def test_uk_and_outside_uk_listed_even_without_such_lines(tmp_path: Path) -> None:
    out = built(tmp_path, [row("1", at(20), country="France")])
    assert core.countries(out) == [ALL, UK, OUTSIDE_UK, "France"]
    uk = scen(out, country=UK)
    assert (uk.selected.revenue, uk.selected.product_lines, rules(uk)) == (
        0.0,
        0,
        ["no_data", "partial_week"],
    )
    assert uk.top_countries == [] and uk.top_products == []
    assert scen(out, country=OUTSIDE_UK).selected.revenue == 10.0


def test_outside_uk_excludes_uk_and_all_is_sum(tmp_path: Path) -> None:
    rows = [
        row("1", at(20), price=10.0, customer=1.0),
        row("2", at(20), price=20.0, country="France", customer=2.0, desc="B"),
        row("3", at(20), price=40.0, country="EIRE", customer=3.0, desc="C"),
    ]
    out = built(tmp_path, rows)
    uk, out_uk, all_ = (scen(out, country=c).selected for c in (UK, OUTSIDE_UK, ALL))
    assert (uk.revenue, out_uk.revenue, all_.revenue) == (10.0, 60.0, 70.0)
    assert uk.orders + out_uk.orders == all_.orders == 3
    assert [r.label for r in scen(out, OUTSIDE_UK).top_countries] == ["EIRE", "France"]


def test_customer_buying_in_two_countries_same_week(tmp_path: Path) -> None:
    rows = [
        row("1", at(20), country=UK, customer=7.0, price=10.0),
        row("2", at(21), country="France", customer=7.0, price=20.0, desc="B"),
    ]
    out = built(tmp_path, rows)
    got = {c: scen(out, country=c).selected for c in (ALL, UK, OUTSIDE_UK, "France")}
    assert {c: (w.customers, w.new_customers) for c, w in got.items()} == {
        ALL: (1, 1),
        UK: (1, 1),
        OUTSIDE_UK: (1, 1),
        "France": (1, 1),
    }
    assert got[ALL].revenue == 30.0


def test_customer_two_countries_two_weeks_new_only_in_first(tmp_path: Path) -> None:
    rows = [
        row("1", at(13), country="France", customer=7.0),
        row("2", at(20), country=UK, customer=7.0),
        row("3", at(20), country="France", customer=7.0),
    ]
    out = built(tmp_path, rows)
    for c in (ALL, UK, "France", OUTSIDE_UK):
        w = scen(out, country=c).selected
        assert (w.customers, w.new_customers, w.returning_customers) == (1, 0, 1)


def test_same_invoice_over_week_boundary_counts_in_both_weeks(tmp_path: Path) -> None:
    rows = [
        row("1", datetime(2011, 9, 25, 23, 0), desc="A"),
        row("1", datetime(2011, 9, 26, 1, 0), desc="B"),
    ]
    out = built(tmp_path, rows)
    assert scen(out, week=W).selected.orders == 1
    assert scen(out, week=date(2011, 9, 26)).selected.orders == 1


def test_cancellation_rate_counts_invoices_not_lines_and_includes_non_product(
    tmp_path: Path,
) -> None:
    rows = [
        row("1", at(20)),
        row("C2", at(21), qty=-1, price=4.0, code="20001"),
        row("C2", at(21), qty=-2, price=1.0, code="20002", desc="B"),
        row("C3", at(22), qty=-1, price=15.0, code="POST", desc="POSTAGE"),
    ]
    w = scen(built(tmp_path, rows)).selected
    assert w.cancellation_invoices == 2
    assert w.orders == 1
    assert w.cancellation_rate == pytest.approx(100 * 2 / 3)
    assert w.cancelled_value == pytest.approx(6.0)
    assert w.net_revenue == pytest.approx(4.0)


def test_cancelled_value_source_counts_only_product_code_lines(tmp_path: Path) -> None:
    rows = [
        row("1", at(20)),
        row("C2", at(21), qty=-1, price=4.0, code="20001"),
        row("C3", at(22), qty=-1, price=15.0, code="POST", desc="POSTAGE"),
        row("C4", at(22), qty=-1, price=1.0, code="M", desc="Manual"),
    ]
    text = scen(built(tmp_path, rows)).sources["cancelled_value"]
    match = pd.Series([text]).str.extract(
        r"over (\d+) cancellation lines with a product code"
    )
    assert match[0].tolist() == ["1"], text


def test_positive_quantity_cancellation_line_reduces_cancelled_value(
    tmp_path: Path,
) -> None:
    rows = [row("1", at(20)), row("C2", at(21), qty=1, price=3.0)]
    w = scen(built(tmp_path, rows)).selected
    assert w.cancelled_value == pytest.approx(-3.0)


# --------------------------------------------------------------- top lists


def test_top_products_limited_to_five_and_tie_broken_alphabetically(
    tmp_path: Path,
) -> None:
    rows = [
        row(str(i), at(20), price=10.0, code=f"2000{i}", desc=d)
        for i, d in enumerate("GFEDCBA")
    ]
    s = scen(built(tmp_path, rows))
    assert [r.label for r in s.top_products] == ["A", "B", "C", "D", "E"]


def test_top_products_only_selected_week_and_filter(tmp_path: Path) -> None:
    rows = [
        row("1", at(13), price=999.0, desc="OLD"),
        row("2", at(20), price=5.0, desc="NEW"),
        row("3", at(20), price=50.0, desc="FR", country="France"),
    ]
    out = built(tmp_path, rows)
    assert [r.label for r in scen(out, country=UK).top_products] == ["NEW"]
    assert [r.label for r in scen(out, country="France").top_products] == ["FR"]


def test_product_description_tie_is_alphabetical(tmp_path: Path) -> None:
    rows = [row("1", at(20), desc="Zed"), row("2", at(21), desc="Alpha")]
    assert [r.label for r in scen(built(tmp_path, rows)).top_products] == ["Alpha"]


def test_stock_code_case_variants_are_separate_products(tmp_path: Path) -> None:
    rows = [
        row("1", at(20), code="85123A", desc="LIGHT", price=3.0),
        row("2", at(20), code="85123a", desc="LIGHT LOWER", price=2.0),
    ]
    out = built(tmp_path, rows)
    p = pd.read_parquet(out / "products.parquet")
    assert sorted(p[p["filter"] == ALL]["stock_code"]) == ["85123A", "85123a"]


def test_top_countries_limited_to_five(tmp_path: Path) -> None:
    rows = [
        row(str(i), at(20), price=float(i + 1), country=f"C{i}", desc=f"D{i}")
        for i in range(8)
    ]
    s = scen(built(tmp_path, rows))
    assert [r.label for r in s.top_countries] == ["C7", "C6", "C5", "C4", "C3"]


# --------------------------------------------------------------------- flags


def test_top_line_tie_picks_earliest_line(tmp_path: Path) -> None:
    rows = [
        row("9", at(22), price=50.0, desc="LATE"),
        row("8", at(20), price=50.0, desc="EARLY", code="20002"),
    ]
    flag = next(
        f for f in scen(built(tmp_path, rows)).selected.flags if f.rule == "top_line"
    )
    assert flag.reason == "One line is 50.0% of revenue: Early, £50 (invoice 8)"


def test_top_line_exactly_25_percent_is_not_flagged(tmp_path: Path) -> None:
    rows = [
        row(str(i), at(20), price=25.0, code=f"2000{i}", desc=f"D{i}") for i in range(4)
    ]
    assert "top_line" not in rules(scen(built(tmp_path, rows)))


def test_top_line_exactly_25_percent_with_decimal_prices_is_not_flagged(
    tmp_path: Path,
) -> None:
    rows = [
        row(str(i), at(20), price=1.1, code=f"2000{i}", desc=f"D{i}") for i in range(4)
    ]
    assert "top_line" not in rules(scen(built(tmp_path, rows)))


def test_top_line_just_over_25_percent_is_flagged(tmp_path: Path) -> None:
    rows = [
        row("1", at(20), price=10.01, desc="Small"),
        row("2", at(20), price=10.0, code="20002", desc="B"),
        row("3", at(20), price=10.0, code="20003", desc="C"),
        row("4", at(20), price=10.0, code="20004", desc="D"),
    ]
    flags = {f.rule: f.reason for f in scen(built(tmp_path, rows)).selected.flags}
    assert flags["top_line"] == "One line is 25.0% of revenue: Small, £10 (invoice 1)"


def test_top_line_single_line_week_and_unicode_description(tmp_path: Path) -> None:
    rows = [row("123456", at(20), qty=2, price=1234.5, desc="CAFÉ MUG ☕, BLUE")]
    flags = {f.rule: f.reason for f in scen(built(tmp_path, rows)).selected.flags}
    assert (
        flags["top_line"]
        == f"One line is 100.0% of revenue: Café Mug ☕, Blue, £2{N}469 (invoice 123456)"
    )


@pytest.mark.parametrize(
    ("cancelled", "flagged", "share"),
    [
        (24.99, False, ""),
        (25.0, True, "25.0%"),
        (25.01, True, "25.0%"),
        (100.0, True, "100.0%"),
        (400.0, True, "400.0%"),
    ],
)
def test_large_cancellations_boundary(
    tmp_path: Path, cancelled: float, flagged: bool, share: str
) -> None:
    rows = [
        row("1", at(20), price=100.0),
        row("C2", at(21), qty=-1, price=cancelled, code="20002"),
    ]
    s = scen(built(tmp_path, rows))
    got = {f.rule: f.reason for f in s.selected.flags}
    assert ("large_cancellations" in got) is flagged
    if flagged:
        assert (
            got["large_cancellations"]
            == f"£{round(cancelled)} cancelled against £100 revenue ({share})"
        )


def test_large_cancellations_exact_25_percent_survives_float_noise(
    tmp_path: Path,
) -> None:
    """3 x 1.10 = 3.3000000000000003 in floats; 0.825 cancelled is exactly 25 % of 3.30."""
    rows = [
        row("1", at(20), qty=3, price=1.1),
        row("C2", at(21), qty=-1, price=0.825, code="20002"),
    ]
    assert "large_cancellations" in rules(scen(built(tmp_path, rows)))


def test_large_cancellations_reason_groups_thousands(tmp_path: Path) -> None:
    rows = [
        row("1", at(20), price=20000.0),
        row("C2", at(21), qty=-1, price=12345.0, code="20002"),
    ]
    flags = {f.rule: f.reason for f in scen(built(tmp_path, rows)).selected.flags}
    assert (
        flags["large_cancellations"]
        == f"£12{N}345 cancelled against £20{N}000 revenue (61.7%)"
    )


def test_no_large_cancellations_flag_when_revenue_is_zero(tmp_path: Path) -> None:
    rows = [row("1", at(13)), row("C1", at(21), qty=-1, price=50.0)]
    s = scen(built(tmp_path, rows))
    assert rules(s) == ["no_data", "partial_week"]
    assert s.selected.net_revenue == -50.0
    assert s.selected.cancellation_rate == 100.0


@pytest.mark.parametrize(
    ("now_price", "flagged", "text"),
    [
        (140.0, True, "Revenue +40.0% vs 4-week average (£140 vs £100)"),
        (139.9, False, ""),
        (60.0, True, "Revenue -40.0% vs 4-week average (£60 vs £100)"),
        (60.04, True, "Revenue -40.0% vs 4-week average (£60 vs £100)"),
        (60.06, False, ""),
        (1000.0, True, "Revenue +900.0% vs 4-week average (£1" + N + "000 vs £100)"),
    ],
)
def test_revenue_swing_boundaries(
    tmp_path: Path, now_price: float, flagged: bool, text: str
) -> None:
    rows = [row("1", at(13), price=100.0), row("2", at(20), price=now_price)]
    got = {f.rule: f.reason for f in scen(built(tmp_path, rows)).selected.flags}
    assert ("revenue_swing" in got) is flagged
    if flagged:
        assert got["revenue_swing"] == text


def test_orders_swing_boundary_and_reason(tmp_path: Path) -> None:
    prev = [
        row(str(i), at(13), price=1.0, code=f"2000{i}", desc=f"D{i}") for i in range(5)
    ]
    now = [
        row(str(10 + i), at(20), price=1.0, code=f"2000{i}", desc=f"D{i}")
        for i in range(7)
    ]
    got = {f.rule: f.reason for f in scen(built(tmp_path, prev + now)).selected.flags}
    assert got["orders_swing"] == "Orders +40.0% vs 4-week average (7 vs 5.0)"
    got = {
        f.rule: f.reason
        for f in scen(built(tmp_path / "b", prev + now[:6])).selected.flags
    }
    assert "orders_swing" not in got


def test_swing_not_flagged_when_previous_week_is_empty(tmp_path: Path) -> None:
    rows = [row("1", at(6), price=100.0), row("2", at(20), price=1000.0)]
    s = scen(built(tmp_path, rows))
    assert s.selected.revenue_vs4w == pytest.approx(900.0)
    assert not {"revenue_swing", "orders_swing"} & set(rules(s))


def test_flag_rule_order_with_every_rule(tmp_path: Path) -> None:
    rows = [
        row("1", at(13), price=100.0),
        row("2", at(20), price=150.0),
        row("3", at(20), price=150.0, code="20002", desc="B"),
        row("C4", at(21), qty=-1, price=100.0, code="20003"),
        row("5", at(21, 11), price=0.01, code="20004", desc="C"),
    ]
    s = scen(built(tmp_path, rows))
    assert rules(s) == [
        "partial_week",
        "revenue_swing",
        "orders_swing",
        "large_cancellations",
        "top_line",
    ]
    assert all(f.week_start == W for f in s.selected.flags)


@pytest.mark.parametrize(
    ("last", "partial"),
    [
        (datetime(2011, 9, 25, 23, 59, 59), False),
        (datetime(2011, 9, 25, 0, 0), False),
        (datetime(2011, 9, 24, 23, 59, 59), True),
        (datetime(2011, 9, 19, 0, 0), True),
        (datetime(2011, 9, 20, 12, 0), True),
    ],
)
def test_partial_week_boundaries(tmp_path: Path, last: datetime, partial: bool) -> None:
    rows = [row("1", datetime(2011, 9, 12, 9)), row("2", last)]
    s = scen(built(tmp_path, rows), week=W)
    got = {f.rule: f.reason for f in s.selected.flags}
    assert ("partial_week" in got) is partial
    if partial:
        assert (
            got["partial_week"] == f"Data ends {last.date()}; the week is missing days"
        )
    assert "partial_week" not in rules(scen(tmp_path / "d", week=PREV))


def test_partial_week_applies_to_empty_week_and_every_filter(tmp_path: Path) -> None:
    rows = [row("1", at(13)), row("2", at(21), country="France")]
    out = built(tmp_path, rows)
    for c in (ALL, UK, OUTSIDE_UK, "France"):
        assert "partial_week" in rules(scen(out, country=c))
    assert rules(scen(out, country=UK)) == [
        "no_data",
        "partial_week",
    ]


def test_last_shown_week_not_partial_when_data_ends_on_final_sunday(
    tmp_path: Path,
) -> None:
    rows = [row("1", datetime(2011, 12, 11, 20, 0))]
    assert "partial_week" not in rules(scen(built(tmp_path, rows), week=LAST_WEEK))


def test_flags_in_scenario_are_concatenation_of_week_flags(tmp_path: Path) -> None:
    rows = [row("1", at(13)), row("2", at(20), price=100.0)]
    s = scen(built(tmp_path, rows), start=PREV, end=W)
    assert s.flags == [f for w in s.weeks for f in w.flags]
    assert s.totals.flagged_weeks == sum(1 for w in s.weeks if w.flags)


# ----------------------------------------------------------------------- CSV


def parse(csv_bytes: bytes) -> list[list[str]]:
    return list(csv.reader(io.StringIO(csv_bytes.decode("utf-8"))))


def test_csv_shape_for_range_with_empty_and_zero_base_weeks(tmp_path: Path) -> None:
    rows = [row("1", at(20), price=12.345, desc="CAFÉ ☕")]
    s = scen(built(tmp_path, rows), start=date(2011, 9, 12), end=date(2011, 9, 26))
    data = weekly_csv(s)
    assert not data.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in data and data.endswith(b"\n")
    table = parse(data)
    assert len(table) == 4
    assert {len(r) for r in table} == {17}
    assert [r[0] for r in table[1:]] == ["2011-09-12", "2011-09-19", "2011-09-26"]
    head = dict(zip(table[0], table[2], strict=True))
    assert head["revenue_gbp"] == "12.35" or head["revenue_gbp"] == "12.34"
    assert (
        head["aov_gbp"] != ""
        and head["revenue_wow_pct"] == ""
        and head["orders_wow_pct"] == ""
    )
    empty = dict(zip(table[0], table[1], strict=True))
    assert empty["aov_gbp"] == "" and empty["cancellation_rate_pct"] == ""
    assert empty["flags"] == "no_data"
    assert empty["orders"] == "0" and empty["revenue_gbp"] == "0.00"
    last = dict(zip(table[0], table[3], strict=True))
    assert last["revenue_wow_pct"] == "-100.00"
    assert last["flags"] == "no_data"


def test_csv_single_week_range(tmp_path: Path) -> None:
    table = parse(weekly_csv(scen(built(tmp_path, [row("1", at(20))]))))
    assert len(table) == 2
    assert table[1][-1] == "partial_week; top_line"


def test_csv_money_is_rounded_half_up_like_the_screen(tmp_path: Path) -> None:
    """538.325 shows as £538.33 on screen; the CSV must not say 538.32 for the same number."""
    s = scen(built(tmp_path, [row("1", at(20), qty=1, price=538.325)]))
    cell = parse(weekly_csv(s))[1][1]
    assert money2(s.selected.revenue) == "£538.33"
    assert cell == "538.33"


def test_csv_has_no_negative_zero_cell(tmp_path: Path) -> None:
    rows = [
        row("1", at(20), price=0.3),
        row("C2", at(21), qty=-1, price=0.1, code="20002"),
        row("C3", at(21), qty=-1, price=0.2, code="20003"),
    ]
    s = scen(built(tmp_path, rows))
    assert abs(s.selected.net_revenue) < 1e-9
    assert "-0.00" not in weekly_csv(s).decode()


def test_csv_wide_values_and_negative_net(tmp_path: Path) -> None:
    rows = [
        row("1", at(20), qty=1000, price=1234.56),
        row("C2", at(21), qty=-1, price=1_500_000.0, code="20002"),
    ]
    cells = parse(weekly_csv(scen(built(tmp_path, rows))))[1]
    assert cells[1] == "1234560.00"
    assert cells[10] == "1500000.00"
    assert cells[11] == "-265440.00"
    assert N not in "".join(cells)


# ---------------------------------------------------------------- invariants


def test_totals_over_range_match_sum_of_weeks(tmp_path: Path) -> None:
    rows = [
        row("1", at(13), price=100.0),
        row("2", at(20), price=50.0),
        row("C3", at(21), qty=-1, price=10.0, code="20002"),
        row("4", at(27, month=9), price=7.0, code="20003"),
    ]
    s = scen(built(tmp_path, rows), start=PREV, end=date(2011, 9, 26))
    assert s.totals.weeks == 3
    assert s.totals.revenue == pytest.approx(157.0)
    assert s.totals.cancelled_value == pytest.approx(10.0)
    assert s.totals.net_revenue == pytest.approx(147.0)
    assert (s.totals.orders, s.totals.units) == (3, 3)


def test_scenario_is_deterministic_and_row_order_independent(tmp_path: Path) -> None:
    rows = [
        row(
            str(i),
            at(13 + i),
            price=float(i + 1),
            code=f"2000{i}",
            desc=f"D{i}",
            customer=float(i % 3),
            country=("France" if i % 2 else UK),
        )
        for i in range(10)
    ]
    shuffled = rows[::-1]
    a = built(tmp_path, rows, "a")
    b = built(tmp_path, shuffled, "b")
    for c in (ALL, UK, OUTSIDE_UK, "France"):
        sa = scen(a, country=c, start=PREV, end=W)
        assert sa == scen(a, country=c, start=PREV, end=W)
        assert sa.model_dump(exclude={"filters"}) == scen(
            b, country=c, start=PREV, end=W
        ).model_dump(exclude={"filters"})


def test_raw_frame_is_not_mutated_by_build(tmp_path: Path) -> None:
    df = raw([row("1", at(20)), row("1", at(20))])
    before = df.copy()
    build(df, tmp_path / "d")
    pd.testing.assert_frame_equal(df, before)


def test_build_twice_is_byte_stable(tmp_path: Path) -> None:
    rows = [row("1", at(20)), row("2", at(21), country="France", desc="B")]
    a, b = built(tmp_path, rows, "a"), built(tmp_path, rows, "b")
    for name in ("weekly.parquet", "products.parquet"):
        pd.testing.assert_frame_equal(
            pd.read_parquet(a / name), pd.read_parquet(b / name)
        )
    assert (a / "meta.json").read_text() == (b / "meta.json").read_text()


def test_rebuilding_into_the_same_dir_is_seen_by_run_scenario(tmp_path: Path) -> None:
    out = tmp_path / "d"
    build(raw([row("1", at(20), price=10.0)]), out)
    assert scen(out).selected.revenue == 10.0
    build(raw([row("1", at(20), price=99.0)]), out)
    assert scen(out).selected.revenue == 99.0


def test_concurrent_run_scenario_matches_sequential(tmp_path: Path) -> None:
    rows = [
        row(
            str(i),
            at(13 + i % 7),
            price=float(i + 1),
            country=c,
            customer=float(i),
            desc=f"D{i}",
            code=f"2000{i}",
        )
        for i, c in enumerate([UK, "France", "EIRE", "Spain"] * 3)
    ]
    out = built(tmp_path, rows)
    names = core.countries(out)
    seq = {c: scen(out, country=c, start=PREV, end=W) for c in names}
    with ThreadPoolExecutor(8) as pool:
        futures = {
            c: [pool.submit(scen, out, c, W, PREV, W) for _ in range(5)] for c in names
        }
    for c, fs in futures.items():
        for f in fs:
            assert f.result() == seq[c]


def test_countries_returns_a_copy(tmp_path: Path) -> None:
    out = built(tmp_path, [row("1", at(20))])
    got = core.countries(out)
    got.append("Mars")
    assert "Mars" not in core.countries(out)


def test_scenario_mutation_does_not_leak_into_next_call(tmp_path: Path) -> None:
    out = built(tmp_path, [row("1", at(20))])
    s = scen(out)
    s.weeks.clear()
    s.sources["revenue"] = "x"
    again = scen(out)
    assert len(again.weeks) == 1
    assert again.sources["revenue"].startswith("sum(Quantity")


def test_unknown_country_variants(tmp_path: Path) -> None:
    out = built(tmp_path, [row("1", at(20), country="France")])
    for bad in ("france", "France ", "", "all countries", "Atlantis"):
        with pytest.raises(ValueError, match=r"^Unknown country: .*\.$"):
            scen(out, country=bad)
    with pytest.raises(ValueError, match="Unknown country: Atlantis."):
        scen(out, country="Atlantis")


def test_very_long_description_and_unicode_country(tmp_path: Path) -> None:
    long = "X" * 10_000
    rows = [row("1", at(20), desc=long, country="Côte d'Ivoire")]
    out = built(tmp_path, rows)
    s = scen(out, country="Côte d'Ivoire")
    assert s.top_products[0].label == long
    flag = next(f for f in s.selected.flags if f.rule == "top_line")
    assert "X" + "x" * 9_999 in flag.reason


def test_sources_have_ten_nonempty_entries_for_zero_week(tmp_path: Path) -> None:
    s = scen(built(tmp_path, [row("1", at(20))]), week=PREV)
    keys = [
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
    ]
    assert all(s.sources[k] for k in keys)
    assert (
        s.sources["revenue"]
        == "sum(Quantity × Price) over 0 product lines, 2011-09-12..2011-09-18"
    )


def test_download_error_paths_write_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = tmp_path / "raw"

    def boom(url: str, timeout: int) -> io.BytesIO:
        raise TimeoutError("timed out")

    monkeypatch.setattr(download.urllib.request, "urlopen", boom)
    with pytest.raises(TimeoutError):
        download.download(dest)
    assert not dest.exists()
    monkeypatch.setattr(
        download.urllib.request, "urlopen", lambda url, timeout: io.BytesIO(b"")
    )
    with pytest.raises(download.ChecksumError):
        download.download(dest)
    assert not dest.exists()


def test_download_uses_120_second_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[tuple[str, int]] = []

    def fake(url: str, timeout: int) -> io.BytesIO:
        seen.append((url, timeout))
        return io.BytesIO(b"nope")

    monkeypatch.setattr(download.urllib.request, "urlopen", fake)
    with pytest.raises(download.ChecksumError):
        download.download(tmp_path / "raw")
    assert seen == [
        ("https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip", 120)
    ]


def test_build_with_only_non_product_lines_does_not_crash(tmp_path: Path) -> None:
    out = built(tmp_path, [row("C1", at(21), qty=-1, price=50.0, customer=None)])
    assert scen(out).selected.revenue == 0.0
