"""PART-B Graphite UX round QA: biggest move (DEC-30), Trends rank, newest-first flags (DEC-22), whole-number order drivers (DEC-24), full flag names and money2 in the table (DEC-28), open Flag details (DEC-19)."""

import gc
import html
import re
from collections.abc import Callable, Iterator
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

import pyarrow as pa
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import kpi.core
from kpi.core import run_scenario
from kpi.models import (
    ALL,
    FIRST_WEEK,
    FLAG_LABELS,
    LAST_WEEK,
    OUTSIDE_UK,
    UK,
    Driver,
    Drivers,
    Filters,
    Flag,
    Scenario,
)

REPO = Path(__file__).resolve().parents[3]
APP = str(REPO / "app.py")
VIEWS = {
    "overview": "views/overview.py",
    "trends": "views/trends.py",
    "flags": "views/flags.py",
    "table": "views/table.py",
}
DEFAULT_WEEK = date(2011, 11, 28)
NO_SALES_WEEK = date(2010, 12, 27)
NNBSP = " "
MOVE_FIELDS = (
    ("Net revenue", "net_revenue_wow"),
    ("Orders", "orders_wow"),
    ("Avg order (net)", "net_aov_wow"),
    ("Gross revenue", "revenue_wow"),
    ("Units", "units_wow"),
    ("Customers", "customers_wow"),
    ("New customers", "new_customers_wow"),
    ("Returning customers", "returning_customers_wow"),
)
ALL_WOW = {field: None for _, field in MOVE_FIELDS} | {"cancelled_value_wow": None}
ORDINALS = {
    1: "1st",
    2: "2nd",
    3: "3rd",
    4: "4th",
    11: "11th",
    12: "12th",
    13: "13th",
    21: "21st",
    22: "22nd",
    23: "23rd",
}


@pytest.fixture(autouse=True)
def isolated() -> Iterator[None]:
    gc.disable()
    st.cache_data.clear()
    yield
    st.cache_data.clear()
    gc.enable()
    gc.collect()


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
    at = AppTest.from_file(APP, default_timeout=120).run()
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


def read_strip(at: AppTest) -> dict[str, str]:
    (raw,) = [str(m.value) for m in at.markdown if "how-to-read" in str(m.value)]
    found = re.findall(r"<b>([A-Z ]+)</b><span[^>]*>(.*?)</span>", raw)
    assert [k for k, _ in found] == ["THE QUESTION", "RIGHT NOW", "DO THIS"]
    return {k: html.unescape(v) for k, v in found}


def patched(
    monkeypatch: pytest.MonkeyPatch, edit: Callable[[Scenario], Scenario]
) -> None:
    """Make the app see a scenario that `edit` rewrote (for cases real data cannot produce)."""
    real = kpi.core.run_scenario

    def run_scenario(filters: Filters) -> Scenario:
        return edit(real(filters))

    monkeypatch.setattr(kpi.core, "run_scenario", run_scenario)


def with_week(s: Scenario, updates: dict[date, dict[str, Any]]) -> Scenario:
    weeks = [w.model_copy(update=updates.get(w.week_start, {})) for w in s.weeks]
    chosen = next(w for w in weeks if w.week_start == s.selected.week_start)
    return s.model_copy(update={"weeks": weeks, "selected": chosen})


def half_up(value: float, places: str) -> Decimal:
    return Decimal(repr(round(value, 9))).quantize(Decimal(places), ROUND_HALF_UP)


def spaced(d: Decimal) -> str:
    return f"{d:,}".replace(",", NNBSP)


def expected_move(w: Any) -> str:
    """DEC-30 Overview RIGHT NOW from the core's week-over-week values (Cancelled is not ranked)."""
    moves = [
        (label, getattr(w, field))
        for label, field in MOVE_FIELDS
        if getattr(w, field) is not None
    ]
    if not moves:
        return "No comparison with last week."
    shown = [abs(half_up(v, "0.1")) for _, v in moves]
    i = shown.index(max(shown))
    value = half_up(moves[i][1], "0.1")
    text = f"Biggest move vs last week: {moves[i][0]} {'-' if value < 0 else '+'}{spaced(abs(value))}%"
    rest = shown[:i] + shown[i + 1 :]
    return text + (
        f"; the other cards moved within ±{spaced(max(rest))}%." if rest else "."
    )


