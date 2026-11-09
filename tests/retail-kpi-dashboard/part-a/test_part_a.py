import hashlib
import io
import json
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from kpi import core
from kpi import download as dl
from kpi.build import build, main
from kpi.core import run_scenario, weekly_csv
from kpi.data import COLUMNS
from kpi.fmt import change, money, money2, pct, points
from kpi.models import Filters, Scenario
from kpi.summaries import build_summaries, extract

UK = "United Kingdom"
W = date(2011, 9, 19)


def raw(rows: list[tuple[Any, ...]]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=COLUMNS)
    df["Invoice"] = df["Invoice"].astype(str)
    df["StockCode"] = df["StockCode"].astype(str)
    return df


def line(
    invoice: str,
    qty: int,
    price: float,
    day: int = 20,
    customer: float = 1.0,
    country: str = UK,
    code: str = "20001",
    desc: str = "MUG",
) -> tuple[Any, ...]:
    return (
        invoice,
        code,
        desc,
        qty,
        datetime(2011, 9, day, 10),
        price,
        customer,
        country,
    )


def scenario(
    tmp_path: Path,
    rows: list[tuple[Any, ...]],
    country: str = "All countries",
    week: date = W,
) -> Scenario:
    out = tmp_path / "d"
    build(raw(rows), out)
    return run_scenario(Filters(start=week, end=week, country=country, week=week), out)


def test_money_formats_negatives_and_none() -> None:
    assert money(-1234.4) == "-£1 234"
    assert money2(None) == "n/a"
    assert money2(-0.004) == "£0.00"
    assert change(-0.04) == "+0.0%"
    assert change(12345.6) == "+12 345.6%"
    assert points(None) == "n/a"
    assert pct(None) == "n/a"


def test_filters_snap_to_monday_and_accept_last_sunday() -> None:
    f = Filters(start=date(2010, 12, 8), end=date(2011, 12, 11), week=date(2011, 9, 21))
    assert (f.start, f.end, f.week) == (
        date(2010, 12, 6),
        date(2011, 12, 5),
        date(2011, 9, 19),
    )


def test_net_revenue_can_go_negative_and_csv_blanks_none(tmp_path: Path) -> None:
    s = scenario(tmp_path, [line("1", 1, 10.0), line("C2", -5, 10.0)])
    assert s.selected.net_revenue == pytest.approx(-40.0)
    assert {f.rule for f in s.selected.flags} >= {"large_cancellations"}
    row = weekly_csv(s).decode().splitlines()[1].split(",")
    assert row[0] == "2011-09-19"
    assert row[14] == ""


def test_cancellation_only_week_has_no_orders_and_rate_100(tmp_path: Path) -> None:
    s = scenario(tmp_path, [line("1", 1, 10.0, day=13), line("C2", -1, 10.0, day=20)])
    w = s.selected
    assert (w.orders, w.aov, w.cancellation_rate) == (0, None, 100.0)
    assert [f.rule for f in w.flags] == [
        "no_data",
        "partial_week",
        "revenue_swing",
        "orders_swing",
    ]


def test_top_countries_follow_the_filter(tmp_path: Path) -> None:
    rows = [
        line("1", 1, 10.0),
        line("2", 1, 30.0, country="France", customer=2.0),
        line("3", 1, 20.0, country="EIRE", customer=3.0),
    ]
    assert [r.label for r in scenario(tmp_path / "a", rows).top_countries] == [
        "France",
        "EIRE",
        UK,
    ]
    assert [
        r.label for r in scenario(tmp_path / "b", rows, "Outside UK").top_countries
    ] == ["France", "EIRE"]
    assert [r.label for r in scenario(tmp_path / "c", rows, "EIRE").top_countries] == [
        "EIRE"
    ]


def test_countries_order(tmp_path: Path) -> None:
    out = tmp_path / "d"
    build(
        raw(
            [
                line("1", 1, 1.0, country="Spain"),
                line("2", 1, 1.0),
                line("3", 1, 1.0, country="Austria"),
            ]
        ),
        out,
    )
    assert core.countries(out) == [
        "All countries",
        UK,
        "Outside UK",
        "Austria",
        "Spain",
    ]


def test_product_label_is_most_frequent_description(tmp_path: Path) -> None:
    rows = [
        line("1", 1, 1.0, desc="B NAME"),
        line("2", 1, 1.0, desc="A NAME"),
        line("3", 1, 1.0, desc="B NAME"),
    ]
    assert [r.label for r in scenario(tmp_path, rows).top_products] == ["B NAME"]


def test_new_customer_uses_first_purchase_in_any_country(tmp_path: Path) -> None:
    rows = [line("1", 1, 1.0, day=13, country="France"), line("2", 1, 1.0, day=20)]
    assert scenario(tmp_path, rows, UK).selected.new_customers == 0


def test_build_keeps_no_customer_ids(tmp_path: Path) -> None:
    out = tmp_path / "d"
    build(raw([line("1", 1, 1.0, customer=77777.0)]), out)
    for name in ("weekly.parquet", "products.parquet"):
        assert "77777" not in pd.read_parquet(out / name).to_csv()


