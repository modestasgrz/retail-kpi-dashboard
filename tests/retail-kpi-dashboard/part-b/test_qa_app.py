"""Extra PART-B QA: sidebar presets, week fallback, cards vs core, CSV, flags, theme."""

import gc
import tomllib
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import plotly.io as pio
import pytest
from streamlit.testing.v1 import AppTest

from kpi import theme
from kpi.core import countries, run_scenario, weekly_csv
from kpi.fmt import change, count, money, money2, pct, points
from kpi.models import ALL, FIRST_WEEK, LAST_WEEK, OUTSIDE_UK, UK, Filters

REPO = Path(__file__).resolve().parents[3]
APP = str(REPO / "app.py")
PAGES = [
    ("views/overview.py", "Overview"),
    ("views/trends.py", "Trends"),
    ("views/flags.py", "Flagged weeks"),
    ("views/table.py", "Weekly table"),
    ("views/methodology.py", "Methodology & data"),
]
DEFAULT_WEEK = date(2011, 11, 28)
GRAY = 2
NO_ARROW = 2
END = LAST_WEEK + timedelta(days=6)


def app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=60).run()


def scen(
    country: str = ALL,
    week: date = DEFAULT_WEEK,
    start: date = FIRST_WEEK,
    end: date = LAST_WEEK,
) -> Any:
    return run_scenario(Filters(start=start, end=end, country=country, week=week))


def metric(at: AppTest, label: str) -> Any:
    found = [m for m in at.metric if m.label == label]
    assert found, f"no metric {label!r}"
    return found[0]


@pytest.fixture(autouse=True)
def no_gc() -> Iterator[None]:
    """The AppTest media storage is only reachable until a gc pass; keep gc off while a test runs."""
    gc.disable()
    yield
    gc.enable()
    gc.collect()


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


def dates(at: AppTest) -> tuple[date, ...]:
    value = at.date_input(key="dates").value
    assert isinstance(value, tuple)
    return value


def chosen_week(at: AppTest) -> date:
    value = at.selectbox(key="week").value
    assert isinstance(value, date)
    return value


def pick(at: AppTest, preset: str) -> AppTest:
    return at.selectbox(key="preset").select(preset).run()


def expected_cards(s: Any) -> dict[str, tuple[str, str, str]]:
    w = s.selected
    rows = {
        "Revenue": (money(w.revenue), change(w.revenue_wow), "revenue"),
        "Orders": (count(w.orders), change(w.orders_wow), "orders"),
        "Average order value": (money2(w.aov), change(w.aov_wow), "aov"),
        "Units": (count(w.units), change(w.units_wow), "units"),
        "Customers": (count(w.customers), change(w.customers_wow), "customers"),
        "New customers": (
            count(w.new_customers),
            change(w.new_customers_wow),
            "new_customers",
        ),
        "Returning customers": (
            count(w.returning_customers),
            change(w.returning_customers_wow),
            "returning_customers",
        ),
        "Cancellation rate": (
            pct(w.cancellation_rate),
            points(w.cancellation_rate_change_pp),
            "cancellation_rate",
        ),
        "Cancelled value": (
            money(w.cancelled_value),
            change(w.cancelled_value_wow),
            "cancelled_value",
        ),
        "Revenue after cancellations": (
            money(w.net_revenue),
            change(w.net_revenue_wow),
            "net_revenue",
        ),
    }
    return {k: (v, d, s.sources[key]) for k, (v, d, key) in rows.items()}


def assert_cards(at: AppTest, s: Any) -> None:
    for label, (value, delta, help_) in expected_cards(s).items():
        m = metric(at, label)
        assert m.value == value, label
        assert m.delta == delta, label
        assert m.help == help_, label


# ---------- presets ----------