# ---------- Overview: biggest move ----------


def test_default_week_text_is_the_acceptance_text() -> None:
    assert read_strip(open_app())["RIGHT NOW"] == (
        "Biggest move vs last week: New customers -16.2%; the other cards moved within ±7.6%."
    )


@pytest.mark.parametrize(
    ("country", "week", "label"),
    [
        ("Australia", date(2011, 8, 15), "Net revenue"),
        ("Belgium", date(2011, 4, 25), "Net revenue"),
        ("Belgium", date(2011, 2, 21), "New customers"),
        ("Australia", date(2011, 11, 21), "Net revenue"),
    ],
)
def test_biggest_move_tie_goes_to_the_first_card(
    country: str, week: date, label: str
) -> None:
    w = scen(country, week).selected
    rounded = [
        abs(half_up(getattr(w, f), "0.1"))
        for _, f in MOVE_FIELDS
        if getattr(w, f) is not None
    ]
    assert rounded.count(max(rounded)) > 1, "this week must hold a tie for the top"
    now = read_strip(open_app(country, None, week))["RIGHT NOW"]
    assert now == expected_move(w)
    assert now.startswith(f"Biggest move vs last week: {label} ")


def test_biggest_move_above_1000_percent_is_grouped() -> None:
    week = date(2011, 8, 15)
    w = scen("Australia", week).selected
    assert w.net_revenue_wow > 1000
    now = read_strip(open_app("Australia", None, week))["RIGHT NOW"]
    assert now == expected_move(w)
    assert re.match(
        rf"Biggest move vs last week: Net revenue \+\d{NNBSP}\d{{3}}\.\d%;", now
    )


def test_move_over_1000_percent_in_both_slots(monkeypatch: pytest.MonkeyPatch) -> None:
    patched(
        monkeypatch,
        lambda s: with_week(
            s,
            {
                DEFAULT_WEEK: ALL_WOW
                | {"net_revenue_wow": -1234.56, "orders_wow": 1100.04, "units_wow": 5.0}
            },
        ),
    )
    assert read_strip(open_app())["RIGHT NOW"] == (
        f"Biggest move vs last week: Net revenue -1{NNBSP}234.6%; the other cards moved within ±1{NNBSP}100.0%."
    )


def test_only_one_card_with_a_change(monkeypatch: pytest.MonkeyPatch) -> None:
    patched(
        monkeypatch,
        lambda s: with_week(s, {DEFAULT_WEEK: ALL_WOW | {"units_wow": -12.34}}),
    )
    assert read_strip(open_app())["RIGHT NOW"] == (
        "Biggest move vs last week: Units -12.3%."
    )


def test_no_card_with_a_change_real_week() -> None:
    week = date(2011, 1, 3)
    w = scen(ALL, week).selected
    assert w.product_lines > 0
    assert all(getattr(w, f) is None for _, f in MOVE_FIELDS)
    strip = read_strip(open_app(ALL, None, week))
    assert strip["RIGHT NOW"] == "No comparison with last week."
    assert strip["DO THIS"].startswith(
        "Nothing flagged." if not w.flags else "Read the flag details below: "
    )


