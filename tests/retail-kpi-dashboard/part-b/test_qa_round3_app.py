"""Round-3 PART-B QA: YoY captions, Trends measure and y range, driver lines, Weekly table toggles, AI summary placement, one net revenue everywhere, no exceptions."""

import gc
import json
import re
from collections.abc import Iterator
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from functools import cache
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from kpi.core import DATA_DIR, countries, load, run_scenario, weekly_csv
from kpi.fmt import SEP, change, count, grouped, money, money2, pct
from kpi.models import (
    ALL,
    FIRST_WEEK,
    FLAG_LABELS,
    LAST_WEEK,
    OUTSIDE_UK,
    UK,
    Filters,
    Flag,
)

REPO = Path(__file__).resolve().parents[3]
APP = str(REPO / "app.py")
DEFAULT_WEEK = date(2011, 11, 28)
END = LAST_WEEK + timedelta(days=6)
VIEWS = {
    "overview": "views/overview.py",
    "trends": "views/trends.py",
    "flags": "views/flags.py",
    "table": "views/table.py",
    "methodology": "views/methodology.py",
}
YOY = "vs same week last year"
NO_BASE = "No comparable week a year earlier: "
AI_LABEL = "AI-written summary, saved; numbers above are computed"
AI_HEADLINE = (
    "Revenue and orders jump to an unusually strong week, led by pantry products"
)
SHORT = (date(2011, 3, 7), date(2011, 4, 25))
FLAG_SHORT = {
    "no_data": "No sales",
    "partial_week": "Partial",
    "revenue_swing": "Revenue",
    "orders_swing": "Orders",
    "large_cancellations": "Cancels",
    "top_line": "Big line",
    "placed_cancelled": "Placed+cancelled",
}


@pytest.fixture(autouse=True)
def no_gc() -> Iterator[None]:
    """The AppTest media storage is only reachable until a gc pass; keep gc off while a test runs."""
    gc.disable()
    yield
    gc.enable()
    gc.collect()


@cache
def scen(
    country: str = ALL,
    week: date = DEFAULT_WEEK,
    start: date = FIRST_WEEK,
    end: date = LAST_WEEK,
) -> Any:
    return run_scenario(Filters(start=start, end=end, country=country, week=week))


def open_app(
    country: str = ALL,
    span: tuple[date, date] | None = None,
    week: date | None = None,
    page: str = "overview",
) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=60).run()
    if country != ALL:
        at.selectbox(key="country").select(country).run()
    if span is not None:
        at.date_input(key="dates").set_value(
            (span[0], span[1] + timedelta(days=6))
        ).run()
    if week is not None:
        at.selectbox(key="week").select(week).run()
    if page != "overview":
        at.switch_page(VIEWS[page]).run()
    assert not at.exception
    return at


def markdowns(at: AppTest) -> list[str]:
    return [str(m.value) for m in at.markdown]


def metric(at: AppTest, label: str) -> Any:
    return next(m for m in at.metric if m.label == label)


def charts(at: AppTest) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [
        json.loads(c.proto.spec) for c in at.get("plotly_chart")
    ]
    return out


def revenue_chart(at: AppTest) -> dict[str, Any]:
    return charts(at)[0]


def y_at(trace: dict[str, Any], week: date) -> Any:
    xs = [str(x)[:10] for x in trace["x"]]
    return trace["y"][xs.index(str(week))]


def yoy_captions(at: AppTest) -> list[Any]:
    found = [c for c in at.main.caption if YOY in str(c.value)]
    assert len(found) == 3
    return found


def sparsest() -> str:
    return min(
        (c for c in countries() if c not in (ALL, UK, OUTSIDE_UK)),
        key=lambda c: scen(c).totals.orders,
    )


def sunday(d: date) -> date:
    return d + timedelta(days=6)


# ---------- year over year captions ----------


@pytest.mark.parametrize("country", [ALL, UK, OUTSIDE_UK, "Germany"])
def test_yoy_dash_for_partial_week_explains_why(country: str) -> None:
    at = open_app(country, None, LAST_WEEK)
    for cap in yoy_captions(at):
        assert cap.value == f"— {YOY}"
        assert (
            cap.proto.help
            == f"{NO_BASE}this week is partial, so there is no like-for-like base."
        )


@pytest.mark.parametrize(
    ("country", "week"),
    [
        (ALL, date(2010, 12, 27)),
        ("Bahrain", date(2011, 6, 6)),
        (UK, date(2010, 12, 27)),
    ],
)
def test_yoy_dash_for_no_sales_week(country: str, week: date) -> None:
    assert scen(country, week).selected.product_lines == 0
    at = open_app(country, None, week)
    for cap in yoy_captions(at):
        assert cap.value == f"— {YOY}"
        assert cap.proto.help == f"{NO_BASE}no sales this week."


def test_yoy_dash_when_partial_week_also_has_no_sales() -> None:
    at = open_app("Switzerland", None, LAST_WEEK)
    assert scen("Switzerland", LAST_WEEK).selected.product_lines == 0
    for cap in yoy_captions(at):
        assert cap.value == f"— {YOY}"
        assert cap.proto.help.startswith(NO_BASE)
        assert cap.proto.help.endswith(".")


