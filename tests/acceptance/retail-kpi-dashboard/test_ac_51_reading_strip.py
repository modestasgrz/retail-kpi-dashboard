"""AC-51 — Given the app on defaults, then each of Overview, Trends, Flagged weeks and Weekly table shows one reading strip (DEC-30): a markdown containing "THE QUESTION", "RIGHT NOW" and "DO THIS" with that page's texts: Overview "How did the selected week go, and does anything need a look?", the computed headline and "Nothing flagged. Scan the top products and countries, then switch weeks in the sidebar."; Trends "Is the selected week part of a trend or a one-off?" and "Net revenue in range £9 593 707; highest full week 2011-11-14 (£369 126), lowest 2011-04-25 (£81 431)."; Flagged weeks "Which weeks need a look, and why?" and "9 of 53 weeks flagged: Revenue swing 6 · Orders swing 3 · No sales 1 · Placed and cancelled 2 · Partial week 1."; Weekly table "What are the exact weekly numbers?" and "Showing the last 8 of 53 weeks, 2011-10-17 – 2011-12-11."; when week 2011-12-05 is picked, the Overview DO THIS line is "Open Flag details below: Partial week, Placed and cancelled."; Methodology & data has no strip."""

from datetime import date
from typing import Any

from fixture import app

S = "\u202f"
PAGES = {
    "views/overview.py": [
        "How did the selected week go, and does anything need a look?",
        f"Net revenue £306{S}112, +3.7% vs last week, -0.9% vs same week last year; no flags.",
        "Nothing flagged. Scan the top products and countries, then switch weeks in the sidebar.",
    ],
    "views/trends.py": [
        "Is the selected week part of a trend or a one-off?",
        f"Net revenue in range £9{S}593{S}707; highest full week 2011-11-14 (£369{S}126), lowest 2011-04-25 (£81{S}431).",
    ],
    "views/flags.py": [
        "Which weeks need a look, and why?",
        "9 of 53 weeks flagged: Revenue swing 6 · Orders swing 3 · No sales 1 · Placed and cancelled 2 · Partial week 1.",
    ],
    "views/table.py": [
        "What are the exact weekly numbers?",
        "Showing the last 8 of 53 weeks, 2011-10-17 – 2011-12-11.",
    ],
}


def strips(at: Any) -> list[str]:
    return [
        str(m.value)
        for m in at.markdown
        if all(k in str(m.value) for k in ("THE QUESTION", "RIGHT NOW", "DO THIS"))
    ]


def test_ac_51_reading_strip() -> None:
    at = app()
    for page, texts in PAGES.items():
        at.switch_page(page).run()
        assert not at.exception, page
        found = strips(at)
        assert len(found) == 1, page
        for text in texts:
            assert text in found[0], (page, text)
    at.switch_page("views/overview.py").run()
    at.selectbox(key="week").select(date(2011, 12, 5)).run()
    assert (
        "Open Flag details below: Partial week, Placed and cancelled." in strips(at)[0]
    )
    at.switch_page("views/methodology.py").run()
    assert strips(at) == []
