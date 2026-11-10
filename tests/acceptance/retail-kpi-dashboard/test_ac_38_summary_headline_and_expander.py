"""AC-38 — Given the app on defaults with week 2011-09-19, then the Overview shows a markdown element equal to the summary headline "Revenue and orders jump to an unusually strong week, led by pantry products", and an expander labelled "Full weekly summary" containing the DEC-14 label and the summary text with no `"` character; on preset "UK only" there is no "Full weekly summary" expander."""

from datetime import date

from fixture import app

LABEL = "Weekly summary written by AI in an earlier run; every figure was checked against the computed numbers. This app makes no AI calls."
HEADLINE = "Revenue and orders jump to an unusually strong week, led by pantry products"


def test_ac_38_summary_headline_and_expander() -> None:
    at = app()
    at.selectbox(key="week").select(date(2011, 9, 19)).run()
    assert not at.exception
    assert HEADLINE in [m.value for m in at.markdown]
    full = [e for e in at.expander if e.label == "Full weekly summary"]
    assert len(full) == 1
    inside = "\n".join(
        [str(c.value) for c in full[0].caption]
        + [str(m.value) for m in full[0].markdown]
    )
    assert LABEL in inside
    assert "SET OF TEA COFFEE SUGAR TINS PANTRY" in inside
    body = "\n".join(str(m.value) for m in full[0].markdown)
    assert '"' not in body
    at.selectbox(key="preset").select("UK only").run()
    assert not [e for e in at.expander if e.label == "Full weekly summary"]
