"""Round-2 PART-B QA: range line, status pill, sparklines, Trends gaps, Flagged weeks groups, Weekly table, top lists."""

import gc
import json
import math
import re
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path
from string import capwords
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest

from kpi.core import run_scenario
from kpi.fmt import count, money, pct
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
DEFAULT_WEEK = date(2011, 11, 28)
END = LAST_WEEK + timedelta(days=6)
VIEWS = {
    "overview": "views/overview.py",
    "trends": "views/trends.py",
    "flags": "views/flags.py",
    "table": "views/table.py",
}
COLOUR = {
    "no_data": "gray",
    "partial_week": "gray",
    "revenue_swing": "blue",
    "orders_swing": "blue",
    "large_cancellations": "orange",
    "top_line": "orange",
}
SHORT = (date(2011, 3, 7), date(2011, 4, 25))
CALM = (date(2011, 1, 24), date(2011, 4, 18))


@pytest.fixture(autouse=True)
def no_gc() -> Iterator[None]:
    """The AppTest media storage is only reachable until a gc pass; keep gc off while a test runs."""
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


def range_line(s: Any) -> str:
    f, t = s.filters, s.totals
    return f"Range {f.start} – {f.end + timedelta(days=6)} · revenue {money(t.revenue)} · orders {count(t.orders)} · flagged weeks {count(t.flagged_weeks)}"


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


def chosen(at: AppTest) -> date:
    value = at.selectbox(key="week").value
    assert isinstance(value, date)
    return value


def captions(at: AppTest) -> list[str]:
    return [str(c.value) for c in at.caption]


def markdowns(at: AppTest) -> list[str]:
    return [str(m.value) for m in at.markdown]


def metric(at: AppTest, label: str) -> Any:
    return next(m for m in at.metric if m.label == label)


def charts(at: AppTest) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [
        json.loads(c.proto.spec) for c in at.get("plotly_chart")
    ]
    return out


def y_at(trace: dict[str, Any], week: date) -> Any:
    xs = [str(x)[:10] for x in trace["x"]]
    return trace["y"][xs.index(str(week))]


CASES = [
    (ALL, None),
    (UK, None),
    (OUTSIDE_UK, None),
    ("Bahrain", None),
    (ALL, SHORT),
    (ALL, (LAST_WEEK, LAST_WEEK)),
    (ALL, (date(2011, 6, 6), date(2011, 6, 6))),
    (UK, (date(2011, 10, 3), LAST_WEEK)),
]


# ---------- range line + data as of ----------


@pytest.mark.parametrize("page", list(VIEWS))
@pytest.mark.parametrize(("country", "span"), CASES)
def test_range_line_and_data_as_of(
    page: str, country: str, span: tuple[date, date] | None
) -> None:
    start, end = span or (FIRST_WEEK, LAST_WEEK)
    at = open_app(country, span, None, page)
    s = scen(country, chosen(at), start, end)
    caps = captions(at)
    assert range_line(s) in caps
    assert any("Data as of 2011-12-09" in c for c in caps)
    assert not [m for m in at.metric if m.label == "Range revenue"]
    assert sum(c.startswith("Range 20") for c in caps) == 1


def test_calm_range_has_zero_flagged_weeks_in_range_line() -> None:
    at = open_app(ALL, CALM, None, "flags")
    s = scen(ALL, chosen(at), *CALM)
    assert s.totals.flagged_weeks == 0
    assert "flagged weeks 0" in range_line(s)
    assert range_line(s) in captions(at)


# ---------- status pill + flag details ----------


@pytest.mark.parametrize(
    ("country", "week"),
    [
        (ALL, w)
        for w in [
            date(2010, 12, 20),
            date(2010, 12, 27),
            date(2011, 1, 17),
            date(2011, 4, 25),
            date(2011, 5, 9),
            date(2011, 9, 19),
            date(2011, 12, 5),
            date(2011, 2, 7),
        ]
    ]
    + [
        (UK, date(2011, 12, 5)),
        ("Bahrain", date(2011, 6, 6)),
        (OUTSIDE_UK, date(2011, 7, 4)),
    ],
)
def test_status_pill_and_flag_details(country: str, week: date) -> None:
    at = open_app(country, None, week)
    flags = scen(country, week).selected.flags
    n = len(flags)
    vals = markdowns(at)
    pills = [v for v in vals if "-badge[▲" in v or "● All clear" in v]
    assert len(pills) == 1
    details = [e for e in at.expander if e.label == "Flag details"]
    if n == 0:
        assert pills == [":green-badge[● All clear]"]
        assert not details
    else:
        word = "flag" if n == 1 else "flags"
        assert pills == [f":orange-badge[▲ {n} {word}]"]
        assert len(details) == 1
        text = "\n".join(str(m.value) for m in details[0].markdown)
        for f in flags:
            assert f"**{FLAG_LABELS[f.rule]}** · {f.reason}" in text
        assert text.count("**") == 2 * n + sum(f.reason.count("**") for f in flags)