def test_yoy_dash_when_base_week_has_no_sales() -> None:
    country, week = "Brazil", date(2011, 4, 11)
    base = week - timedelta(days=364)
    weekly = load(DATA_DIR, 0).weekly
    row = weekly[(weekly["filter"] == country) & (weekly["week_start"] == base)]
    assert scen(country, week).selected.product_lines > 0
    assert row.empty or row.iloc[0]["product_lines"] == 0
    at = open_app(country, None, week)
    for cap in yoy_captions(at):
        assert cap.value == f"— {YOY}"
        help_ = cap.proto.help
        assert help_.startswith(NO_BASE)
        assert f"{base} – {sunday(base)}" in help_
        assert "partial" not in help_
        assert "this week" not in help_


@pytest.mark.parametrize(
    ("country", "week"),
    [
        (ALL, date(2011, 9, 19)),
        (ALL, date(2011, 11, 28)),
        (ALL, date(2011, 1, 17)),
        (UK, date(2011, 5, 2)),
        (OUTSIDE_UK, date(2011, 11, 21)),
        ("Germany", date(2011, 9, 19)),
        ("EIRE", date(2011, 6, 20)),
        ("EIRE", date(2011, 2, 21)),
        ("Sweden", date(2011, 3, 7)),
    ],
)
def test_yoy_caption_and_base_value_in_help(country: str, week: date) -> None:
    w = scen(country, week).selected
    base = week - timedelta(days=364)
    weekly = load(DATA_DIR, 0).weekly
    row = weekly[(weekly["filter"] == country) & (weekly["week_start"] == base)].iloc[0]
    net = float(row["revenue"] - row["cancelled_value"])
    orders = int(row["orders"])
    want = [
        (w.net_revenue_yoy, money(net)),
        (w.orders_yoy, count(orders)),
        (w.net_aov_yoy, money2(net / orders)),
    ]
    at = open_app(country, None, week)
    for cap, (yoy, base_text) in zip(yoy_captions(at), want, strict=True):
        assert yoy is not None
        assert cap.value == f"{change(yoy)} {YOY}"
        assert (
            cap.proto.help
            == f"Same week a year earlier: {base} – {sunday(base)}, {base_text}."
        )


def test_yoy_caption_follows_each_card() -> None:
    at = open_app(ALL, None, date(2011, 9, 19))
    w = scen(ALL, date(2011, 9, 19)).selected
    assert [c.value for c in yoy_captions(at)] == [
        f"{change(w.net_revenue_yoy)} {YOY}",
        f"{change(w.orders_yoy)} {YOY}",
        f"{change(w.net_aov_yoy)} {YOY}",
    ]
    assert not [c for c in at.main.caption if "wrong" in str(c.value)]


# ---------- Trends: Net / Gross and the y range ----------


def revenue_values(s: Any, measure: str) -> list[float]:
    key = "net_revenue" if measure == "Net" else "revenue"
    return [getattr(w, key) for w in s.weeks]


def full_values(s: Any, measure: str) -> list[float]:
    return [
        v
        for v, w in zip(revenue_values(s, measure), s.weeks, strict=True)
        if w.product_lines > 0 and not any(f.rule == "partial_week" for f in w.flags)
    ]


def set_measure(at: AppTest, measure: str) -> AppTest:
    return at.segmented_control(key="measure").set_value(measure).run()


@pytest.mark.parametrize("measure", ["Net", "Gross"])
def test_measure_picks_series_title_and_values(measure: str) -> None:
    at = open_app(ALL, None, None, "trends")
    other = "Gross" if measure == "Net" else "Net"
    assert at.segmented_control(key="measure").value == "Net"
    set_measure(at, measure)
    assert not at.exception
    s = scen()
    assert f"**{measure} revenue per week**" in markdowns(at)
    assert f"**{other} revenue per week**" not in markdowns(at)
    main = revenue_chart(at)["data"][0]
    assert main["name"] == f"{measure} revenue"
    names = [t.get("name") for t in revenue_chart(at)["data"]]
    assert f"{other} revenue" not in names
    for w, v in zip(s.weeks, revenue_values(s, measure), strict=True):
        got = y_at(main, w.week_start)
        if w.product_lines == 0 or w.week_start == LAST_WEEK:
            assert got is None, w.week_start
        else:
            assert got == pytest.approx(v), w.week_start


def test_measure_round_trip_and_cleared_control() -> None:
    at = open_app(ALL, None, None, "trends")
    net = revenue_chart(at)["data"][0]["y"]
    set_measure(at, "Gross")
    gross = revenue_chart(at)["data"][0]["y"]
    assert gross != net
    set_measure(at, "Net")
    assert revenue_chart(at)["data"][0]["y"] == net
    at.segmented_control(key="measure").set_value(None).run()
    assert not at.exception
    assert "**Net revenue per week**" in markdowns(at)
    assert revenue_chart(at)["data"][0]["y"] == net


def test_measure_does_not_change_other_charts() -> None:
    at = open_app(ALL, None, None, "trends")
    before = [json.dumps(c["data"], sort_keys=True) for c in charts(at)[1:]]
    set_measure(at, "Gross")
    assert [json.dumps(c["data"], sort_keys=True) for c in charts(at)[1:]] == before
    titles = [
        m for m in markdowns(at) if re.fullmatch(r"\*\*[A-Z][^*]* per week[^*]*\*\*", m)
    ]
    assert titles == [
        "**Gross revenue per week**",
        "**Orders per week**",
        "**Customers per week: returning and new**",
        "**Cancelled value per week**",
    ]