def test_only_cancelled_changed_means_no_comparison(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patched(
        monkeypatch,
        lambda s: with_week(
            s, {DEFAULT_WEEK: ALL_WOW | {"cancelled_value_wow": 500.0}}
        ),
    )
    assert read_strip(open_app())["RIGHT NOW"] == "No comparison with last week."


def test_cancelled_is_left_out_even_with_a_huge_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patched(
        monkeypatch,
        lambda s: with_week(
            s,
            {DEFAULT_WEEK: ALL_WOW | {"cancelled_value_wow": 9000.0, "units_wow": 3.0}},
        ),
    )
    assert read_strip(open_app())["RIGHT NOW"] == (
        "Biggest move vs last week: Units +3.0%."
    )


@pytest.mark.parametrize("week", [date(2011, 9, 19), LAST_WEEK, date(2011, 1, 17)])
def test_cancelled_never_the_biggest_move_on_real_weeks(week: date) -> None:
    w = scen(ALL, week).selected
    assert abs(w.cancelled_value_wow) > max(
        abs(getattr(w, f)) for _, f in MOVE_FIELDS if getattr(w, f) is not None
    )
    now = read_strip(open_app(ALL, None, week))["RIGHT NOW"]
    assert "Cancelled" not in now
    assert now == expected_move(w)


def test_pick_uses_the_rounded_change_the_cards_show(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raw 10.049 is larger than 10.04, but both show +10.0%: the tie goes to the first card."""
    patched(
        monkeypatch,
        lambda s: with_week(
            s,
            {
                DEFAULT_WEEK: ALL_WOW
                | {"net_revenue_wow": 10.04, "orders_wow": 10.049, "units_wow": -9.96}
            },
        ),
    )
    at = open_app()
    assert read_strip(at)["RIGHT NOW"] == (
        "Biggest move vs last week: Net revenue +10.0%; the other cards moved within ±10.0%."
    )


def test_pick_rounds_half_up_like_the_card(monkeypatch: pytest.MonkeyPatch) -> None:
    patched(
        monkeypatch,
        lambda s: with_week(
            s,
            {DEFAULT_WEEK: ALL_WOW | {"net_revenue_wow": 10.05, "orders_wow": 10.0499}},
        ),
    )
    at = open_app()
    assert read_strip(at)["RIGHT NOW"] == (
        "Biggest move vs last week: Net revenue +10.1%; the other cards moved within ±10.0%."
    )
    card = next(m for m in at.metric if m.label == "Net revenue")
    assert str(card.delta) == "+10.1%"


def test_biggest_move_matches_the_core_on_every_week() -> None:
    for week in [w.week_start for w in scen().weeks][::4]:
        s = scen(ALL, week)
        if s.selected.product_lines == 0:
            continue
        got = read_strip(open_app(ALL, None, week))["RIGHT NOW"]
        assert got == expected_move(s.selected), week


def test_no_sales_week_has_its_own_text() -> None:
    strip = read_strip(open_app(ALL, None, NO_SALES_WEEK))
    assert strip["RIGHT NOW"] == "No sales this week."
    assert strip["DO THIS"] == "Pick another week in the sidebar."


def test_apostrophes_stay_literal_in_the_strip() -> None:
    at = open_app(ALL, None, LAST_WEEK, "trends")
    (raw,) = [str(m.value) for m in at.markdown if "how-to-read" in str(m.value)]
    assert "isn't ranked" in raw
    assert "&#x27;" not in raw and "&quot;" not in raw


# ---------- Trends: rank ----------


def ranked_full_weeks(country: str = ALL) -> list[Any]:
    s = scen(country)
    full = [
        w
        for w in s.weeks
        if w.product_lines > 0 and all(f.rule != "partial_week" for f in w.flags)
    ]
    ordered = sorted(full, key=lambda w: -w.net_revenue)
    assert len({w.net_revenue for w in full}) == len(full)
    return ordered


@pytest.mark.parametrize("rank", list(ORDINALS))
def test_trends_ordinal_for_each_rank(rank: int) -> None:
    ordered = ranked_full_weeks()
    week = ordered[rank - 1]
    at = open_app(ALL, None, week.week_start, "trends")
    digits = f"{week.net_revenue:,.0f}".replace(",", NNBSP)
    assert read_strip(at)["RIGHT NOW"] == (
        f"Week {week.week_start}: net revenue £{digits}, the {ORDINALS[rank]} highest of {len(ordered)} full weeks in range."
    )


def test_trends_last_rank_is_the_lowest_week() -> None:
    ordered = ranked_full_weeks()
    n = len(ordered)
    at = open_app(ALL, None, ordered[-1].week_start, "trends")
    now = read_strip(at)["RIGHT NOW"]
    assert n == 51
    assert "the 51st highest of 51 full weeks" in now


def test_trends_ties_share_the_better_rank(monkeypatch: pytest.MonkeyPatch) -> None:
    ordered = ranked_full_weeks()
    fourth, fifth, sixth = ordered[3], ordered[4], ordered[5]
    tie = {fifth.week_start: {"net_revenue": fourth.net_revenue}}
    patched(monkeypatch, lambda s: with_week(s, tie))
    for week, word in ((fourth, "4th"), (fifth, "4th"), (sixth, "6th")):
        at = open_app(ALL, None, week.week_start, "trends")
        assert (
            f"the {word} highest of {len(ordered)} full weeks"
            in read_strip(at)["RIGHT NOW"]
        )
        st.cache_data.clear()


def test_trends_partial_selected_week() -> None:
    best = ranked_full_weeks()[0]
    at = open_app(ALL, None, LAST_WEEK, "trends")
    digits = f"{best.net_revenue:,.0f}".replace(",", NNBSP)
    assert read_strip(at)["RIGHT NOW"] == (
        f"Week {LAST_WEEK} is partial, so it isn't ranked; highest full week {best.week_start} (£{digits})."
    )


def test_trends_no_sales_selected_week() -> None:
    best = ranked_full_weeks()[0]
    at = open_app(ALL, None, NO_SALES_WEEK, "trends")
    digits = f"{best.net_revenue:,.0f}".replace(",", NNBSP)
    assert read_strip(at)["RIGHT NOW"] == (
        f"Week {NO_SALES_WEEK} had no sales; highest full week {best.week_start} (£{digits})."
    )


@pytest.mark.parametrize(
    "span", [(LAST_WEEK, LAST_WEEK), (NO_SALES_WEEK, NO_SALES_WEEK)]
)
def test_trends_no_full_week_in_range(span: tuple[date, date]) -> None:
    now = read_strip(open_app(ALL, span, None, "trends"))["RIGHT NOW"]
    assert now == "No full week with sales in this range."


def test_trends_one_full_week_is_singular() -> None:
    week = date(2011, 6, 6)
    now = read_strip(open_app(ALL, (week, week), None, "trends"))["RIGHT NOW"]
    assert now.endswith(", the 1st highest of 1 full week in range.")


def test_trends_rank_ignores_partial_and_no_sales_weeks() -> None:
    """Two full weeks followed by the partial week: only the two full weeks are ranked."""
    s = scen(
        ALL, LAST_WEEK - timedelta(days=7), LAST_WEEK - timedelta(days=14), LAST_WEEK
    )
    full = [w for w in s.weeks if all(f.rule != "partial_week" for f in w.flags)]
    assert len(full) == 2
    low = min(full, key=lambda w: w.net_revenue)
    at = open_app(ALL, (full[0].week_start, LAST_WEEK), low.week_start, "trends")
    assert "the 2nd highest of 2 full weeks in range." in read_strip(at)["RIGHT NOW"]


# ---------- Flagged weeks ----------


def test_flags_one_week_range_is_singular_and_has_no_swing_text() -> None:
    at = open_app(ALL, (LAST_WEEK, LAST_WEEK), None, "flags")
    s = scen(ALL, LAST_WEEK, LAST_WEEK, LAST_WEEK)
    assert [f.rule for f in s.selected.flags] == ["partial_week", "placed_cancelled"]
    strip = read_strip(at)
    assert (
        strip["RIGHT NOW"]
        == "1 of 1 week flagged: Partial week 1 · Placed and cancelled 1."
    )
    assert strip["DO THIS"] == "Read each reason."


def test_flags_one_flagged_week_of_several_keeps_plural_weeks() -> None:
    span = (date(2011, 11, 21), LAST_WEEK)
    s = scen(ALL, LAST_WEEK, *span)
    assert s.totals.flagged_weeks == 1 and s.totals.weeks == 3
    strip = read_strip(open_app(ALL, span, None, "flags"))
    assert (
        strip["RIGHT NOW"]
        == "1 of 3 weeks flagged: Partial week 1 · Placed and cancelled 1."
    )
    assert strip["DO THIS"] == "Read each reason."


def test_flags_swing_in_range_gets_the_driver_sentence() -> None:
    strip = read_strip(open_app(ALL, None, None, "flags"))
    assert (
        strip["DO THIS"]
        == "Read each reason; for swings, the drivers show which products and countries moved."
    )


def test_flags_no_sales_week_alone_has_no_swing_text() -> None:
    strip = read_strip(open_app(ALL, (NO_SALES_WEEK, NO_SALES_WEEK), None, "flags"))
    assert strip["RIGHT NOW"] == "1 of 1 week flagged: No sales 1."
    assert strip["DO THIS"] == "Read each reason."


@pytest.mark.parametrize("country", [ALL, UK, OUTSIDE_UK, "Germany"])
def test_flag_cards_run_newest_first(country: str) -> None:
    at = open_app(country, None, None, "flags")
    heads = [str(m.value) for m in at.markdown if str(m.value).startswith("**20")]
    starts = [h[2:12] for h in heads]
    want = [str(w.week_start) for w in reversed(scen(country).weeks) if w.flags]
    assert starts == want
    assert starts == sorted(starts, reverse=True)
    assert starts[0] == str(LAST_WEEK)


def test_flags_within_a_week_keep_core_order() -> None:
    at = open_app(ALL, None, None, "flags")
    head = next(
        str(m.value) for m in at.markdown if str(m.value).startswith(f"**{LAST_WEEK} ")
    )
    assert head.index("Partial week") < head.index("Placed and cancelled")


# ---------- order driver lines ----------


def detail_lines(at: AppTest) -> str:
    box = next(e for e in at.expander if e.label == "Flag details")
    return "\n".join(str(m.value) for m in box.markdown)


def orders_flag(items: list[tuple[str, float]]) -> Flag:
    return Flag(
        week_start=DEFAULT_WEEK,
        rule="orders_swing",
        reason="Orders +40.0% vs 4-week average (100 vs 70)",
        drivers=[
            Drivers(
                by="country",
                items=[Driver(label=a, change=b) for a, b in items],
                explained_pct=100.0,
            )
        ],
    )


def test_order_drivers_whole_numbers_singular_and_half_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    flag = orders_flag(
        [
            ("Exactly One", 1.0),
            ("Half Rounds Up", 0.5),
            ("Minus One", -1.0),
            ("One And A Half", 1.5),
            ("Big", 1000.5),
        ]
    )
    patched(monkeypatch, lambda s: with_week(s, {DEFAULT_WEEK: {"flags": [flag]}}))
    text = detail_lines(open_app())
    assert (
        f"Top countries: Exactly One +1 order · Half Rounds Up +1 order · Minus One -1 order · One And A Half +2 orders · Big +1{NNBSP}001 orders (100.0% of the change)"
        in text
    )
    assert "+1 orders" not in text and "-1 orders" not in text


def test_order_drivers_minus_394_example(monkeypatch: pytest.MonkeyPatch) -> None:
    flag = orders_flag([("United Kingdom", -393.8), ("Germany", -6.8), ("EIRE", -3.5)])
    patched(monkeypatch, lambda s: with_week(s, {DEFAULT_WEEK: {"flags": [flag]}}))
    assert (
        "United Kingdom -394 orders · Germany -7 orders · EIRE -4 orders"
        in detail_lines(open_app())
    )


def test_order_drivers_real_week_example_on_overview_and_flags_page() -> None:
    week = date(2010, 12, 20)
    at = open_app(ALL, None, week)
    assert "United Kingdom -394 orders" in detail_lines(at)
    at.switch_page(VIEWS["flags"]).run()
    assert "United Kingdom -394 orders" in "\n".join(str(m.value) for m in at.markdown)


@pytest.mark.parametrize(
    ("week", "text"),
    [
        (date(2011, 2, 7), "EIRE -3 orders"),
        (date(2011, 8, 22), "Channel Islands +3 orders"),
        (date(2011, 11, 14), "Germany +13 orders"),
    ],
)
def test_order_drivers_half_goes_up_not_to_even(week: date, text: str) -> None:
    flag_orders = [
        i.change
        for f in scen(OUTSIDE_UK, week).selected.flags
        if f.rule == "orders_swing"
        for d in f.drivers
        for i in d.items
    ]
    assert any(abs(abs(c) % 1 - 0.5) < 1e-6 for c in flag_orders)
    assert text in detail_lines(open_app(OUTSIDE_UK, None, week))


def test_revenue_drivers_stay_money() -> None:
    text = detail_lines(open_app(ALL, None, date(2011, 9, 19)))
    assert "Top products: " in text and "£" in text
    assert " order" not in text.split("Top products: ")[1].split("\n")[0]


# ---------- Flag details open ----------


@pytest.mark.parametrize(
    "week", [date(2011, 9, 19), LAST_WEEK, NO_SALES_WEEK, date(2011, 1, 17)]
)
def test_flag_details_expanded_on_flagged_weeks(week: date) -> None:
    assert scen(ALL, week).selected.flags
    at = open_app(ALL, None, week)
    (box,) = [e for e in at.expander if e.label == "Flag details"]
    assert box.proto.expanded is True


def test_no_flag_details_on_a_calm_week() -> None:
    week = date(2011, 11, 21)
    assert not scen(ALL, week).selected.flags
    at = open_app(ALL, None, week)
    assert not [e for e in at.expander if e.label == "Flag details"]
    assert read_strip(at)["DO THIS"].startswith("Nothing flagged.")


def test_overview_do_this_names_every_flag_in_order() -> None:
    week = date(2011, 1, 17)
    flags = scen(ALL, week).selected.flags
    at = open_app(ALL, None, week)
    assert read_strip(at)["DO THIS"] == (
        f"Read the flag details below: {', '.join(FLAG_LABELS[f.rule] for f in flags)}."
    )


# ---------- Weekly table ----------


def display_values(at: AppTest) -> Any:
    styler = at.dataframe[0].proto.arrow_data.styler
    return pa.ipc.open_stream(styler.display_values).read_all().to_pandas()


def test_table_flags_column_uses_full_labels_joined_by_comma() -> None:
    at = open_app(ALL, None, None, "table")
    at.toggle(key="all_weeks").set_value(True).run()
    s = scen()
    want = [", ".join(FLAG_LABELS[f.rule] for f in w.flags) for w in s.weeks]
    assert display_values(at)["Flags"].tolist() == want
    assert at.dataframe[0].value["Flags"].tolist() == want
    assert "Partial week, Placed and cancelled" in want
    assert not any("+" in cell or cell.startswith("Partial,") for cell in want)


def test_table_avg_order_cells_have_two_decimals() -> None:
    at = open_app(ALL, None, None, "table")
    at.toggle(key="all_weeks").set_value(True).run()
    s = scen()
    shown = display_values(at)["Avg order (net)"].tolist()

    def money2(value: float | None) -> str:
        if value is None:
            return "n/a"
        d = half_up(value, "0.01")
        return f"{'-' if d < 0 else ''}£{spaced(abs(d))}"

    assert shown == [money2(w.net_aov) for w in s.weeks]
    assert "n/a" in shown, "the no-sales week has no average order"
    assert all(re.fullmatch(rf"-?£[\d{NNBSP}]+\.\d\d|n/a", c) for c in shown)
    assert not any("." in c for c in display_values(at)["Net revenue"].tolist())


def test_table_avg_order_rounds_half_up_to_the_penny(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    last = LAST_WEEK - timedelta(days=7)
    values = {
        last: {"net_aov": 538.325},
        last - timedelta(days=7): {"net_aov": 1234.565},
        last - timedelta(days=14): {"net_aov": 0.005},
    }
    patched(monkeypatch, lambda s: with_week(s, values))
    at = open_app(ALL, None, None, "table")
    shown = display_values(at)["Avg order (net)"].tolist()
    assert shown[-2] == "£538.33"
    assert shown[-3] == f"£1{NNBSP}234.57"
    assert shown[-4] == "£0.01"


def test_table_flags_column_empty_for_calm_weeks() -> None:
    at = open_app(ALL, None, None, "table")
    cells = display_values(at)["Flags"].tolist()
    assert cells[0] == "" and cells[-1] == "Partial week, Placed and cancelled"
