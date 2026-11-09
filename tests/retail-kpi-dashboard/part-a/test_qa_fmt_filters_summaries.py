import json
import re
from datetime import date, timedelta
from pathlib import Path

import pytest

from kpi.fmt import change, count, money, money2, pct, points
from kpi.models import FIRST_WEEK, LAST_WEEK, MAX_DATE, Filters
from kpi.summaries import build_summaries, extract

N = " "
DATES_MSG = "Dates must be between 2010-12-06 and 2011-12-11."
ORDER_MSG = "Start week must be on or before end week."
INSIDE_MSG = "Selected week must be inside the date range."


# ---------------------------------------------------------------- formatters


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.0, "£0"),
        (0.49999, "£0"),
        (0.5, "£1"),
        (1.5, "£2"),
        (2.5, "£3"),
        (999.5, f"£1{N}000"),
        (538.325, "£538"),
        (1234567.5, f"£1{N}234{N}568"),
        (1234567890.5, f"£1{N}234{N}567{N}891"),
        (-0.4, "£0"),
        (-0.5, "-£1"),
        (-2.5, "-£3"),
        (-1234.5, f"-£1{N}235"),
    ],
)
def test_money_half_up_and_grouping(value: float, expected: str) -> None:
    assert money(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (538.325, "£538.33"),
        (1.005, "£1.01"),
        (2.675, "£2.68"),
        (0.045, "£0.05"),
        (0.005, "£0.01"),
        (0.0049999, "£0.00"),
        (999.995, f"£1{N}000.00"),
        (1234567.895, f"£1{N}234{N}567.90"),
        (-538.325, "-£538.33"),
        (-0.005, "-£0.01"),
        (-1234.565, f"-£1{N}234.57"),
        (0.0, "£0.00"),
    ],
)
def test_money2_half_up_incl_float_noise(value: float, expected: str) -> None:
    assert money2(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.05, "+0.1%"),
        (-0.05, "-0.1%"),
        (0.049999, "+0.0%"),
        (-0.049999, "+0.0%"),
        (24.95, "+25.0%"),
        (-24.95, "-25.0%"),
        (-24.96, "-25.0%"),
        (24.94, "+24.9%"),
        (153.75, "+153.8%"),
        (1234.55, f"+1{N}234.6%"),
        (-1234.55, f"-1{N}234.6%"),
        (-100.0, "-100.0%"),
    ],
)
def test_change_rounding_and_sign(value: float, expected: str) -> None:
    assert change(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (-1.25, "-1.3 pp"),
        (1.25, "+1.3 pp"),
        (0.05, "+0.1 pp"),
        (-0.04, "+0.0 pp"),
        (0.0, "+0.0 pp"),
        (1234.56, f"+1{N}234.6 pp"),
    ],
)
def test_points_rounding_and_sign(value: float, expected: str) -> None:
    assert points(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (16.65, "16.7%"),
        (16.649, "16.6%"),
        (0.05, "0.1%"),
        (0.0, "0.0%"),
        (100.0, "100.0%"),
        (25.0, "25.0%"),
        (24.95, "25.0%"),
    ],
)
def test_pct_rounding(value: float, expected: str) -> None:
    assert pct(value) == expected


def test_pct_groups_thousands_with_narrow_nbsp() -> None:
    """AC-13: every thousands separator is U+202F. Shares above 1 000 % (a huge cancellation week) hit this."""
    assert pct(1234.5) == f"1{N}234.5%"


def test_pct_never_shows_negative_zero() -> None:
    assert pct(-0.04) == "0.0%"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, "0"),
        (999, "999"),
        (1000, f"1{N}000"),
        (1_000_000, f"1{N}000{N}000"),
        (-1234, f"-1{N}234"),
    ],
)
def test_count_grouping(value: int, expected: str) -> None:
    assert count(value) == expected


def test_formatters_never_emit_ascii_or_nbsp_separators() -> None:
    for text in (money(1e9), money2(1e9), count(10**9), change(1e5), points(1e5)):
        assert not re.search(r"\d[ \u00a0]\d", text)
        assert re.search(rf"\d{N}\d", text)


# ------------------------------------------------------------------- Filters


def mk(start: date, end: date, week: date, country: str = "All countries") -> Filters:
    return Filters(start=start, end=end, week=week, country=country)


def test_filters_accept_every_boundary_date() -> None:
    f = mk(FIRST_WEEK, MAX_DATE, MAX_DATE)
    assert (f.start, f.end, f.week) == (FIRST_WEEK, LAST_WEEK, LAST_WEEK)
    f = mk(FIRST_WEEK, FIRST_WEEK, FIRST_WEEK)
    assert (f.start, f.end, f.week) == (FIRST_WEEK,) * 3
    assert MAX_DATE == date(2011, 12, 11)