def test_partial_annotation_uses_gross_share_for_both_measures() -> None:
    p = scen().weeks[-1]
    want = f"Partial · {pct(100 * p.cancelled_value / p.revenue)} cancelled"
    at = open_app(ALL, None, None, "trends")
    for measure in ("Net", "Gross"):
        set_measure(at, measure)
        texts = [a["text"] for a in revenue_chart(at)["layout"]["annotations"]]
        assert texts == [want]


Y_CASES = [
    (ALL, None),
    (UK, None),
    (OUTSIDE_UK, None),
    ("Germany", None),
    (ALL, SHORT),
    (ALL, (date(2011, 11, 7), date(2011, 11, 28))),
    (ALL, (date(2011, 6, 6), date(2011, 6, 6))),
    (ALL, (date(2011, 11, 28), LAST_WEEK)),
    (sparsest(), None),
    ("Spain", None),
    ("Spain", (date(2011, 10, 17), date(2011, 10, 17))),
    ("Switzerland", None),
]


@pytest.mark.parametrize("measure", ["Net", "Gross"])
@pytest.mark.parametrize(("country", "span"), Y_CASES)
def test_revenue_y_range_excludes_partial_week(
    country: str, span: tuple[date, date] | None, measure: str
) -> None:
    start, end = span or (FIRST_WEEK, LAST_WEEK)
    at = open_app(country, span, None, "trends")
    set_measure(at, measure)
    assert not at.exception
    s = scen(country, end, start, end)
    full = full_values(s, measure)
    rev = revenue_chart(at)
    rng = rev["layout"]["yaxis"].get("range")
    if not full or max(full) <= 0:
        assert rng is None
        return
    assert rng[1] == pytest.approx(1.08 * max(full))
    assert rng[0] == pytest.approx(min(0.0, 1.08 * min(full)))
    assert rev["layout"]["yaxis"]["rangemode"] == "tozero"
    partial = next((t for t in rev["data"] if t.get("name") == "Partial week"), None)
    if partial is not None:
        assert all(y <= rng[1] + 1e-6 for y in partial["y"] if y is not None)
    for a in rev["layout"].get("annotations", []):
        assert a["y"] <= rng[1] + 1e-6


def test_partial_week_higher_than_full_weeks_does_not_stretch_axis() -> None:
    s = scen()
    full = full_values(s, "Gross")
    assert s.weeks[-1].revenue > 1.08 * max(full)
    at = open_app(ALL, None, None, "trends")
    set_measure(at, "Gross")
    rng = revenue_chart(at)["layout"]["yaxis"]["range"]
    assert rng[1] == pytest.approx(1.08 * max(full))
    assert rng[1] < s.weeks[-1].revenue


def test_other_charts_have_no_fixed_range() -> None:
    at = open_app(ALL, None, None, "trends")
    for c in charts(at)[1:]:
        assert "range" not in c["layout"]["yaxis"]


@pytest.mark.parametrize("measure", ["Net", "Gross"])
def test_one_week_range_axis_scales_to_that_week(measure: str) -> None:
    week = date(2011, 6, 6)
    at = open_app(ALL, (week, week), None, "trends")
    set_measure(at, measure)
    s = scen(ALL, week, week, week)
    value = revenue_values(s, measure)[0]
    rev = revenue_chart(at)
    assert rev["layout"]["yaxis"]["range"][1] == pytest.approx(1.08 * value)
    assert rev["data"][0]["y"] == [pytest.approx(value)]
    assert "Partial week" not in [t.get("name") for t in rev["data"]]
    assert rev["layout"].get("annotations", []) == []


def test_all_empty_country_weeks_have_no_axis_and_no_exception() -> None:
    country = "Brazil"
    empty = date(2011, 6, 6)
    assert scen(country, empty).selected.product_lines == 0
    at = open_app(country, (date(2011, 5, 30), date(2011, 6, 13)), None, "trends")
    for measure in ("Net", "Gross"):
        set_measure(at, measure)
        assert not at.exception
        cs = charts(at)
        assert len(cs) == 4
        rev = cs[0]
        assert rev["data"][0]["y"] == [None, None, None]
        assert "range" not in rev["layout"]["yaxis"]


def test_partial_week_without_sales_draws_no_partial_trace() -> None:
    at = open_app("Switzerland", None, None, "trends")
    rev = revenue_chart(at)
    assert "Partial week" not in [t.get("name") for t in rev["data"]]
    assert not rev["layout"].get("annotations")
    assert y_at(rev["data"][0], LAST_WEEK) is None


def test_partial_only_range_has_trace_but_no_axis_range() -> None:
    at = open_app(ALL, (LAST_WEEK, LAST_WEEK), None, "trends")
    rev = revenue_chart(at)
    assert "range" not in rev["layout"]["yaxis"]
    tr = next(t for t in rev["data"] if t.get("name") == "Partial week")
    assert tr["showlegend"] is False
    assert [str(x)[:10] for x in tr["x"]] == [str(LAST_WEEK)]


