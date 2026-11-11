"""PART-B Graphite pass QA: reading strip (DEC-30), plain-words helps (DEC-31), theme tokens (DEC-16)."""

import gc
import html
import json
import re
import tomllib
from collections.abc import Iterator
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest

from kpi import theme
from kpi.core import countries, run_scenario
from kpi.fmt import money
from kpi.models import (
    ALL,
    FIRST_WEEK,
    FLAG_LABELS,
    LAST_WEEK,
    OUTSIDE_UK,
    UK,
    Filters,
)

REPO = Path(__file__).resolve().parents[3]
APP = str(REPO / "app.py")
VIEWS = {
    "overview": "views/overview.py",
    "trends": "views/trends.py",
    "flags": "views/flags.py",
    "table": "views/table.py",
}
DATA_PAGES = list(VIEWS)
DEFAULT_WEEK = date(2011, 11, 28)
NO_SALES_WEEK = date(2010, 12, 27)
CALM = (date(2011, 1, 24), date(2011, 4, 18))
EIGHT = (date(2011, 3, 7), date(2011, 4, 25))
NINE = (date(2011, 3, 7), date(2011, 5, 2))
QUESTIONS = {
    "overview": "How did the selected week go, and does anything need a look?",
    "trends": "Is the selected week part of a trend or a one-off?",
    "flags": "Which weeks need a look, and why?",
    "table": "What are the exact weekly numbers?",
}
PLAIN = {
    "Net revenue": "What the week's sales brought in after cancellations.",
    "Orders": "How many separate orders customers placed.",
    "Avg order (net)": "What an order was worth on average, after cancellations.",
    "Gross revenue": "Sales before cancellations are taken off.",
    "Units": "How many items were sold.",
    "Customers": "How many different customers bought (only lines with a customer id count).",
    "New customers": "Customers buying from the shop for the first time.",
    "Returning customers": "Customers who had bought before.",
    "Cancelled": "The value of items cancelled this week; lower is better.",
}
FORMULA = ("×", "−", "/", "sum(")


@pytest.fixture(autouse=True)
def no_gc() -> Iterator[None]:
    gc.disable()
    yield
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


def strips(at: AppTest) -> list[str]:
    return [str(m.value) for m in at.markdown if "how-to-read" in str(m.value)]


def read_strip(at: AppTest) -> dict[str, str]:
    (raw,) = strips(at)
    found = re.findall(r"<b>([A-Z ]+)</b><span[^>]*>(.*?)</span>", raw)
    assert [k for k, _ in found] == ["THE QUESTION", "RIGHT NOW", "DO THIS"]
    return {k: html.unescape(v) for k, v in found}


def gross(at: AppTest) -> None:
    box: Any = at.get("button_group")[0]
    box.set_value("Gross").run()


def sunday(d: date) -> date:
    return d + timedelta(days=6)


def half_up(value: float, places: str) -> Decimal:
    return Decimal(repr(round(value, 9))).quantize(Decimal(places), ROUND_HALF_UP)


def spaced(d: Decimal) -> str:
    return f"{d:,}".replace(",", "\u202f")


def signed_pct(value: float) -> str:
    d = half_up(value, "0.1")
    return f"{'-' if d < 0 else '+'}{spaced(abs(d))}%"


CARD_FIELDS = (
    ("Net revenue", "net_revenue_wow"),
    ("Orders", "orders_wow"),
    ("Avg order (net)", "net_aov_wow"),
    ("Gross revenue", "revenue_wow"),
    ("Units", "units_wow"),
    ("Customers", "customers_wow"),
    ("New customers", "new_customers_wow"),
    ("Returning customers", "returning_customers_wow"),
    ("Cancelled", "cancelled_value_wow"),
)


def biggest_move_text(w: Any) -> str:
    moves = [
        (label, getattr(w, field))
        for label, field in CARD_FIELDS
        if getattr(w, field) is not None and label != "Cancelled"
    ]
    if not moves:
        return "No comparison with last week."
    shown = [abs(half_up(v, "0.1")) for _, v in moves]
    top = max(shown)
    i = shown.index(top)
    text = f"Biggest move vs last week: {moves[i][0]} {signed_pct(moves[i][1])}"
    rest = shown[:i] + shown[i + 1 :]
    return text + (
        f"; the other cards moved within ±{spaced(max(rest))}%." if rest else "."
    )