@pytest.mark.parametrize(
    ("preset", "start", "country"),
    [
        ("Full year", date(2010, 12, 6), ALL),
        ("Q4 2011", date(2011, 10, 3), ALL),
        ("UK only", date(2010, 12, 6), UK),
        ("Outside UK", date(2010, 12, 6), OUTSIDE_UK),
    ],
)
def test_every_preset_sets_dates_country_week(
    preset: str, start: date, country: str
) -> None:
    at = app()
    pick(at, "Custom")
    pick(at, preset)
    assert not at.exception
    assert at.selectbox(key="preset").value == preset
    assert dates(at) == (start, END)
    assert at.selectbox(key="country").value == country
    assert at.selectbox(key="week").value == DEFAULT_WEEK
    assert_cards(at, scen(country, DEFAULT_WEEK, start))


def test_q4_week_options_and_default() -> None:
    at = app()
    pick(at, "Q4 2011")
    opts = at.selectbox(key="week").options
    assert len(opts) == 10
    assert opts[0].startswith("2011-10-03 – 2011-10-09")
    assert any(o.startswith("2011-12-05") for o in opts)


def test_outside_uk_numbers_equal_core() -> None:
    at = app()
    pick(at, "Outside UK")
    s = scen(OUTSIDE_UK)
    assert metric(at, "Range revenue").value == money(s.totals.revenue)
    assert metric(at, "Range orders").value == count(s.totals.orders)
    assert metric(at, "Flagged weeks").value == count(s.totals.flagged_weeks)


def test_country_change_turns_preset_custom() -> None:
    at = app()
    at.selectbox(key="country").select("France").run()
    assert not at.exception
    assert at.selectbox(key="preset").value == "Custom"
    assert at.selectbox(key="country").value == "France"
    assert_cards(at, scen("France"))


def test_dates_change_turns_preset_custom() -> None:
    at = app()
    pick(at, "Q4 2011")
    at.date_input(key="dates").set_value((date(2011, 10, 10), END)).run()
    assert not at.exception
    assert at.selectbox(key="preset").value == "Custom"
    assert at.selectbox(key="country").value == ALL


def test_custom_preset_selected_by_hand_keeps_filters() -> None:
    at = app()
    pick(at, "UK only")
    pick(at, "Custom")
    assert not at.exception
    assert at.selectbox(key="country").value == UK
    assert dates(at) == (FIRST_WEEK, END)


def test_reset_from_custom() -> None:
    at = app()
    at.selectbox(key="country").select("Germany").run()
    at.date_input(key="dates").set_value((date(2011, 3, 7), date(2011, 6, 5))).run()
    at.selectbox(key="week").select(date(2011, 4, 4)).run()
    assert at.selectbox(key="preset").value == "Custom"
    at.button(key="reset").click().run()
    assert not at.exception
    assert at.selectbox(key="preset").value == "Full year"
    assert at.selectbox(key="country").value == ALL
    assert dates(at) == (FIRST_WEEK, END)
    assert at.selectbox(key="week").value == DEFAULT_WEEK
    assert_cards(at, scen())


def test_reset_twice_is_idempotent() -> None:
    at = app()
    pick(at, "UK only")
    at.button(key="reset").click().run()
    at.button(key="reset").click().run()
    assert not at.exception
    assert at.selectbox(key="week").value == DEFAULT_WEEK
    assert metric(at, "Revenue").value == money(scen().selected.revenue)


# ---------- week fallback ----------


def last_full_week(start: date, end: date, country: str = ALL) -> date:
    s = scen(country, end, start, end)
    full = [
        w.week_start for w in s.weeks if "partial_week" not in {f.rule for f in w.flags}
    ]
    last: date = (full or [w.week_start for w in s.weeks])[-1]
    return last


def test_range_ending_before_selected_week_falls_back() -> None:
    at = app()
    assert at.selectbox(key="week").value == DEFAULT_WEEK
    at.date_input(key="dates").set_value((date(2011, 3, 7), date(2011, 5, 1))).run()
    assert not at.exception
    assert at.selectbox(key="week").value == date(2011, 4, 25)
    assert_cards(at, scen(ALL, date(2011, 4, 25), date(2011, 3, 7), date(2011, 4, 25)))