def test_cancelled_value_chart_replaces_cancellation_rate() -> None:
    at = open_app(ALL, None, None, "trends")
    s = scen()
    chart = charts(at)[3]
    assert "**Cancelled value per week**" in markdowns(at)
    assert not [m for m in markdowns(at) if "ancellation rate" in m]
    tr = chart["data"][0]
    for w in s.weeks:
        got = y_at(tr, w.week_start)
        if w.product_lines == 0:
            assert got is None
        else:
            assert got == pytest.approx(w.cancelled_value)
    assert chart["layout"]["yaxis"]["tickprefix"] == "£"


# ---------- driver lines ----------


def expected_item_lines(flag: Flag) -> list[str]:
    lines = []
    for d in flag.drivers:
        if not d.items:
            continue
        parts = []
        for i in d.items:
            sign = "+" if i.change >= 0 else "-"
            if flag.rule == "revenue_swing":
                amount = money(abs(i.change))
            else:
                q = Decimal(str(round(abs(i.change), 9))).quantize(
                    Decimal("0.1"), ROUND_HALF_UP
                )
                amount = f"{grouped(q.to_integral_value() if q == q.to_integral_value() else q)} orders"
            parts.append(f"{i.label} {sign}{amount}")
        what = "products" if d.by == "product" else "countries"
        lines.append(
            f"Top {what}: {' · '.join(parts)} ({pct(d.explained_pct)} of the change)"
        )
    return lines


def expected_list(flags: list[Flag], template: str) -> str:
    out = []
    for f in flags:
        label = FLAG_LABELS[f.rule]
        head = (
            f"- {f.reason}"
            if f.reason.startswith(f"{label}:")
            else template.format(label=label, reason=f.reason)
        )
        out.append(head + "".join(f"\n    - {x}" for x in expected_item_lines(f)))
    return "\n".join(out)


def flag_week(country: str, rule: str, nth: int = 0) -> date:
    weeks: list[date] = [
        w.week_start for w in scen(country).weeks if rule in {f.rule for f in w.flags}
    ]
    return weeks[nth]


def details_text(at: AppTest) -> str:
    box = next(e for e in at.expander if e.label == "Flag details")
    return "\n".join(str(m.value) for m in box.markdown)


def test_known_driver_lines_signs_and_numbers() -> None:
    sep = SEP
    text = details_text(open_app(ALL, None, date(2011, 9, 19)))
    assert f"Set Of Tea Coffee Sugar Tins Pantry +£8{sep}265" in text
    assert "Top products: " in text and "Top countries: " in text
    assert text.index("Top products") < text.index("Top countries")
    assert f"United Kingdom +£113{sep}442" in text
    down = details_text(open_app(ALL, None, date(2010, 12, 20)))
    assert f"Regency Cakestand 3 Tier -£5{sep}180" in down
    assert "+£" not in down.split("Top products:")[1].split("\n")[0]


def test_orders_format_whole_versus_decimal_and_half_up() -> None:
    may = details_text(open_app(ALL, None, date(2011, 5, 9)))
    assert "Germany +5 orders" in may
    assert "France +6.3 orders" in may
    assert "United Kingdom +111.3 orders" in may
    assert ".0 orders" not in may
    dec = details_text(open_app(ALL, None, date(2010, 12, 20)))
    assert "United Kingdom -393.8 orders" in dec
    assert "Germany -6.8 orders" in dec
    assert "EIRE -3.5 orders" in dec


def test_every_orders_driver_line_matches_format_everywhere() -> None:
    pattern = re.compile(r"^.+ [+-][\d ]+(\.\d)? orders$")
    seen = 0
    for country in (ALL, OUTSIDE_UK):
        for w in scen(country).weeks:
            for f in w.flags:
                if f.rule != "orders_swing":
                    continue
                for line in expected_item_lines(f):
                    body = line.split(": ", 1)[1].rsplit(" (", 1)[0]
                    for item in body.split(" · "):
                        assert pattern.match(item), item
                        assert ".0 orders" not in item
                        seen += 1
    assert seen > 10


@pytest.mark.parametrize(
    ("country", "rule", "products", "countries_"),
    [
        (ALL, "revenue_swing", True, True),
        (ALL, "orders_swing", False, True),
        (OUTSIDE_UK, "revenue_swing", True, True),
        (OUTSIDE_UK, "orders_swing", False, True),
        (UK, "revenue_swing", True, False),
        ("Germany", "revenue_swing", True, False),
        ("Switzerland", "revenue_swing", True, False),
    ],
)
def test_overview_flag_details_have_drivers_per_filter(
    country: str, rule: str, products: bool, countries_: bool
) -> None:
    week = flag_week(country, rule)
    at = open_app(country, None, week)
    flags = scen(country, week).selected.flags
    text = details_text(at)
    assert text == expected_list(flags, "- **{label}** · {reason}")
    swing = next(f for f in flags if f.rule == rule)
    block = expected_item_lines(swing)
    assert any(line.startswith("Top products:") for line in block) == products
    assert any(line.startswith("Top countries:") for line in block) == countries_


@pytest.mark.parametrize("country", ["Germany", "France", UK])
def test_orders_swing_of_single_filters_has_no_driver_lines(country: str) -> None:
    weeks = [
        w for w in scen(country).weeks if "orders_swing" in {f.rule for f in w.flags}
    ]
    assert weeks, country
    at = open_app(country, None, weeks[0].week_start)
    lines = details_text(at).split("\n")
    i = next(i for i, x in enumerate(lines) if x.startswith("- **Orders swing** · "))
    assert i == len(lines) - 1 or not lines[i + 1].startswith("    - ")
    assert "Top countries" not in "\n".join(lines)