def test_unknown_country_message(tmp_path: Path) -> None:
    out = tmp_path / "d"
    build(raw([line("1", 1, 1.0)]), out)
    with pytest.raises(ValueError, match=r"Unknown country: Mars\."):
        run_scenario(Filters(start=W, end=W, country="Mars", week=W), out)


REPORT = """# Weekly sales · 2011-12-05 to 2011-12-11

> **Needs review**
>
> - Data stops on Friday.

## Partial week, £172,782 cancelled

- Revenue: £483,725 (+56.4% vs last week)

Product revenue was £483,725 [F3], and 1,234,567 units [F6] moved.

Second paragraph [F10].

## Worth a look

- Revenue +56.4% vs last week
"""


def test_extract_cleans_markers_and_commas() -> None:
    s = extract(REPORT)
    assert s is not None
    assert s.headline == "Partial week, £172 782 cancelled"
    assert (
        s.text
        == "Product revenue was £483 725, and 1 234 567 units moved.\n\nSecond paragraph."
    )


def test_extract_without_heading_is_none() -> None:
    assert extract("# Title\n\nNo sales data for week.\n") is None


def test_build_summaries_counts_weeks(tmp_path: Path) -> None:
    (tmp_path / "src" / "2011-12-05").mkdir(parents=True)
    (tmp_path / "src" / "2011-12-05" / "report.md").write_text(REPORT)
    (tmp_path / "src" / "2010-12-27").mkdir()
    (tmp_path / "src" / "2010-12-27" / "report.md").write_text("# Title\n\nNo sales.\n")
    out = tmp_path / "out" / "summaries.json"
    assert build_summaries(tmp_path / "src", out) == 1
    assert list(json.loads(out.read_text())) == ["2011-12-05"]


def test_download_writes_workbook_when_checksum_matches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(dl.FILE_NAME, b"xlsx bytes")
    payload = buf.getvalue()
    monkeypatch.setattr(dl, "SHA256", hashlib.sha256(payload).hexdigest())
    monkeypatch.setattr(
        dl.urllib.request, "urlopen", lambda url, timeout: io.BytesIO(payload)
    )
    assert dl.download(tmp_path / "raw").read_bytes() == b"xlsx bytes"


def test_main_downloads_when_raw_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[Path] = []
    target = tmp_path / "raw" / "x.xlsx"

    def fake_download(dest: Path) -> Path:
        calls.append(dest)
        return target

    monkeypatch.setattr("kpi.build.download", fake_download)
    monkeypatch.setattr("kpi.build.read", lambda path: raw([line("1", 1, 1.0)]))
    main(["--raw", str(target), "--out", str(tmp_path / "out")])
    assert calls == [tmp_path / "raw"]
    assert (tmp_path / "out" / "weekly.parquet").exists()


def test_csv_rounds_half_up_like_the_cards(tmp_path: Path) -> None:
    s = scenario(tmp_path, [line("1", 1, 374.325)])
    assert f"{s.selected.aov:.2f}" == "374.32"
    assert money2(s.selected.aov) == "£374.33"
    assert weekly_csv(s).decode().splitlines()[1].split(",")[3] == "374.33"


def test_cancelled_value_source_counts_only_product_code_cancellations(
    tmp_path: Path,
) -> None:
    rows = [line("1", 4, 10.0), line("C2", -1, 10.0), line("C3", -1, 5.0, code="POST")]
    assert (
        "over 1 cancellation lines with a product code"
        in scenario(tmp_path, rows).sources["cancelled_value"]
    )


def test_exact_quarter_with_float_noise_is_flagged(tmp_path: Path) -> None:
    prices = [1.10, 1.10, 1.10, 1.10, 0.10, 0.30, 0.40]
    rows = [line(str(i), 1, p) for i, p in enumerate(prices, 1)] + [
        line("C9", -1, 1.30)
    ]
    reasons = {f.rule: f.reason for f in scenario(tmp_path, rows).selected.flags}
    assert reasons["large_cancellations"] == "£1 cancelled against £5 revenue (25.0%)"


def test_change_from_negative_base_is_none(tmp_path: Path) -> None:
    rows = [
        line("1", 1, 10.0, day=13),
        line("C2", -5, 10.0, day=13),
        line("3", 1, 10.0),
    ]
    assert scenario(tmp_path, rows).selected.net_revenue_wow is None


def test_countries_sort_ignores_case(tmp_path: Path) -> None:
    out = tmp_path / "d"
    build(
        raw(
            [
                line("1", 1, 1.0, country=c)
                for c in ["USA", "United Arab Emirates", "Unspecified"]
            ]
        ),
        out,
    )
    assert core.countries(out)[3:] == ["United Arab Emirates", "Unspecified", "USA"]


def test_extract_drops_rules_lists_and_splits_on_space_only_lines() -> None:
    s = extract("## H\nPara one.\n- item a\n1. item b\n\n---\n  \nPara two.\n")
    assert s is not None
    assert s.text == "Para one.\n\nPara two."