def ordinal(n: int) -> str:
    if n % 100 in (11, 12, 13):
        return f"{n}th"
    return f"{n}{({1: 'st', 2: 'nd', 3: 'rd'}).get(n % 10, 'th')}"


def expected_strip(page: str, s: Any, all_weeks: bool = False) -> tuple[str, str]:
    """RIGHT NOW and DO THIS from the DEC-30 wording and the core numbers."""
    if page == "overview":
        w = s.selected
        if w.product_lines == 0:
            return "No sales this week.", "Pick another week in the sidebar."
        if w.flags:
            do = f"Read the flag details below: {', '.join(FLAG_LABELS[f.rule] for f in w.flags)}."
        else:
            do = "Nothing flagged. Scan the top products and countries, then switch weeks in the sidebar."
        return biggest_move_text(w), do
    if page == "trends":
        full = [
            w
            for w in s.weeks
            if w.product_lines > 0 and all(f.rule != "partial_week" for f in w.flags)
        ]
        do = "Switch Net / Gross to see what cancellations took out; amber diamonds are flagged weeks."
        if not full:
            return "No full week with sales in this range.", do
        sel = s.selected
        hi = max(full, key=lambda w: w.net_revenue)
        if sel in full:
            rank = 1 + sum(w.net_revenue > sel.net_revenue for w in full)
            return (
                f"Week {sel.week_start}: net revenue {money(sel.net_revenue)}, the {ordinal(rank)} highest of {len(full)} full week{'s' if len(full) > 1 else ''} in range.",
                do,
            )
        state = (
            "had no sales"
            if sel.product_lines == 0
            else "is partial, so it isn't ranked"
        )
        return (
            f"Week {sel.week_start} {state}; highest full week {hi.week_start} ({money(hi.net_revenue)}).",
            do,
        )
    if page == "flags":
        rules = [f.rule for w in s.weeks for f in w.flags]
        if not rules:
            return (
                "No week flagged in this range.",
                "Widen the date range or pick another country in the sidebar.",
            )
        parts = " · ".join(
            f"{FLAG_LABELS[r]} {rules.count(r)}" for r in dict.fromkeys(rules)
        )
        swing = {"revenue_swing", "orders_swing"} & set(rules)
        plural = "s" if len(s.weeks) > 1 else ""
        return (
            f"{s.totals.flagged_weeks} of {s.totals.weeks} week{plural} flagged: {parts}.",
            "Read each reason; for swings, the drivers show which products and countries moved."
            if swing
            else "Read each reason.",
        )
    n = len(s.weeks)
    every = all_weeks or n <= 8
    shown = s.weeks if every else s.weeks[-8:]
    return (
        f"Showing {'all' if every else 'the last 8'} of {n} week{'s' if n > 1 else ''}, {shown[0].week_start} – {sunday(shown[-1].week_start)}.",
        "Switch on Show changes for week and year comparisons; Download CSV has every week.",
    )


def check_strip(at: AppTest, page: str, s: Any, all_weeks: bool = False) -> None:
    now, do = expected_strip(page, s, all_weeks)
    assert read_strip(at) == {
        "THE QUESTION": QUESTIONS[page],
        "RIGHT NOW": now,
        "DO THIS": do,
    }


# ---------- reading strip: scenarios on every data page ----------

SCENARIOS = {
    "default": (ALL, None, None),
    "uk": (UK, None, None),
    "outside_uk": (OUTSIDE_UK, None, None),
    "sparse_country": ("Brazil", None, None),
    "one_week_mid_year": (ALL, (date(2011, 6, 6), date(2011, 6, 6)), None),
    "partial_only": (ALL, (LAST_WEEK, LAST_WEEK), None),
    "no_sales_week": (ALL, None, NO_SALES_WEEK),
    "no_sales_sparse_week": ("Bahrain", None, date(2011, 6, 6)),
    "calm": (ALL, CALM, None),
    "eight_weeks": (ALL, EIGHT, None),
    "nine_weeks": (ALL, NINE, None),
    "only_no_sales_week": (ALL, (NO_SALES_WEEK, NO_SALES_WEEK), None),
    "flagged_partial_week": (ALL, None, LAST_WEEK),
}