def test_placed_and_cancelled_reason_printed_once_on_overview() -> None:
    for week in (date(2011, 1, 17), LAST_WEEK):
        flags = scen(ALL, week).selected.flags
        pc = next(f for f in flags if f.rule == "placed_cancelled")
        at = open_app(ALL, None, week)
        text = details_text(at)
        assert text.count("Placed and cancelled") == 1
        assert f"- {pc.reason}" in text
        assert "**Placed and cancelled**" not in text
        assert " · Placed and cancelled:" not in text
        assert text == expected_list(flags, "- **{label}** · {reason}")


@pytest.mark.parametrize("country", [ALL, UK, OUTSIDE_UK, "Germany", "Switzerland"])
def test_flagged_weeks_list_with_driver_lines_equals_expected(country: str) -> None:
    at = open_app(country, None, None, "flags")
    s = scen(country)
    vals = markdowns(at)
    heads = [v for v in vals if v.startswith("**20")]
    flagged = [w for w in s.weeks if w.flags]
    assert len(heads) == len(flagged)
    for head, w in zip(heads, flagged, strict=True):
        assert vals[vals.index(head) + 1] == expected_list(
            w.flags, "- **{label}:** {reason}"
        )


def test_flagged_weeks_placed_cancelled_once_and_orange_badge() -> None:
    at = open_app(ALL, None, None, "flags")
    vals = markdowns(at)
    head = next(v for v in vals if v.startswith(f"**{LAST_WEEK} "))
    assert ":gray-badge[Partial week]" in head
    assert ":orange-badge[Placed and cancelled]" in head
    listed = vals[vals.index(head) + 1]
    assert listed.count("Placed and cancelled") == 1
    assert listed.splitlines()[0].startswith("- **Partial week:** ")
    assert listed.splitlines()[1].startswith("- Placed and cancelled: ")


def test_flagged_weeks_nested_lines_are_indented_under_their_flag() -> None:
    at = open_app(ALL, None, None, "flags")
    vals = markdowns(at)
    head = next(v for v in vals if v.startswith("**2010-12-20 "))
    lines = vals[vals.index(head) + 1].split("\n")
    assert lines[0].startswith("- **Revenue swing:** ")
    assert lines[1].startswith("    - Top products: ")
    assert lines[2].startswith("    - Top countries: ")
    assert lines[3].startswith("- **Orders swing:** ")
    assert lines[4].startswith("    - Top countries: ")
    assert len(lines) == 5


def test_driver_lines_end_with_percent_explained() -> None:
    at = open_app(ALL, None, None, "flags")
    lines = [
        line
        for m in markdowns(at)
        for line in m.split("\n")
        if line.startswith("    - Top ")
    ]
    assert lines
    assert all(re.search(r" \(\d[\d ]*\.\d% of the change\)$", x) for x in lines)


# ---------- Weekly table ----------

BASE_COLS = [
    "Week",
    "Flags",
    "Net revenue",
    "Gross",
    "Orders",
    "Avg order (net)",
    "Units",
    "Customers",
    "New",
    "Returning",
    "Cancelled",
]
CHANGE_COLS = ["Net vs last week", "Net vs last year", "Orders vs last week"]


def frame(at: AppTest) -> Any:
    assert len(at.dataframe) == 1
    return at.dataframe[0]


def toggled(at: AppTest, key: str, on: bool = True) -> AppTest:
    return at.toggle(key=key).set_value(on).run()


@pytest.mark.parametrize(
    ("country", "span", "rows"),
    [
        (ALL, None, 8),
        ("Bahrain", None, 8),
        (ALL, SHORT, 8),
        (ALL, (date(2011, 3, 7), date(2011, 4, 4)), 5),
        (ALL, (date(2011, 3, 7), date(2011, 3, 14)), 2),
        (ALL, (LAST_WEEK, LAST_WEEK), 1),
        (ALL, (date(2011, 3, 7), date(2011, 4, 18)), 7),
    ],
)
def test_default_table_shows_last_eight_weeks(
    country: str, span: tuple[date, date] | None, rows: int
) -> None:
    start, end = span or (FIRST_WEEK, LAST_WEEK)
    at = open_app(country, span, None, "table")
    s = scen(country, end, start, end)
    df = frame(at).value
    assert len(df) == rows == min(8, len(s.weeks))
    assert df["Week"].astype(str).tolist() == [str(w.week_start) for w in s.weeks[-8:]]
    assert list(df.columns) == BASE_COLS


def test_all_weeks_toggle_round_trip() -> None:
    at = open_app(ALL, None, None, "table")
    toggled(at, "all_weeks")
    assert len(frame(at).value) == 53
    toggled(at, "all_weeks", False)
    assert len(frame(at).value) == 8
    assert frame(at).value["Week"].tolist()[-1] == str(LAST_WEEK)


