"""AC-38 — Given the app on defaults with week 2011-09-19, then the Overview has no markdown equal to the saved AI headline outside the expander, and one expander labelled "AI-written summary, saved; numbers above are computed" containing the DEC-14 label, the AI headline "Revenue and orders jump to an unusually strong week, led by pantry products" and the summary text with no `"` character; on preset "UK only" there is no such expander and the note "The saved weekly summary covers all countries, so it is hidden while a country filter is on." is shown."""

from datetime import date

from fixture import app, texts

S = "\u202f"
LABEL = "Weekly summary written by AI in an earlier run; every figure was checked against the computed numbers. This app makes no AI calls."
AI_HEADLINE = (
    "Revenue and orders jump to an unusually strong week, led by pantry products"
)
EXPANDER = "AI-written summary, saved; numbers above are computed"
NOTE = "The saved weekly summary covers all countries, so it is hidden while a country filter is on."


def test_ac_38_summary_headline_and_expander() -> None:
    at = app()
    at.selectbox(key="week").select(date(2011, 9, 19)).run()
    assert not at.exception
    values = [str(m.value) for m in at.markdown]
    assert AI_HEADLINE not in values
    found = [e for e in at.expander if e.label == EXPANDER]
    assert len(found) == 1
    inside = "\n".join(
        [str(c.value) for c in found[0].caption]
        + [str(m.value) for m in found[0].markdown]
    )
    assert LABEL in inside
    assert AI_HEADLINE in inside
    assert "SET OF TEA COFFEE SUGAR TINS PANTRY" in inside
    assert '"' not in "\n".join(str(m.value) for m in found[0].markdown)
    at.selectbox(key="preset").select("UK only").run()
    at.selectbox(key="week").select(date(2011, 9, 19)).run()
    assert not at.exception
    assert not [e for e in at.expander if e.label == EXPANDER]
    assert NOTE in texts(at)