def scenario_of(country: str, span: tuple[date, date] | None, week: date | None) -> Any:
    start, end = span or (FIRST_WEEK, LAST_WEEK)
    if week is None:
        probe = scen(country, end, start, end)
        full = [
            w.week_start
            for w in probe.weeks
            if all(f.rule != "partial_week" for f in w.flags)
        ]
        week = (full or [w.week_start for w in probe.weeks])[-1]
    return scen(country, week, start, end)


@pytest.mark.parametrize("page", DATA_PAGES)
@pytest.mark.parametrize("name", list(SCENARIOS))
def test_strip_matches_dec30_texts(name: str, page: str) -> None:
    country, span, week = SCENARIOS[name]
    at = open_app(country, span, week, page)
    check_strip(at, page, scenario_of(country, span, week))


@pytest.mark.parametrize("page", DATA_PAGES)
@pytest.mark.parametrize("preset", ["Full year", "Q4 2011", "UK only", "Outside UK"])
def test_strip_for_each_preset(preset: str, page: str) -> None:
    at = AppTest.from_file(APP, default_timeout=120).run()
    at.selectbox(key="preset").select(preset).run()
    if page != "overview":
        at.switch_page(VIEWS[page]).run()
    assert not at.exception
    country = {"UK only": UK, "Outside UK": OUTSIDE_UK}.get(preset, ALL)
    span = (date(2011, 10, 3), LAST_WEEK) if preset == "Q4 2011" else None
    check_strip(at, page, scenario_of(country, span, None))


def test_smallest_country_really_is_brazil() -> None:
    cs = [c for c in countries() if c not in (ALL, UK, OUTSIDE_UK)]
    assert min(cs, key=lambda c: scen(c).totals.orders) == "Brazil"


def test_strip_changes_with_the_selected_week() -> None:
    at = open_app()
    first = read_strip(at)["RIGHT NOW"]
    at.selectbox(key="week").select(date(2011, 9, 19)).run()
    second = read_strip(at)["RIGHT NOW"]
    assert first != second
    assert second == biggest_move_text(scen(ALL, date(2011, 9, 19)).selected)


@pytest.mark.parametrize("page", DATA_PAGES)
def test_exactly_one_strip_per_data_page(page: str) -> None:
    at = open_app(page=page)
    assert len(strips(at)) == 1
    raw = strips(at)[0]
    for label in ("THE QUESTION", "RIGHT NOW", "DO THIS"):
        assert raw.count(label) == 1
    assert raw.count("how-to-read") == 1


@pytest.mark.parametrize("page", DATA_PAGES)
def test_strip_stays_single_after_rerun_and_page_hopping(page: str) -> None:
    at = open_app(page=page)
    at.selectbox(key="country").select("Germany").run()
    at.switch_page("views/methodology.py").run()
    at.switch_page(VIEWS[page]).run()
    assert len(strips(at)) == 1
    check_strip(at, page, scenario_of("Germany", None, None))


def test_methodology_has_no_strip() -> None:
    at = open_app()
    at.switch_page("views/methodology.py").run()
    assert not at.exception
    assert not strips(at)
    assert not [m for m in at.markdown if "THE QUESTION" in str(m.value)]


def test_strip_is_html_escaped() -> None:
    for page in DATA_PAGES:
        raw = strips(open_app("Bahrain", page=page))[0]
        body = re.sub(r"</?(div|b|span)[^>]*>", "", raw)
        assert "<" not in body and ">" not in body


def test_overview_headline_is_not_shown_anywhere() -> None:
    at = open_app()
    headline = scen().headline
    assert not [m for m in at.markdown if headline in str(m.value)]
    assert not [e for e in at.expander if headline in str(e.label)]


def test_overview_no_sales_week_do_this_exact() -> None:
    at = open_app(week=NO_SALES_WEEK)
    assert read_strip(at)["DO THIS"] == "Pick another week in the sidebar."
    assert read_strip(at)["RIGHT NOW"] == "No sales this week."


def test_overview_do_this_lists_all_flags_in_order() -> None:
    at = open_app(week=date(2011, 12, 5))
    assert (
        read_strip(at)["DO THIS"]
        == "Read the flag details below: Partial week, Placed and cancelled."
    )


def test_flags_page_calm_range() -> None:
    at = open_app(span=CALM, page="flags")
    assert read_strip(at)["RIGHT NOW"] == "No week flagged in this range."
    assert (
        read_strip(at)["DO THIS"]
        == "Widen the date range or pick another country in the sidebar."
    )
    assert [str(s.value) for s in at.success] == [
        "No flagged weeks in the selected range."
    ]