def test_changes_toggle_adds_only_the_three_columns() -> None:
    at = open_app(ALL, None, None, "table")
    toggled(at, "changes")
    cols = list(frame(at).value.columns)
    assert set(cols) - set(BASE_COLS) == set(CHANGE_COLS)
    assert [c for c in cols if c in BASE_COLS] == BASE_COLS
    assert len(frame(at).value) == 8
    toggled(at, "changes", False)
    assert list(frame(at).value.columns) == BASE_COLS


def test_toggles_survive_filter_changes() -> None:
    at = open_app(ALL, None, None, "table")
    toggled(at, "all_weeks")
    toggled(at, "changes")
    at.selectbox(key="country").select("France").run()
    assert not at.exception
    assert len(frame(at).value) == 53
    assert set(CHANGE_COLS) <= set(frame(at).value.columns)
    at.button(key="reset").click().run()
    assert at.toggle(key="all_weeks").value is True


def test_na_cells_for_missing_values() -> None:
    country = "Bahrain"
    at = open_app(country, None, None, "table")
    toggled(at, "all_weeks")
    toggled(at, "changes")
    assert frame(at).proto.placeholder == "n/a"
    df = frame(at).value
    s = scen(country)
    empty = [i for i, w in enumerate(s.weeks) if w.product_lines == 0]
    assert len(empty) > 40
    for i in empty:
        assert df["Avg order (net)"].isna().iloc[i]
        assert df["Orders"].iloc[i] == 0
    for col, key in zip(
        CHANGE_COLS, ("net_revenue_wow", "net_revenue_yoy", "orders_wow"), strict=True
    ):
        for i, w in enumerate(s.weeks):
            assert df[col].isna().iloc[i] == (getattr(w, key) is None), (col, i)
    assert any(df["Net vs last week"].isna())


def test_change_columns_and_net_yoy_match_core() -> None:
    at = open_app(UK, None, None, "table")
    toggled(at, "all_weeks")
    toggled(at, "changes")
    df = frame(at).value
    s = scen(UK)
    for col, key in zip(
        CHANGE_COLS, ("net_revenue_wow", "net_revenue_yoy", "orders_wow"), strict=True
    ):
        for got, w in zip(df[col].tolist(), s.weeks, strict=True):
            want = getattr(w, key)
            assert pd.isna(got) if want is None else got == pytest.approx(want)
    assert pd.isna(df["Net vs last year"].iloc[-1])


def test_flag_column_short_labels_for_two_flag_week() -> None:
    at = open_app(ALL, None, None, "table")
    df = frame(at).value
    assert df["Flags"].tolist()[-1] == "Partial, Placed+cancelled"
    toggled(at, "all_weeks")
    flags = frame(at).value["Flags"].tolist()
    s = scen()
    assert flags == [", ".join(FLAG_SHORT[f.rule] for f in w.flags) for w in s.weeks]
    assert (
        "Placed+cancelled"
        in flags[
            s.weeks.index(next(w for w in s.weeks if w.week_start == date(2011, 1, 17)))
        ]
    )


def test_spain_negative_week_is_inside_the_axis() -> None:
    week = date(2011, 10, 17)
    assert scen("Spain", week).selected.net_revenue < 0
    at = open_app("Spain", None, None, "trends")
    rng = revenue_chart(at)["layout"]["yaxis"]["range"]
    assert rng[0] <= 1.08 * scen("Spain", week).selected.net_revenue + 1e-6
    assert rng[0] < 0 < rng[1]
    assert y_at(revenue_chart(at)["data"][0], week) == pytest.approx(
        scen("Spain", week).selected.net_revenue
    )


def test_one_week_negative_range_is_not_inverted() -> None:
    week = date(2011, 10, 17)
    for measure in ("Net", "Gross"):
        at = open_app("Spain", (week, week), None, "trends")
        set_measure(at, measure)
        assert not at.exception
        rng = revenue_chart(at)["layout"]["yaxis"].get("range")
        assert rng is None or rng[0] < rng[1]


@pytest.mark.parametrize("country", [ALL, UK])
def test_partial_value_above_top_is_clamped_with_true_value_in_customdata(
    country: str,
) -> None:
    s = scen(country)
    full = full_values(s, "Gross")
    top = 1.08 * max(full)
    true = s.weeks[-1].revenue
    assert true > top
    at = open_app(country, None, None, "trends")
    set_measure(at, "Gross")
    rev = revenue_chart(at)
    tr = next(t for t in rev["data"] if t.get("name") == "Partial week")
    assert y_at(tr, LAST_WEEK) == pytest.approx(top)
    assert y_at({"x": tr["x"], "y": tr["customdata"]}, LAST_WEEK) == pytest.approx(true)
    assert "customdata" in tr["hovertemplate"]
    (note,) = rev["layout"]["annotations"]
    assert note["ay"] == 36
    assert note["y"] == pytest.approx(top)


@pytest.mark.parametrize(
    ("country", "measure"), [(ALL, "Net"), (UK, "Net"), ("Germany", "Gross")]
)
def test_partial_value_within_top_is_not_clamped(country: str, measure: str) -> None:
    s = scen(country)
    top = 1.08 * max(full_values(s, measure))
    true = revenue_values(s, measure)[-1]
    assert 0 < true <= top
    at = open_app(country, None, None, "trends")
    set_measure(at, measure)
    rev = revenue_chart(at)
    tr = next(t for t in rev["data"] if t.get("name") == "Partial week")
    assert y_at(tr, LAST_WEEK) == pytest.approx(true)
    (note,) = rev["layout"]["annotations"]
    assert note["ay"] == -36
    assert note["y"] == pytest.approx(true)