@pytest.mark.parametrize(
    "bad",
    [
        date(2010, 12, 5),
        date(2010, 11, 29),
        date(2011, 12, 12),
        date(2011, 12, 19),
        date(2000, 1, 1),
        date(2099, 1, 1),
    ],
)
@pytest.mark.parametrize("slot", ["start", "end", "week"])
def test_filters_reject_dates_outside_bounds(bad: date, slot: str) -> None:
    d = {
        "start": date(2011, 9, 19),
        "end": date(2011, 9, 19),
        "week": date(2011, 9, 19),
    }
    d[slot] = bad
    with pytest.raises(ValueError, match=re.escape(DATES_MSG)):
        mk(d["start"], d["end"], d["week"])


def test_filters_start_after_end() -> None:
    with pytest.raises(ValueError, match=re.escape(ORDER_MSG)):
        mk(date(2011, 9, 26), date(2011, 9, 19), date(2011, 9, 19))


def test_filters_start_after_end_wins_over_week_outside() -> None:
    with pytest.raises(ValueError, match=re.escape(ORDER_MSG)):
        mk(date(2011, 9, 26), date(2011, 9, 19), date(2011, 10, 3))


def test_filters_start_after_end_in_days_but_same_week_is_valid() -> None:
    f = mk(date(2011, 9, 23), date(2011, 9, 20), date(2011, 9, 21))
    assert (f.start, f.end, f.week) == (date(2011, 9, 19),) * 3


@pytest.mark.parametrize(
    ("week", "ok"),
    [
        (date(2011, 9, 12), False),
        (date(2011, 9, 18), False),
        (date(2011, 9, 19), True),
        (date(2011, 9, 25), True),
        (date(2011, 9, 26), False),
    ],
)
def test_filters_week_must_be_inside_range(week: date, ok: bool) -> None:
    if ok:
        assert mk(date(2011, 9, 19), date(2011, 9, 19), week).week == date(2011, 9, 19)
    else:
        with pytest.raises(ValueError, match=re.escape(INSIDE_MSG)):
            mk(date(2011, 9, 19), date(2011, 9, 19), week)


def test_filters_every_weekday_snaps_to_monday() -> None:
    monday = date(2011, 9, 19)
    for offset in range(7):
        day = monday + timedelta(days=offset)
        f = mk(day, day, day)
        assert f.start == f.end == f.week == monday
        assert f.start.weekday() == 0


def test_filters_first_sunday_snaps_to_first_week() -> None:
    f = mk(date(2010, 12, 12), date(2010, 12, 12), date(2010, 12, 12))
    assert f.week == FIRST_WEEK


def test_filters_date_check_precedes_snapping() -> None:
    """2010-12-05 is a Sunday whose ISO week starts 2010-11-29, before the first shown week: still refused."""
    with pytest.raises(ValueError, match=re.escape(DATES_MSG)):
        mk(date(2010, 12, 5), date(2011, 9, 19), date(2011, 9, 19))


def test_filters_full_range_has_53_weeks() -> None:
    assert (LAST_WEEK - FIRST_WEEK).days // 7 + 1 == 53


def test_filters_error_is_plain_value_error_with_exact_message() -> None:
    with pytest.raises(ValueError, match=re.escape(DATES_MSG)) as exc:
        mk(date(2012, 1, 1), date(2012, 1, 1), date(2012, 1, 1))
    assert DATES_MSG in str(exc.value)
    assert "Traceback" not in str(exc.value)


def test_filters_country_is_kept_verbatim() -> None:
    f = mk(FIRST_WEEK, FIRST_WEEK, FIRST_WEEK, country=" France ")
    assert f.country == " France "
    assert mk(FIRST_WEEK, FIRST_WEEK, FIRST_WEEK).country == "All countries"


# ----------------------------------------------------------------- summaries


def wrap(body: str, heading: str = "## Headline here") -> str:
    return f"# Weekly\n\n{heading}\n\n{body}\n\n## Worth a look\n\n- x\n"


def test_extract_crlf_equals_lf() -> None:
    md = wrap("First para [F1].\n\nSecond 1,234 para.")
    assert extract(md.replace("\n", "\r\n")) == extract(md)


def test_extract_heading_trailing_spaces_stripped() -> None:
    s = extract(wrap("Body.", heading="## Headline here   "))
    assert s is not None
    assert s.headline == "Headline here"