def test_pill_grammar_covers_singular_plural_and_clear() -> None:
    counts = {len(w.flags) for w in scen().weeks}
    assert {0, 1, 2, 3, 4} <= counts


# ---------- sparklines ----------


def window(s: Any, key: str) -> list[float]:
    shown = [w for w in s.weeks if w.week_start <= s.selected.week_start][-12:]
    return [v for w in shown if (v := getattr(w, key)) is not None]


BIG = {"Revenue": "revenue", "Orders": "orders", "Average order value": "aov"}
SMALL = [
    "Units",
    "Customers",
    "New customers",
    "Returning customers",
    "Cancellation rate",
    "Cancelled value",
    "Revenue after cancellations",
]


@pytest.mark.parametrize(
    ("country", "span", "week", "n"),
    [
        (ALL, SHORT, None, 8),
        (ALL, SHORT, date(2011, 3, 14), 2),
        (ALL, SHORT, date(2011, 3, 7), 1),
        (ALL, None, date(2010, 12, 6), 1),
        (ALL, None, date(2011, 1, 3), 5),
        (ALL, None, date(2011, 2, 21), 12),
        (ALL, None, date(2011, 2, 14), 11),
        (ALL, None, date(2011, 6, 6), 12),
        ("Bahrain", None, date(2011, 6, 6), 12),
        ("Bahrain", None, date(2011, 1, 3), 5),
        (UK, (LAST_WEEK, LAST_WEEK), None, 1),
    ],
)
def test_sparkline_window(
    country: str, span: tuple[date, date] | None, week: date | None, n: int
) -> None:
    at = open_app(country, span, week)
    start, end = span or (FIRST_WEEK, LAST_WEEK)
    s = scen(country, chosen(at), start, end)
    shown = [w for w in s.weeks if w.week_start <= s.selected.week_start][-12:]
    assert len(shown) == n
    for label, key in BIG.items():
        assert list(metric(at, label).proto.chart_data) == pytest.approx(window(s, key))
    for label in SMALL:
        assert list(metric(at, label).proto.chart_data) == []


def test_sparkline_skips_none_aov_for_sparse_country() -> None:
    at = open_app("Bahrain", None, date(2011, 6, 6))
    s = scen("Bahrain", date(2011, 6, 6))
    revenue = list(metric(at, "Revenue").proto.chart_data)
    aov = list(metric(at, "Average order value").proto.chart_data)
    assert len(revenue) == 12
    assert len(aov) == len(
        [w for w in s.weeks if w.week_start <= date(2011, 6, 6)][-12:]
    ) - sum(
        1
        for w in s.weeks
        if date(2011, 3, 21) <= w.week_start <= date(2011, 6, 6) and w.aov is None
    )
    assert len(aov) < 12


# ---------- Trends ----------


def test_sparse_country_gaps_in_all_four_charts() -> None:
    at = open_app("Bahrain", None, None, "trends")
    s = scen("Bahrain")
    empty = [w.week_start for w in s.weeks if w.product_lines == 0]
    assert len(empty) > 40
    cs = charts(at)
    assert len(cs) == 4
    for chart in cs:
        for tr in chart["data"]:
            for wk in empty:
                assert y_at(tr, wk) is None, (
                    chart["layout"]["title"],
                    tr.get("name"),
                    wk,
                )
            for w in s.weeks:
                if w.product_lines > 0 and w.week_start != LAST_WEEK:
                    assert (
                        y_at(tr, w.week_start) is not None
                        or tr.get("name") == "Cancellation rate"
                    )


def test_partial_trace_starts_at_partial_week_when_previous_week_is_empty() -> None:
    at = open_app("Austria", None, None, "trends")
    s = scen("Austria")
    assert s.weeks[-2].product_lines == 0 and s.weeks[-1].product_lines > 0
    rev = next(
        c for c in charts(at) if any(t.get("name") == "Partial week" for t in c["data"])
    )
    tr = next(t for t in rev["data"] if t["name"] == "Partial week")
    drawn = [
        str(x)[:10] for x, y in zip(tr["x"], tr["y"], strict=True) if y is not None
    ]
    assert drawn == [str(LAST_WEEK)]


def test_count_axes_have_no_si_suffix() -> None:
    at = open_app("Austria", None, None, "trends")
    for chart in charts(at):
        axis = chart["layout"].get("yaxis", {})
        if axis.get("tickprefix") != "£":
            assert axis.get("tickformat") is None, chart["layout"]["title"]