@pytest.mark.parametrize(
    ("country", "week"),
    [
        ("France", date(2011, 9, 26)),
        ("France", date(2011, 8, 1)),
        ("Spain", date(2011, 10, 17)),
    ],
)
def test_yoy_dash_for_non_positive_base_names_the_base_week(
    country: str, week: date
) -> None:
    base = week - timedelta(days=364)
    w = scen(country, week).selected
    assert w.product_lines > 0 and w.net_revenue_yoy is None
    at = open_app(country, None, week)
    cap = yoy_captions(at)[0]
    assert cap.value == f"— {YOY}"
    assert (
        cap.proto.help
        == f"{NO_BASE}{base} – {sunday(base)} had no sales or a zero or negative value."
    )


def test_theme_returning_is_muted_and_new_is_blue() -> None:
    from kpi import theme

    assert theme.RETURNING == theme.MUTED
    assert theme.NEW == theme.BLUE
    at = open_app(ALL, None, None, "trends")
    bars = charts(at)[2]["data"]
    assert {t["name"]: t["marker"]["color"] for t in bars} == {
        "Returning": theme.MUTED,
        "New": theme.BLUE,
    }


def test_driver_lines_folded_into_flag_line() -> None:
    from views import ui

    assert not hasattr(ui, "driver_lines")
    flag = scen(ALL, date(2011, 9, 19)).selected.flags[0]
    out = ui.flag_line(flag, "- **{label}** · {reason}")
    assert out == expected_list([flag], "- **{label}** · {reason}")


# ---------- CSV ----------


def download_file(button: Any) -> tuple[str, bytes]:
    from streamlit.runtime.media_file_manager import MediaFileManager
    from streamlit.runtime.media_file_storage import MediaFileStorageError

    file_id = button.proto.url.split("/")[-1].split(".")[0]
    for obj in gc.get_objects():
        if isinstance(obj, MediaFileManager):
            try:
                storage: Any = obj._storage
                f = storage.get_file(file_id)
            except MediaFileStorageError:
                continue
            return f.filename or "", f.content
    raise AssertionError("download not found")


@pytest.mark.parametrize("all_weeks", [False, True])
@pytest.mark.parametrize("changes", [False, True])
@pytest.mark.parametrize("country", [ALL, "Bahrain"])
def test_csv_stays_all_weeks_whatever_the_toggles(
    country: str, changes: bool, all_weeks: bool
) -> None:
    at = open_app(country, None, None, "table")
    toggled(at, "all_weeks", all_weeks)
    toggled(at, "changes", changes)
    s = scen(country, at.selectbox(key="week").value)
    name, content = download_file(at.get("download_button")[0])
    assert content == weekly_csv(s)
    assert content.decode().count("\n") == s.totals.weeks + 1
    assert (
        name
        == f"weekly-kpis_{FIRST_WEEK}_{LAST_WEEK}_{country.lower().replace(' ', '-')}.csv"
    )


# ---------- AI summary ----------


def ai_boxes(at: AppTest) -> list[Any]:
    return [e for e in at.expander if e.label == AI_LABEL]


def test_ai_summary_only_inside_labelled_expander() -> None:
    at = open_app(ALL, None, date(2011, 9, 19))
    (box,) = ai_boxes(at)
    inside = {str(m.value) for m in box.markdown}
    assert f"**{AI_HEADLINE}**" in inside
    assert not any('"' in v for v in inside)
    outside = [m for m in markdowns(at) if m not in inside]
    assert not [m for m in outside if AI_HEADLINE in m]
    summary = [v for v in inside if AI_HEADLINE not in v]
    assert summary
    for v in summary:
        assert v not in outside
    assert any(
        "Weekly summary written by AI in an earlier run" in str(c.value)
        for c in box.caption
    )
    assert "This app makes no AI calls." in "".join(str(c.value) for c in box.caption)
    assert not [
        e for e in at.expander if e.label != AI_LABEL and e.label != "Flag details"
    ]


@pytest.mark.parametrize("country", [UK, OUTSIDE_UK, "Germany", "Brazil"])
def test_ai_summary_hidden_for_country_filters(country: str) -> None:
    at = open_app(country, None, date(2011, 9, 19))
    assert not ai_boxes(at)
    assert any(
        i.value
        == "The saved weekly summary covers all countries, so it is hidden while a country filter is on."
        for i in at.info
    )
    assert not [m for m in markdowns(at) if AI_HEADLINE in m]
    assert not [c for c in at.main.caption if "Weekly summary written" in str(c.value)]


def test_ai_summary_returns_when_filter_is_cleared() -> None:
    at = open_app(UK, None, date(2011, 9, 19))
    assert not ai_boxes(at)
    at.button(key="reset").click().run()
    at.selectbox(key="week").select(date(2011, 9, 19)).run()
    assert len(ai_boxes(at)) == 1
    assert not at.info


def test_no_sales_week_has_no_expander_and_a_note() -> None:
    at = open_app(ALL, None, date(2010, 12, 27))
    assert not ai_boxes(at)
    assert "No saved summary for this week (no sales)." in [
        str(c.value) for c in at.main.caption
    ]
    assert not at.info