@pytest.mark.parametrize(
    "md",
    [
        "",
        "\n\n",
        "##NoSpace\n\ntext\n",
        "### Sub heading\n\ntext\n",
        "# Only title\n\ntext\n",
        "## Heading only",
        "## Heading\n\n## Worth a look\n\ntext\n",
        "## Heading\n\n- bullet one\n- bullet two\n",
        "## Heading\n\n> quote only\n",
    ],
)
def test_extract_returns_none_without_headline_and_body(md: str) -> None:
    assert extract(md) is None


def test_extract_ignores_text_before_first_heading_and_later_sections() -> None:
    md = "Intro text.\n\n## Head\n\nKept.\n\n## Worth a look\n\nDropped.\n\n## Other\n\nAlso dropped.\n"
    s = extract(md)
    assert s is not None
    assert (s.headline, s.text) == ("Head", "Kept.")


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ("Sold £1,234 [F3].", f"Sold £1{N}234."),
        ("Sold [F3] and [F12] units.", "Sold and units."),
        ("Two[F1][F2] markers.", "Two markers."),
        ("[F7] starts here.", "starts here."),
        ("Big 1,234,567 units.", f"Big 1{N}234{N}567 units."),
        ("Price £12,345.67 today.", f"Price £12{N}345.67 today."),
        ("Five digits 1,2345 stay.", "Five digits 1,2345 stay."),
        ("Letters a,123 stay.", "Letters a,123 stay."),
        ("Two digits 1,23 stay.", "Two digits 1,23 stay."),
        ("List 1, 234 stays.", "List 1, 234 stays."),
        ("Café ☕ naïve 東京 stays.", "Café ☕ naïve 東京 stays."),
        ("Not a marker [Fx] or [F].", "Not a marker [Fx] or [F]."),
    ],
)
def test_extract_cleaning_rules(raw: str, clean: str) -> None:
    s = extract(wrap(raw))
    assert s is not None
    assert s.text == clean


def test_extract_cleans_headline_too() -> None:
    s = extract(wrap("Body.", heading="## Sales hit £1,234,567 [F2]"))
    assert s is not None
    assert s.headline == f"Sales hit £1{N}234{N}567"


def test_extract_paragraph_starting_with_a_negative_number_is_kept() -> None:
    """A narrative line like '-5.1% on last week ...' is not a markdown bullet ('- ')."""
    s = extract(wrap("-5.1% on last week was the story."))
    assert s is not None
    assert s.text == "-5.1% on last week was the story."


def test_extract_wrapped_paragraph_stays_one_paragraph() -> None:
    s = extract(wrap("A long paragraph wrapped\nonto a second line."))
    assert s is not None
    assert "\n\n" not in s.text


def test_build_summaries_empty_src_writes_empty_object(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    out = tmp_path / "deep" / "nested" / "summaries.json"
    assert build_summaries(tmp_path / "src", out) == 0
    assert json.loads(out.read_text()) == {}


def test_build_summaries_ignores_non_report_files_and_empty_reports(
    tmp_path: Path,
) -> None:
    src = tmp_path / "src"
    (src / "2011-01-03").mkdir(parents=True)
    (src / "2011-01-03" / "notes.md").write_text(wrap("Body."))
    (src / "2011-01-10").mkdir()
    (src / "2011-01-10" / "report.md").write_text("")
    (src / "2011-01-17").mkdir()
    (src / "2011-01-17" / "report.md").write_text(wrap("Body 1,000 [F1]."))
    (src / "stray.md").write_text(wrap("Body."))
    out = tmp_path / "out.json"
    assert build_summaries(src, out) == 1
    data = json.loads(out.read_text())
    assert data == {
        "2011-01-17": {"headline": "Headline here", "text": f"Body 1{N}000."}
    }


def test_build_summaries_is_idempotent_and_sorted(tmp_path: Path) -> None:
    src = tmp_path / "src"
    for week in ("2011-02-07", "2011-01-03"):
        (src / week).mkdir(parents=True)
        (src / week / "report.md").write_text(wrap(f"Body {week}."))
    out = tmp_path / "out.json"
    build_summaries(src, out)
    first = out.read_text()
    build_summaries(src, out)
    assert out.read_text() == first
    assert list(json.loads(first)) == ["2011-01-03", "2011-02-07"]


def test_build_summaries_keeps_unicode_readable_in_file(tmp_path: Path) -> None:
    src = tmp_path / "src"
    (src / "2011-01-03").mkdir(parents=True)
    (src / "2011-01-03" / "report.md").write_text(wrap("Sold 2,500 café mugs."))
    out = tmp_path / "out.json"
    build_summaries(src, out)
    raw = out.read_text(encoding="utf-8")
    assert "café" in raw
    assert f"2{N}500" in raw