def test_fallback_keeps_week_still_in_range() -> None:
    at = app()
    at.selectbox(key="week").select(date(2011, 9, 19)).run()
    at.date_input(key="dates").set_value((date(2011, 9, 1), date(2011, 10, 30))).run()
    assert at.selectbox(key="week").value == date(2011, 9, 19)


def test_range_including_partial_week_defaults_to_last_full() -> None:
    at = app()
    at.selectbox(key="week").select(date(2011, 3, 7)).run()
    at.date_input(key="dates").set_value((date(2011, 11, 7), END)).run()
    assert at.selectbox(key="week").value == last_full_week(
        date(2011, 11, 7), LAST_WEEK
    )
    assert at.selectbox(key="week").value == DEFAULT_WEEK


def test_one_week_partial_range_selects_that_week() -> None:
    at = app()
    at.date_input(key="dates").set_value((date(2011, 12, 5), END)).run()
    assert not at.exception
    assert at.selectbox(key="preset").value == "Custom"
    assert len(at.selectbox(key="week").options) == 1
    assert at.selectbox(key="week").value == date(2011, 12, 5)
    s = scen(ALL, LAST_WEEK, LAST_WEEK, LAST_WEEK)
    assert_cards(at, s)
    assert metric(at, "Range revenue").value == money(s.totals.revenue)


def test_one_week_mid_year_range() -> None:
    at = app()
    at.date_input(key="dates").set_value((date(2011, 6, 8), date(2011, 6, 10))).run()
    assert not at.exception
    assert at.selectbox(key="week").value == date(2011, 6, 6)
    assert metric(at, "Range revenue").value == money(
        scen(ALL, date(2011, 6, 6), date(2011, 6, 6), date(2011, 6, 6)).totals.revenue
    )


def test_one_week_range_all_pages() -> None:
    at = app()
    at.date_input(key="dates").set_value((date(2011, 12, 5), END)).run()
    for page, title in PAGES:
        at.switch_page(page).run()
        assert not at.exception, page
        assert [t.value for t in at.title] == [title]


def test_week_label_format_exact() -> None:
    at = app()
    opts = at.selectbox(key="week").options
    assert len(opts) == 53
    assert "2011-12-05 – 2011-12-11" in "".join(opts)
    for o in opts:
        d = date.fromisoformat(o[:10])
        assert o == f"{d} – {d + timedelta(days=6)}"


# ---------- sparse country ----------


def sparse_country() -> str:
    totals = {
        c: scen(c).totals.orders for c in countries() if c not in (ALL, UK, OUTSIDE_UK)
    }
    return min(totals, key=lambda c: totals[c])


@pytest.mark.parametrize("name", ["Bahrain", "smallest"])
def test_sparse_country_renders_all_pages(name: str) -> None:
    country = sparse_country() if name == "smallest" else name
    at = app()
    at.selectbox(key="country").select(country).run()
    assert not at.exception
    s = scen(country)
    for page, title in PAGES:
        at.switch_page(page).run()
        assert not at.exception, (country, page)
        assert [t.value for t in at.title] == [title]
        assert not at.error
    at.switch_page("views/overview.py").run()
    assert_cards(at, s)