@pytest.mark.parametrize(
    "week", [FIRST_WEEK, date(2011, 1, 17), date(2011, 5, 9), LAST_WEEK]
)
def test_ai_summary_matches_saved_text_per_week(week: date) -> None:
    summary = scen(ALL, week).summary
    assert summary is not None
    at = open_app(ALL, None, week)
    (box,) = ai_boxes(at)
    values = [str(m.value) for m in box.markdown]
    assert values[0] == f"**{summary.headline.replace(chr(34), '')}**"
    assert values[1] == summary.text.replace(chr(34), "")
    assert s_headline(week) not in [v for v in values]


def s_headline(week: date) -> str:
    out: str = scen(ALL, week).headline
    return out


# ---------- one net revenue everywhere ----------

NET_CASES = [
    (ALL, date(2011, 9, 19)),
    (ALL, date(2010, 12, 6)),
    (ALL, LAST_WEEK),
    (ALL, date(2010, 12, 27)),
    (UK, date(2011, 5, 2)),
    (OUTSIDE_UK, date(2011, 11, 21)),
    ("Germany", date(2011, 3, 7)),
    ("Spain", date(2011, 10, 17)),
    ("Bahrain", date(2011, 6, 6)),
]


@pytest.mark.parametrize(("country", "week"), NET_CASES)
def test_same_net_revenue_on_card_headline_trends_and_table(
    country: str, week: date
) -> None:
    s = scen(country, week)
    w = s.selected
    at = open_app(country, None, week)
    assert metric(at, "Net revenue").value == money(w.net_revenue)
    assert s.headline in markdowns(at)
    if w.product_lines > 0:
        assert f"Net revenue {money(w.net_revenue)}" in s.headline
    assert f"net revenue {money(s.totals.net_revenue)} " in " ".join(
        str(c.value) for c in at.main.caption
    )
    at.switch_page(VIEWS["trends"]).run()
    rev = revenue_chart(at)
    partial = week == LAST_WEEK and w.product_lines > 0
    if w.product_lines == 0:
        assert y_at(rev["data"][0], week) is None
    elif partial:
        assert y_at(rev["data"][0], week) is None
        tr = next(t for t in rev["data"] if t.get("name") == "Partial week")
        assert y_at(tr, week) == pytest.approx(w.net_revenue)
    else:
        assert y_at(rev["data"][0], week) == pytest.approx(w.net_revenue)
    at.switch_page(VIEWS["table"]).run()
    toggled(at, "all_weeks")
    df = frame(at).value
    row = df[df["Week"] == str(week)].iloc[0]
    assert row["Net revenue"] == pytest.approx(w.net_revenue)
    assert row["Gross"] == pytest.approx(w.revenue)
    assert row["Net revenue"] == pytest.approx(row["Gross"] - row["Cancelled"])


def test_range_net_equals_sum_of_weekly_net() -> None:
    at = open_app(ALL, None, None, "table")
    toggled(at, "all_weeks")
    df = frame(at).value
    s = scen()
    assert float(df["Net revenue"].sum()) == pytest.approx(s.totals.net_revenue)
    assert any(
        f"net revenue {money(s.totals.net_revenue)} " in str(c.value)
        for c in at.main.caption
    )


# ---------- no exceptions ----------

SWEEP = [
    ("preset-full", ALL, None),
    ("preset-q4", ALL, (date(2011, 10, 3), LAST_WEEK)),
    ("preset-uk", UK, None),
    ("preset-outside", OUTSIDE_UK, None),
    ("sparse", sparsest(), None),
    ("brazil", "Brazil", None),
    ("spain", "Spain", None),
    ("one-week", ALL, (date(2011, 6, 6), date(2011, 6, 6))),
    ("one-week-empty-country", "Bahrain", (date(2011, 6, 6), date(2011, 6, 6))),
    ("one-week-negative", "Spain", (date(2011, 10, 17), date(2011, 10, 17))),
    ("partial-only", ALL, (LAST_WEEK, LAST_WEEK)),
    ("partial-only-uk", UK, (LAST_WEEK, LAST_WEEK)),
    ("partial-only-no-sales", "Switzerland", (LAST_WEEK, LAST_WEEK)),
]


@pytest.mark.parametrize("page", list(VIEWS))
@pytest.mark.parametrize(("name", "country", "span"), SWEEP)
def test_no_exception_on_any_page(
    name: str, country: str, span: tuple[date, date] | None, page: str
) -> None:
    at = open_app(country, span, None, page)
    assert not at.exception, name
    assert not at.error, name
    assert len(at.title) == 1
    if page == "trends":
        set_measure(at, "Gross")
        assert not at.exception, name
    if page == "table":
        toggled(at, "all_weeks")
        toggled(at, "changes")
        assert not at.exception, name


@pytest.mark.parametrize("preset", ["Full year", "Q4 2011", "UK only", "Outside UK"])
def test_presets_on_every_page_with_toggles_on(preset: str) -> None:
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.selectbox(key="preset").select(preset).run()
    for page in VIEWS.values():
        at.switch_page(page).run()
        assert not at.exception, (preset, page)
    at.switch_page(VIEWS["table"]).run()
    toggled(at, "all_weeks")
    toggled(at, "changes")
    assert not at.exception