def test_uk_only_partial_trace_and_annotation() -> None:
    at = open_app(UK, None, None, "trends")
    s = scen(UK, DEFAULT_WEEK)
    p = s.weeks[-1]
    rev = next(
        c for c in charts(at) if any(t.get("name") == "Partial week" for t in c["data"])
    )
    assert y_at(rev["data"][0], LAST_WEEK) is None
    tr = next(t for t in rev["data"] if t["name"] == "Partial week")
    drawn = [(str(x)[:10], y) for x, y in zip(tr["x"], tr["y"], strict=True) if y]
    assert [d[0] for d in drawn] == [
        str(LAST_WEEK - timedelta(days=7)),
        str(LAST_WEEK),
    ]
    assert tr["marker"]["symbol"] == "circle-open"
    assert drawn[0][1] == pytest.approx(s.weeks[-2].revenue)
    assert drawn[-1][1] == pytest.approx(p.revenue)
    assert tr["line"]["dash"] == "dot"
    texts = [a["text"] for a in rev["layout"]["annotations"]]
    expected = f"Partial week, {money(p.cancelled_value)} cancelled ({pct(100 * p.cancelled_value / p.revenue)})"
    assert expected in texts
    assert len([t for t in texts if t.startswith("Partial week")]) == 1


@pytest.mark.parametrize(
    ("country", "span"),
    [(ALL, SHORT), (UK, SHORT), (ALL, (date(2011, 11, 7), date(2011, 11, 28)))],
)
def test_no_partial_trace_when_range_ends_before_partial_week(
    country: str, span: tuple[date, date]
) -> None:
    at = open_app(country, span, None, "trends")
    for chart in charts(at):
        assert "Partial week" not in [t.get("name") for t in chart["data"]]
        assert not [
            a
            for a in chart["layout"].get("annotations", [])
            if "Partial" in str(a.get("text"))
        ]
        assert (
            len(chart["data"][0]["x"])
            == scen(country, start=span[0], end=span[1], week=span[1]).totals.weeks
        )


def test_range_that_is_only_the_partial_week() -> None:
    at = open_app(ALL, (LAST_WEEK, LAST_WEEK), None, "trends")
    s = scen(ALL, LAST_WEEK, LAST_WEEK, LAST_WEEK)
    cs = charts(at)
    assert len(cs) == 4
    rev = next(c for c in cs if any(t.get("name") == "Partial week" for t in c["data"]))
    assert rev["data"][0]["y"] == [None]
    tr = next(t for t in rev["data"] if t["name"] == "Partial week")
    assert [str(x)[:10] for x in tr["x"]] == [str(LAST_WEEK)]
    assert tr["y"] == [pytest.approx(s.selected.revenue)]
    assert tr["marker"]["symbol"] == "circle-open"


def test_range_starting_on_no_data_week_has_gap_first() -> None:
    at = open_app(ALL, (date(2010, 12, 27), date(2011, 1, 10)), None, "trends")
    for chart in charts(at):
        assert y_at(chart["data"][0], date(2010, 12, 27)) is None


# ---------- Flagged weeks ----------


@pytest.mark.parametrize(
    ("country", "span"),
    [
        (ALL, None),
        (UK, None),
        (OUTSIDE_UK, SHORT),
        ("Bahrain", SHORT),
        (ALL, (LAST_WEEK, LAST_WEEK)),
    ],
)
def test_flag_groups_colours_order_and_lines(
    country: str, span: tuple[date, date] | None
) -> None:
    start, end = span or (FIRST_WEEK, LAST_WEEK)
    at = open_app(country, span, None, "flags")
    s = scen(country, chosen(at), start, end)
    flagged = [w for w in s.weeks if w.flags]
    vals = markdowns(at)
    heads = [v for v in vals if v.startswith("**20")]
    assert heads == [
        f"**{w.week_start} – {w.week_start + timedelta(days=6)}** "
        + " ".join(f":{COLOUR[f.rule]}-badge[{FLAG_LABELS[f.rule]}]" for f in w.flags)
        for w in flagged
    ]
    assert [h[2:12] for h in heads] == sorted(h[2:12] for h in heads)
    lists = [v for v in vals if v.startswith("- **")]
    assert lists == [
        "\n".join(f"- **{FLAG_LABELS[f.rule]}:** {f.reason}" for f in w.flags)
        for w in flagged
    ]
    assert not at.success


def test_flag_badge_colours_cover_every_rule() -> None:
    seen: dict[str, str] = {}
    for country in (ALL, "Bahrain", "Germany"):
        at = open_app(country, None, None, "flags")
        for h in (v for v in markdowns(at) if v.startswith("**20")):
            for colour, label in re.findall(r":(\w+)-badge\[([^\]]+)\]", h):
                seen[label] = colour
    inverse = {v: k for k, v in FLAG_LABELS.items()}
    assert {inverse[label]: c for label, c in seen.items()} == COLOUR