def test_flags_page_single_flag_type_has_no_trailing_separator() -> None:
    at = open_app(week=NO_SALES_WEEK, span=(NO_SALES_WEEK, NO_SALES_WEEK), page="flags")
    assert read_strip(at)["RIGHT NOW"] == "1 of 1 week flagged: No sales 1."


def test_trends_no_full_week_partial_only() -> None:
    at = open_app(span=(LAST_WEEK, LAST_WEEK), page="trends")
    assert read_strip(at)["RIGHT NOW"] == "No full week with sales in this range."
    assert not at.exception


def test_trends_no_full_week_no_sales_only() -> None:
    at = open_app(span=(NO_SALES_WEEK, NO_SALES_WEEK), page="trends")
    assert read_strip(at)["RIGHT NOW"] == "No full week with sales in this range."


def test_trends_single_full_week_is_ranked_first_of_one() -> None:
    wk = date(2011, 6, 6)
    at = open_app(span=(wk, wk), page="trends")
    net = money(scen(ALL, wk, wk, wk).selected.net_revenue)
    assert read_strip(at)["RIGHT NOW"] == (
        f"Week {wk}: net revenue {net}, the 1st highest of 1 full week in range."
    )


def test_trends_default_is_acceptance_text() -> None:
    at = open_app(page="trends")
    assert read_strip(at)["RIGHT NOW"] == (
        "Week 2011-11-28: net revenue £306 112, the 4th highest of 51 full weeks in range."
    )


def test_trends_gross_toggle_does_not_change_strip() -> None:
    at = open_app(page="trends")
    before = read_strip(at)
    gross(at)
    assert read_strip(at) == before


@pytest.mark.parametrize(
    ("span", "text"),
    [
        ((LAST_WEEK, LAST_WEEK), "Showing all of 1 week, 2011-12-05 – 2011-12-11."),
        (EIGHT, "Showing all of 8 weeks, 2011-03-07 – 2011-05-01."),
        (NINE, "Showing the last 8 of 9 weeks, 2011-03-14 – 2011-05-08."),
    ],
)
def test_table_week_count_boundaries(span: tuple[date, date], text: str) -> None:
    at = open_app(span=span, page="table")
    assert read_strip(at)["RIGHT NOW"] == text
    assert len(at.dataframe[0].value) == min(8, len(scenario_of(ALL, span, None).weeks))


def test_table_default_is_acceptance_text() -> None:
    at = open_app(page="table")
    assert (
        read_strip(at)["RIGHT NOW"]
        == "Showing the last 8 of 53 weeks, 2011-10-17 – 2011-12-11."
    )


def test_table_all_weeks_toggle_updates_strip_and_rows() -> None:
    at = open_app(page="table")
    at.toggle(key="all_weeks").set_value(True).run()
    assert (
        read_strip(at)["RIGHT NOW"]
        == "Showing all of 53 weeks, 2010-12-06 – 2011-12-11."
    )
    assert len(at.dataframe[0].value) == 53
    at.toggle(key="all_weeks").set_value(False).run()
    assert (
        read_strip(at)["RIGHT NOW"]
        == "Showing the last 8 of 53 weeks, 2011-10-17 – 2011-12-11."
    )
    assert len(at.dataframe[0].value) == 8


def test_table_strip_matches_rows_after_page_switch_and_back() -> None:
    at = open_app(page="table")
    at.toggle(key="all_weeks").set_value(True).run()
    at.switch_page(VIEWS["flags"]).run()
    at.switch_page(VIEWS["table"]).run()
    assert not at.exception
    assert len(strips(at)) == 1
    on = bool(at.toggle(key="all_weeks").value)
    check_strip(at, "table", scen(), all_weeks=on)
    assert len(at.dataframe[0].value) == (53 if on else 8)


def test_table_all_weeks_with_narrow_range_after_change() -> None:
    at = open_app(page="table")
    at.toggle(key="all_weeks").set_value(True).run()
    at.date_input(key="dates").set_value((EIGHT[0], sunday(NINE[1]))).run()
    check_strip(at, "table", scenario_of(ALL, NINE, None), all_weeks=True)
    assert read_strip(at)["RIGHT NOW"].startswith("Showing all of 9 weeks")