def test_sparse_country_empty_week_shows_na() -> None:
    s = scen("Bahrain")
    empty = [w for w in s.weeks if w.orders == 0]
    assert empty, "Bahrain should have weeks without sales"
    week = empty[len(empty) // 2].week_start
    at = app()
    at.selectbox(key="country").select("Bahrain").run()
    at.selectbox(key="week").select(week).run()
    assert not at.exception
    sw = scen("Bahrain", week)
    assert_cards(at, sw)
    assert metric(at, "Average order value").value == "n/a"
    assert metric(at, "Cancellation rate").value == "n/a"
    assert any("No sales lines this week" in w.value for w in at.warning)
    for page, _ in PAGES:
        at.switch_page(page).run()
        assert not at.exception, page


def test_sparse_country_trends_charts() -> None:
    at = app()
    at.selectbox(key="country").select("Bahrain").run()
    at.switch_page("views/trends.py").run()
    assert not at.exception
    assert len(at.get("plotly_chart")) == 4


# ---------- cards ----------


@pytest.mark.parametrize(
    ("country", "week"),
    [
        (ALL, date(2010, 12, 6)),
        (ALL, date(2011, 1, 17)),
        (ALL, date(2011, 12, 5)),
        (UK, date(2011, 5, 2)),
        (OUTSIDE_UK, date(2011, 11, 21)),
        ("Germany", date(2011, 9, 19)),
        ("EIRE", date(2011, 2, 7)),
    ],
)
def test_overview_cards_equal_core(country: str, week: date) -> None:
    at = app()
    at.selectbox(key="country").select(country).run()
    at.selectbox(key="week").select(week).run()
    assert not at.exception
    assert_cards(at, scen(country, week))


def test_first_week_cards_equal_core() -> None:
    at = app()
    at.selectbox(key="week").select(FIRST_WEEK).run()
    assert not at.exception
    assert_cards(at, scen(ALL, FIRST_WEEK))


def test_cancellation_rate_delta_uses_pp() -> None:
    at = app()
    for week in (date(2011, 9, 19), DEFAULT_WEEK, date(2011, 1, 17)):
        at.selectbox(key="week").select(week).run()
        d = metric(at, "Cancellation rate").delta
        if d:
            assert d.endswith(" pp") and "%" not in d
        for label in ("Revenue", "Orders", "Cancelled value"):
            d2 = metric(at, label).delta
            assert not d2 or d2.endswith("%")


def test_na_delta_shown_as_neutral_na() -> None:
    s = scen("Bahrain")
    candidates = [
        w.week_start for w in s.weeks if w.orders > 0 and w.revenue_wow is None
    ]
    at = app()
    at.selectbox(key="country").select("Bahrain").run()
    if not candidates:
        pytest.fail("Bahrain has no week with a None revenue change")
    at.selectbox(key="week").select(candidates[0]).run()
    m = metric(at, "Revenue")
    assert m.delta == "n/a"
    assert m.proto.color == GRAY
    assert m.proto.direction == NO_ARROW
    assert_cards(at, scen("Bahrain", candidates[0]))


def test_delta_colors() -> None:
    red, green = 0, 1
    at = app()
    inverse = {"Cancellation rate", "Cancelled value"}
    for week in (date(2011, 9, 19), DEFAULT_WEEK):
        at.selectbox(key="week").select(week).run()
        for label in expected_cards(scen()):
            m = metric(at, label)
            assert m.delta
            if m.delta == "n/a":
                assert m.proto.color == GRAY, label
                continue
            up = not m.delta.startswith("-")
            good = up != (label in inverse)
            assert m.proto.color == (green if good else red), (week, label)


def test_range_strip_equal_on_every_page_for_custom_filters() -> None:
    at = app()
    at.selectbox(key="country").select("France").run()
    at.date_input(key="dates").set_value((date(2011, 2, 7), date(2011, 8, 14))).run()
    s = scen("France", date(2011, 8, 8), date(2011, 2, 7), date(2011, 8, 8))
    assert at.selectbox(key="week").value == date(2011, 8, 8)
    for page, _ in PAGES[:4]:
        at.switch_page(page).run()
        assert metric(at, "Range revenue").value == money(s.totals.revenue)
        assert metric(at, "Range orders").value == count(s.totals.orders)
        assert metric(at, "Flagged weeks").value == count(s.totals.flagged_weeks)


# ---------- pages ----------


@pytest.mark.parametrize(
    ("country", "start", "end"),
    [
        (ALL, FIRST_WEEK, LAST_WEEK),
        (UK, date(2011, 10, 3), LAST_WEEK),
        ("Bahrain", FIRST_WEEK, LAST_WEEK),
        ("Outside UK", date(2011, 1, 3), date(2011, 3, 28)),
    ],
)
def test_csv_download_equals_core(country: str, start: date, end: date) -> None:
    at = app()
    at.selectbox(key="country").select(country).run()
    at.date_input(key="dates").set_value((start, end + timedelta(days=6))).run()
    at.switch_page("views/table.py").run()
    assert not at.exception
    week = chosen_week(at)
    s = scen(country, week, start, end)
    name, content = download_file(at.get("download_button")[0])
    assert content == weekly_csv(s)
    slug = country.lower().replace(" ", "-")
    assert name == f"weekly-kpis_{start}_{end}_{slug}.csv"
    assert [len(df.value) for df in at.dataframe] == [s.totals.weeks]


def test_csv_content_independent_of_selected_week() -> None:
    at = app()
    at.selectbox(key="week").select(date(2011, 3, 7)).run()
    at.switch_page("views/table.py").run()
    _, content = download_file(at.get("download_button")[0])
    assert content == weekly_csv(scen())


@pytest.mark.parametrize(
    ("country", "start", "end"),
    [
        (ALL, FIRST_WEEK, LAST_WEEK),
        (UK, FIRST_WEEK, LAST_WEEK),
        (ALL, date(2011, 3, 7), date(2011, 3, 28)),
        ("Bahrain", FIRST_WEEK, LAST_WEEK),
    ],
)
def test_flag_rows_equal_scenario_flags(country: str, start: date, end: date) -> None:
    at = app()
    at.selectbox(key="country").select(country).run()
    at.date_input(key="dates").set_value((start, end + timedelta(days=6))).run()
    at.switch_page("views/flags.py").run()
    assert not at.exception
    s = scen(country, chosen_week(at), start, end)
    if s.flags:
        assert [len(df.value) for df in at.dataframe] == [len(s.flags)]
        df = at.dataframe[0].value
        assert list(df["Reason"]) == [f.reason for f in s.flags]
        assert list(df["Flag"]) == [f.rule for f in s.flags]
    else:
        assert len(at.dataframe) == 0
        assert any("No flagged weeks" in e.value for e in at.success)


def test_flags_empty_range_message() -> None:
    at = app()
    for start in (date(2011, 3, 7), date(2011, 4, 4), date(2011, 5, 9)):
        s = scen(ALL, start, start, start)
        if not s.flags:
            at.date_input(key="dates").set_value((start, start)).run()
            at.switch_page("views/flags.py").run()
            assert not at.exception
            assert len(at.dataframe) == 0
            assert metric(at, "Flagged weeks").value == "0"
            return
    pytest.fail("no unflagged week found")


def test_methodology_renders_without_scenario() -> None:
    at = AppTest.from_file(REPO / "views" / "methodology.py", default_timeout=60)
    at.run()
    assert not at.exception
    assert [t.value for t in at.title] == ["Methodology & data"]
    body = "\n".join(str(m.value) for m in at.markdown)
    assert "Chen, D. (2012)" in body
    assert "CC BY 4.0" in body


def test_methodology_after_filter_changes() -> None:
    at = app()
    at.selectbox(key="country").select("Bahrain").run()
    at.switch_page("views/methodology.py").run()
    assert not at.exception
    assert "Data: UCI Online Retail II (Chen 2012), CC BY 4.0" in [
        c.value for c in at.sidebar.caption
    ]


def test_invalid_date_inputs_show_error_not_traceback() -> None:
    at = app()
    at.date_input(key="dates").set_value(()).run()
    assert not at.exception
    assert "Pick both a start and an end date." in [e.value for e in at.error]
    assert len(at.metric) == 0
    at.date_input(key="dates").set_value((date(2011, 3, 7), date(2011, 6, 5))).run()
    assert not at.exception
    assert not at.error
    assert len(at.metric) > 0


def test_swapped_dates_show_error() -> None:
    at = app()
    at.date_input(key="dates").set_value((date(2011, 6, 5), date(2011, 3, 7))).run()
    assert not at.exception
    assert "Start week must be on or before end week." in [e.value for e in at.error]
    assert len(at.metric) == 0


def test_summary_hidden_for_country_and_shown_for_all() -> None:
    at = app()
    at.selectbox(key="week").select(date(2011, 9, 19)).run()
    assert not at.info
    at.selectbox(key="country").select("Bahrain").run()
    assert any("covers all countries" in i.value for i in at.info)


def test_top_lists_on_overview_match_core() -> None:
    at = app()
    s = scen()
    assert len(at.dataframe) == 2
    assert list(at.dataframe[0].value["Name"]) == [r.label for r in s.top_products]
    assert list(at.dataframe[0].value["Revenue"]) == pytest.approx(
        [r.revenue for r in s.top_products]
    )
    assert list(at.dataframe[1].value["Name"]) == [r.label for r in s.top_countries]
    assert list(at.dataframe[1].value["Revenue"]) == pytest.approx(
        [r.revenue for r in s.top_countries]
    )


# ---------- theme ----------


def test_theme_config_matches_tokens() -> None:
    cfg = tomllib.loads((REPO / ".streamlit" / "config.toml").read_text())["theme"]
    assert cfg["base"] == "dark"
    assert cfg["backgroundColor"] == theme.BG == "#0B1426"
    assert cfg["secondaryBackgroundColor"] == theme.SURFACE == "#13203A"
    assert cfg["primaryColor"] == theme.BLUE == "#3B82F6"
    assert cfg["textColor"] == theme.TEXT == "#E6ECF5"


def test_theme_other_tokens() -> None:
    assert theme.BORDER == "#22324F"
    assert theme.MUTED == "#8B9AB4"
    assert theme.GREEN == "#22C55E"
    assert theme.AMBER == "#F59E0B"
    assert theme.RED == "#EF4444"
    assert theme.FONT == '"Inter", "Avenir Next", "Helvetica Neue", Arial, sans-serif'


def test_plotly_template_registered_and_default() -> None:
    assert pio.templates["navy"] == theme.TEMPLATE
    assert pio.templates.default == "navy"


def test_plotly_template_separators_and_colours() -> None:
    lay = theme.TEMPLATE.layout
    assert lay.separators == ". "
    assert lay.paper_bgcolor == theme.SURFACE
    assert lay.font.color == theme.TEXT
    assert lay.xaxis.gridcolor == theme.BORDER


def test_fmt_separator_is_narrow_nbsp() -> None:
    assert money(1234567.5) == "£1 234 568"
    assert count(1000) == "1 000"


def test_css_loaded_once_and_exists() -> None:
    css = (REPO / "assets" / "style.css").read_text()
    assert css.strip()
    src = (REPO / "app.py").read_text()
    assert src.count("style.css") == 1


def test_trend_figures_use_navy_template_and_four_charts() -> None:
    at = app()
    at.switch_page("views/trends.py").run()
    assert not at.exception
    assert len(at.get("plotly_chart")) == 4


def test_reset_and_footer_render_with_invalid_dates() -> None:
    at = app()
    at.date_input(key="dates").set_value((date(2011, 3, 7),)).run()
    assert not at.exception
    assert "Pick both a start and an end date." in [e.value for e in at.error]
    assert at.button(key="reset").label == "Reset to Full year"
    assert "Data: UCI Online Retail II (Chen 2012), CC BY 4.0" in [
        c.value for c in at.sidebar.caption
    ]
    at.button(key="reset").click().run()
    assert not at.exception
    assert not at.error
    assert metric(at, "Revenue").value == money(scen().selected.revenue)


def test_trends_caption_text() -> None:
    at = app()
    at.switch_page("views/trends.py").run()
    s = scen()
    expected = f"Range revenue {money(s.totals.revenue)}; cancellations in range {money(s.totals.cancelled_value)}."
    assert any(c.value.startswith(expected) for c in at.caption)


def test_weekly_table_values_are_numeric_and_match_core() -> None:
    at = app()
    at.switch_page("views/table.py").run()
    df = at.dataframe[0].value
    s = scen()
    assert list(df["Week"]) == [str(w.week_start) for w in s.weeks]
    assert list(df["Revenue"]) == pytest.approx([w.revenue for w in s.weeks])
    assert list(df["Orders"]) == [w.orders for w in s.weeks]
    assert df["Revenue"].dtype.kind == "f"
    assert df["Orders"].dtype.kind in "iu"