def test_no_flags_shows_success_and_no_groups() -> None:
    at = open_app(ALL, CALM, None, "flags")
    assert [str(s.value) for s in at.success] == [
        "No flagged weeks in the selected range."
    ]
    assert not [v for v in markdowns(at) if v.startswith("**20")]


def test_flag_summary_caption_counts() -> None:
    at = open_app(ALL, None, None, "flags")
    s = scen()
    rules = [f.rule for f in s.flags]
    expected = " · ".join(
        f"{FLAG_LABELS[r]}: {rules.count(r)}" for r in dict.fromkeys(rules)
    )
    assert expected in captions(at)


# ---------- Weekly table ----------


def frame(at: AppTest) -> Any:
    assert len(at.dataframe) == 1
    return at.dataframe[0]


@pytest.mark.parametrize(
    ("country", "span"),
    [
        (ALL, None),
        (UK, None),
        ("Bahrain", None),
        (ALL, SHORT),
        (ALL, (LAST_WEEK, LAST_WEEK)),
    ],
)
def test_table_rows_flags_and_pinning(
    country: str, span: tuple[date, date] | None
) -> None:
    start, end = span or (FIRST_WEEK, LAST_WEEK)
    at = open_app(country, span, None, "table")
    s = scen(country, chosen(at), start, end)
    df = frame(at).value
    assert len(df) == len(s.weeks)
    assert df["Week"].astype(str).tolist() == [str(w.week_start) for w in s.weeks]
    assert df["Flags"].tolist() == [
        ", ".join(FLAG_LABELS[f.rule] for f in w.flags) for w in s.weeks
    ]
    cols = json.loads(frame(at).proto.columns)
    assert cols["Week"]["pinned"] is True
    assert not cols.get("Flags", {}).get("pinned")
    assert list(df.columns)[:2] == ["Week", "Flags"]


def test_table_change_cells_match_core_signs() -> None:
    at = open_app(ALL, None, None, "table")
    s = scen()
    df = frame(at).value
    for col, key in (("Rev. change", "revenue_wow"), ("Orders change", "orders_wow")):
        for got, w in zip(df[col].tolist(), s.weeks, strict=True):
            want = getattr(w, key)
            assert math.isnan(got) if want is None else got == pytest.approx(want)
    assert any(v > 0 for v in df["Rev. change"].dropna())
    assert any(v < 0 for v in df["Rev. change"].dropna())


def test_table_download_button_present() -> None:
    at = open_app(ALL, SHORT, None, "table")
    assert len(at.get("download_button")) == 1


# ---------- top lists ----------


@pytest.mark.parametrize(
    ("country", "week"),
    [
        (ALL, DEFAULT_WEEK),
        (UK, date(2011, 9, 19)),
        (OUTSIDE_UK, date(2011, 5, 9)),
        ("Germany", date(2011, 3, 7)),
        ("Bahrain", date(2011, 6, 6)),
        (ALL, date(2010, 12, 27)),
    ],
)
def test_top_lists_names_and_share(country: str, week: date) -> None:
    at = open_app(country, None, week)
    s = scen(country, week)
    frames = [d.value for d in at.dataframe]
    prods, ctrs = (frames + [None, None])[:2]
    for df, rows, name in (
        (prods, s.top_products, capwords),
        (ctrs, s.top_countries, str),
    ):
        if not rows:
            assert df is None or len(df) == 0
            continue
        assert df is not None
        assert df["Name"].tolist() == [name(r.label) for r in rows]
        assert df["Revenue"].tolist() == pytest.approx([r.revenue for r in rows])
        assert df["Share of week"].tolist() == pytest.approx(
            [100 * r.revenue / s.selected.revenue for r in rows]
        )
        assert all(0 <= v <= 100 for v in df["Share of week"])
    if not s.top_products:
        assert "No sales this week." in captions(at)


def test_top_product_names_are_title_case() -> None:
    at = open_app(ALL, None, date(2011, 9, 19))
    names = at.dataframe[0].value["Name"].tolist()
    assert names and all(n == capwords(n) for n in names)
    assert names != [n.upper() for n in names]


def test_top_lists_at_most_five_rows() -> None:
    at = open_app(ALL, None, date(2011, 9, 19))
    assert all(len(d.value) <= 5 for d in at.dataframe)


# ---------- Methodology ----------


def test_methodology_mentions_threshold_and_with_your_data() -> None:
    at = open_app(ALL, None, None, "overview")
    at.switch_page("views/methodology.py").run()
    assert not at.exception
    text = "\n".join(markdowns(at))
    assert "40.0%" in text
    assert "### With your data" in text
    after = text.split("### With your data")[1].split("###")[0]
    for word in ("margin", "stock", "targets", "Monday email", "ERP"):
        assert word in after
    assert not any(c.startswith("Range 20") for c in captions(at))