def test_table_do_this_is_static() -> None:
    do = "Switch on Show changes for week and year comparisons; Download CSV has every week."
    at = open_app(page="table")
    assert read_strip(at)["DO THIS"] == do
    at.toggle(key="changes").set_value(True).run()
    assert read_strip(at)["DO THIS"] == do


def test_strip_after_invalid_dates_is_absent_not_stale() -> None:
    at = open_app()
    at.date_input(key="dates").set_value((date(2011, 3, 7),)).run()
    assert not at.exception
    assert not strips(at)


# ---------- plain words in helps ----------


def first_sentence(text: str) -> str:
    return text.split(". ")[0].split(".\n")[0]


@pytest.mark.parametrize("label", list(PLAIN))
def test_overview_card_help_is_plain_blank_line_sources(label: str) -> None:
    at = open_app()
    m = next(m for m in at.metric if m.label == label)
    plain, sep, rest = m.help.partition("\n\n")
    assert sep == "\n\n"
    assert plain == PLAIN[label]
    assert rest
    assert not any(c in plain for c in FORMULA)
    assert m.help.startswith(PLAIN[label])


def test_overview_has_exactly_nine_card_helps() -> None:
    at = open_app()
    assert {m.label for m in at.metric} == set(PLAIN)
    assert all(m.help for m in at.metric)


def test_card_help_sources_come_from_core() -> None:
    at = open_app()
    s = scen()
    keys = {
        "Net revenue": "net_revenue",
        "Orders": "orders",
        "Avg order (net)": "net_aov",
        "Gross revenue": "revenue",
        "Units": "units",
        "Customers": "customers",
        "New customers": "new_customers",
        "Returning customers": "returning_customers",
        "Cancelled": "cancelled_value",
    }
    for m in at.metric:
        assert m.help == f"{PLAIN[m.label]}\n\n{s.sources[keys[m.label]]}"


@pytest.mark.parametrize("week", [FIRST_WEEK, NO_SALES_WEEK, LAST_WEEK])
def test_card_help_unchanged_on_edge_weeks(week: date) -> None:
    at = open_app(week=week)
    for m in at.metric:
        assert m.help.startswith(f"{PLAIN[m.label]}\n\n")


def test_yoy_help_opens_with_plain_sentence() -> None:
    at = open_app()
    caps = [c for c in at.main.caption if "vs same week last year" in str(c.value)]
    assert len(caps) == 3
    for c in caps:
        sentence = first_sentence(c.proto.help)
        assert sentence == "How this week compares with the same week a year ago"
        assert not any(ch in sentence for ch in FORMULA)


def test_yoy_dash_help_opens_with_plain_sentence() -> None:
    at = open_app(week=LAST_WEEK)
    caps = [c for c in at.main.caption if "vs same week last year" in str(c.value)]
    assert len(caps) == 3
    for c in caps:
        assert c.value.startswith("—")
        assert c.proto.help.startswith(
            "There is no fair comparison with last year for this week"
        )


def test_trends_switch_help_opens_with_plain_sentence() -> None:
    at = open_app(page="trends")
    help_ = at.get("button_group")[0].proto.help
    sentence = first_sentence(help_)
    assert sentence == "Choose which revenue to plot: after or before cancellations"
    assert not any(c in sentence for c in FORMULA)


def test_flags_column_help_opens_with_plain_sentence() -> None:
    at = open_app(page="table")
    cols = json.loads(at.dataframe[0].proto.columns)
    sentence = first_sentence(cols["Flags"]["help"])
    assert (
        sentence
        == "What was flagged that week; at narrow widths the text may be cut, and the full reasons are on Flagged weeks."
    )
    assert not any(c in sentence for c in FORMULA)


def test_share_bar_help_opens_with_plain_sentence() -> None:
    at = open_app()
    cols = json.loads(at.dataframe[0].proto.columns)
    sentence = first_sentence(cols["Share of week"]["help"])
    assert sentence == "How much of the week's sales each one brought in"
    assert not any(c in sentence for c in FORMULA)


def test_csv_button_help_opens_with_plain_sentence() -> None:
    at = open_app(page="table")
    (btn,) = at.get("download_button")
    sentence = first_sentence(btn.proto.help)
    assert sentence == "Download every week in the range for a spreadsheet"
    assert not any(c in sentence for c in FORMULA)


@pytest.mark.parametrize("page", DATA_PAGES)
def test_every_help_on_page_opens_plain(page: str) -> None:
    at = open_app(page=page)
    helps = [m.help for m in at.metric if m.help]
    helps += [c.proto.help for c in at.main.caption if c.proto.help]
    helps += [e.proto.help for e in at.get("button_group") if e.proto.help]
    helps += [e.proto.help for e in at.get("download_button") if e.proto.help]
    for df in at.dataframe:
        helps += [
            c["help"] for c in json.loads(df.proto.columns).values() if "help" in c
        ]
    for h in helps:
        sentence = first_sentence(h)
        assert sentence[:1].isupper(), h
        assert not any(c in sentence for c in FORMULA), h


# ---------- theme ----------


def luminance(h: str) -> float:
    rgb = [int(h[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = (c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


@pytest.mark.parametrize("name", ["TEXT", "MUTED", "GOOD", "BAD", "SLATE", "PRIMARY"])
def test_text_tokens_contrast_on_bg_and_surfaces(name: str) -> None:
    colour = getattr(theme, name)
    assert contrast(colour, theme.BG) >= 4.5
    assert contrast(colour, theme.SURFACE) >= 4.5


@pytest.mark.parametrize("name", ["TEXT", "MUTED", "GOOD", "BAD"])
def test_text_tokens_readable_on_hover_surface(name: str) -> None:
    assert contrast(getattr(theme, name), theme.SURFACE_2) >= 4.5


@pytest.mark.parametrize("name", ["BLUE", "NEW", "RETURNING", "AMBER", "GREEN", "RED"])
def test_data_colours_contrast(name: str) -> None:
    assert contrast(getattr(theme, name), theme.BG) >= 3.0


def test_new_and_returning_are_distinct_and_meaningful() -> None:
    assert theme.NEW == theme.BLUE
    assert theme.RETURNING == theme.SLATE
    assert theme.NEW.lower() != theme.RETURNING.lower()
    assert contrast(theme.NEW, theme.RETURNING) >= 1.3
    assert theme.GOOD == theme.GREEN and theme.BAD == theme.RED
    assert theme.PRIMARY != theme.BLUE
    assert theme.SERIES == [theme.BLUE, theme.RETURNING]


def test_tokens_are_valid_hex() -> None:
    for name in (
        "BG", "SURFACE", "SURFACE_2", "BORDER", "TEXT", "MUTED", "PRIMARY",
        "BLUE", "GREEN", "AMBER", "RED", "SLATE",
    ):  # fmt: skip
        assert re.fullmatch(r"#[0-9A-Fa-f]{6}", getattr(theme, name)), name


def test_template_registered_and_backgrounds() -> None:
    import plotly.io as pio

    assert pio.templates.default == "graphite_dark"
    assert pio.templates["graphite_dark"] == theme.TEMPLATE
    assert theme.TEMPLATE.layout.paper_bgcolor == theme.BG
    assert theme.TEMPLATE.layout.plot_bgcolor == theme.BG
    assert theme.TEMPLATE.layout.font.family == theme.FONT
    assert list(theme.TEMPLATE.layout.colorway) == [theme.BLUE, theme.RETURNING]


def test_css_vars_all_in_injected_style() -> None:
    at = open_app()
    (blob,) = at.get("html")
    body = blob.proto.body
    for name, value in theme.CSS_VARS.items():
        assert f"--{name}: {value};" in body, name
    assert "var(--font)" in body
    assert "how-to-read" in body


def test_css_uses_only_declared_variables() -> None:
    css = (REPO / "assets" / "style.css").read_text()
    used = set(re.findall(r"var\(--([a-z0-9-]+)\)", css))
    assert used <= set(theme.CSS_VARS), used - set(theme.CSS_VARS)


def test_config_toml_mirrors_tokens_and_font() -> None:
    cfg = tomllib.loads((REPO / ".streamlit" / "config.toml").read_text())["theme"]
    assert cfg["base"] == "dark"
    assert cfg["backgroundColor"] == theme.BG
    assert cfg["secondaryBackgroundColor"] == theme.SURFACE
    assert cfg["primaryColor"] == theme.PRIMARY
    assert cfg["textColor"] == theme.TEXT
    assert cfg["greenColor"] == theme.GOOD
    assert cfg["redColor"] == theme.BAD
    assert cfg["font"] == theme.FONT
    assert "Inter" not in cfg["font"]


# ---------- review and UX fixes (7dfe0de) ----------

CAPTION = "A flag asks for a look; it is not an error in the data."
NOTE = "The saved weekly summary covers all countries, so it is hidden while a country filter is on."


def css_rules(at: AppTest) -> dict[tuple[int, int], dict[str, str]]:
    """Styler css of the first dataframe as {(row, col): {property: value}}."""
    styles = at.dataframe[0].proto.arrow_data.styler.styles
    out: dict[tuple[int, int], dict[str, str]] = {}
    for sel, body in re.findall(r"([^{}]+)\{([^}]*)\}", styles):
        props = dict(p.strip().split(": ", 1) for p in body.split(";") if ": " in p)
        for r, c in re.findall(r"_row(\d+)_col(\d+)", sel):
            out.setdefault((int(r), int(c)), {}).update(props)
    return out


@pytest.mark.parametrize("name", ["default", "calm", "sparse_country"])
def test_flags_caption_and_help(name: str) -> None:
    country, span, week = SCENARIOS[name]
    at = open_app(country, span, week, "flags")
    caps = [c for c in at.main.caption if str(c.value) == CAPTION]
    assert len(caps) == 1
    help_ = caps[0].proto.help
    assert help_.startswith("Why weeks get flagged and how to read them.")
    assert not any(c in first_sentence(help_) for c in FORMULA)


@pytest.mark.parametrize("page", ["overview", "trends", "table"])
def test_flags_caption_only_on_flags_page(page: str) -> None:
    at = open_app(page=page)
    assert CAPTION not in [str(c.value) for c in at.main.caption]


@pytest.mark.parametrize("country", [UK, OUTSIDE_UK, "Germany", "Brazil"])
def test_country_note_is_caption_not_info(country: str) -> None:
    at = open_app(country, week=date(2011, 9, 19))
    assert not at.info
    assert [str(c.value) for c in at.main.caption].count(NOTE) == 1


def test_no_country_note_for_all_countries() -> None:
    at = open_app(week=date(2011, 9, 19))
    assert not at.info
    assert NOTE not in [str(c.value) for c in at.main.caption]


@pytest.mark.parametrize(
    ("country", "titles"),
    [
        (ALL, ["Top 5 products", "Top 5 countries"]),
        (OUTSIDE_UK, ["Top 5 products", "Top 5 countries"]),
        (UK, ["Top 5 products"]),
        ("Germany", ["Top 5 products"]),
        ("Brazil", ["Top 5 products"]),
    ],
)
def test_top5_countries_only_for_all_and_outside_uk(
    country: str, titles: list[str]
) -> None:
    at = open_app(country, week=date(2011, 9, 19))
    assert [str(s.value) for s in at.subheader] == titles
    sold = scen(country, date(2011, 9, 19)).selected.product_lines > 0
    assert len(at.dataframe) == (len(titles) if sold else 0)


def test_top5_on_no_sales_week_single_country() -> None:
    at = open_app("Bahrain", week=date(2011, 6, 6))
    assert not at.exception
    assert [str(s.value) for s in at.subheader] == ["Top 5 products"]
    assert "No sales this week." in [str(c.value) for c in at.main.caption]


def test_table_selected_week_row_is_tinted() -> None:
    wk = date(2011, 11, 28)
    at = open_app(week=wk, page="table")
    rows = list(at.dataframe[0].value["Week"])
    row = rows.index(str(wk))
    rules = css_rules(at)
    ncols = len(at.dataframe[0].value.columns)
    for c in range(ncols):
        assert rules[(row, c)]["background-color"] == theme.SURFACE_2
    assert rules[(row, 0)]["color"] == theme.TEXT
    for r in range(len(rows)):
        assert rules[(r, 0)]["color"] == theme.TEXT
        if r != row:
            assert "background-color" not in rules[(r, 0)]
            assert (r, 1) not in rules


def test_table_selected_week_outside_slice_has_no_tint() -> None:
    at = open_app(week=date(2011, 3, 7), page="table")
    assert "2011-03-07" not in list(at.dataframe[0].value["Week"])
    assert not [r for r in css_rules(at).values() if "background-color" in r]
    at.toggle(key="all_weeks").set_value(True).run()
    rows = list(at.dataframe[0].value["Week"])
    tinted = {k[0] for k, v in css_rules(at).items() if "background-color" in v}
    assert tinted == {rows.index("2011-03-07")}


def test_table_tint_survives_show_changes() -> None:
    wk = date(2011, 11, 28)
    at = open_app(week=wk, page="table")
    at.toggle(key="changes").set_value(True).run()
    rows = list(at.dataframe[0].value["Week"])
    rules = css_rules(at)
    row = rows.index(str(wk))
    assert all(
        rules[(row, c)].get("background-color") == theme.SURFACE_2
        for c in range(len(at.dataframe[0].value.columns))
    )
    colours = {v["color"] for v in rules.values() if "color" in v}
    assert colours <= {theme.TEXT, theme.GOOD, theme.BAD}
    assert {theme.GOOD, theme.BAD} & colours


@pytest.mark.parametrize(
    "name",
    ["default", "eight_weeks", "nine_weeks", "calm", "partial_only", "no_sales_week"],
)
@pytest.mark.parametrize("all_weeks", [False, True])
def test_table_strip_and_rows_share_one_slice(name: str, all_weeks: bool) -> None:
    country, span, week = SCENARIOS[name]
    at = open_app(country, span, week, "table")
    if all_weeks:
        at.toggle(key="all_weeks").set_value(True).run()
    rows = list(at.dataframe[0].value["Week"])
    text = read_strip(at)["RIGHT NOW"]
    assert text.endswith(f"{rows[0]} – {sunday(date.fromisoformat(rows[-1]))}.")
    n = len(scenario_of(country, span, week).weeks)
    assert f"of {n} week{'s' if n > 1 else ''}, " in text
    assert (len(rows) == n) == ("all of" in text)


def revenue_layout_charts(at: AppTest) -> list[dict[str, Any]]:
    return [json.loads(c.proto.spec) for c in at.get("plotly_chart")]


@pytest.mark.parametrize("measure", ["Net", "Gross"])
@pytest.mark.parametrize(
    "name",
    ["default", "sparse_country", "one_week_mid_year", "partial_only", "no_sales_week"],
)
def test_trends_selected_week_marker_on_all_four_charts(
    name: str, measure: str
) -> None:
    country, span, week = SCENARIOS[name]
    at = open_app(country, span, week, "trends")
    if measure == "Gross":
        gross(at)
    sel = scenario_of(country, span, week).filters.week
    charts = revenue_layout_charts(at)
    assert len(charts) == 4
    for ch in charts:
        notes = [a for a in ch["layout"]["annotations"] if a["text"] == "Selected week"]
        assert len(notes) == 1
        assert notes[0]["yref"] == "paper"
        assert str(notes[0]["x"])[:10] == str(sel)
        (line,) = [s for s in ch["layout"]["shapes"] if s["type"] == "line"]
        assert str(line["x0"])[:10] == str(sel)
        assert line["line"]["color"] == theme.TEXT
        assert line["opacity"] == 0.5
        assert not line["line"].get("dash")


def test_trends_help_says_solid_vertical_line() -> None:
    at = open_app(page="trends")
    help_ = at.get("button_group")[0].proto.help
    assert "the solid vertical line marks the selected week" in help_
    assert "dotted vertical" not in help_


def test_trends_selected_week_annotation_is_not_a_partial_note() -> None:
    at = open_app(week=LAST_WEEK, page="trends")
    texts = [a["text"] for a in revenue_layout_charts(at)[0]["layout"]["annotations"]]
    assert texts.count("Selected week") == 1
    assert len([t for t in texts if t.startswith("Partial")]) == 1


def test_csv_help_opens_with_download_sentence() -> None:
    at = open_app(page="table")
    (btn,) = at.get("download_button")
    assert btn.proto.help.startswith(
        "Download every week in the range for a spreadsheet."
    )


def test_css_vars_exact_keys() -> None:
    assert set(theme.CSS_VARS) == {
        "surface", "surface-2", "border", "text", "muted", "font", "radius", "card-fill",
    }  # fmt: skip


def test_small_card_breakpoint() -> None:
    css = (REPO / "assets" / "style.css").read_text()
    assert "@media (max-width: 1600px)" in css
    assert "1366px" not in css
