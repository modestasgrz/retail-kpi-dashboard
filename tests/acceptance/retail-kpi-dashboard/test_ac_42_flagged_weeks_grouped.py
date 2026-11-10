"""AC-42 — Given the app on defaults, when Flagged weeks is opened, then there is one group per flagged week (9 groups), newest first (the first is 2011-12-05), and the group for 2011-12-05 is a markdown heading exactly "2011-12-05 – 2011-12-11 :gray-badge[Partial week] :orange-badge[Placed and cancelled]" followed by a markdown list whose text contains each of the week's full reasons; the list of 2011-09-19 contains "Top products: Set Of Tea Coffee Sugar Tins Pantry +£8 265", "(11.5% of the change)", "Top countries: United Kingdom +£113 442" and "(90.3% of the change)"; the list of 2010-12-20 contains "United Kingdom -394 orders" (whole numbers)."""

from datetime import date

from fixture import REPO, app

S = "\u202f"
HEADING = "**2011-12-05 – 2011-12-11** :gray-badge[Partial week] :orange-badge[Placed and cancelled]"


def test_ac_42_flagged_weeks_grouped() -> None:
    from kpi.core import run_scenario
    from kpi.models import FIRST_WEEK, LAST_WEEK, Filters

    at = app()
    at.switch_page("views/flags.py").run()
    assert not at.exception
    values = [str(m.value) for m in at.markdown]
    headings = [v for v in values if v.startswith("**20")]
    assert len(headings) == 9
    assert headings[0].startswith("**2011-12-05")
    assert HEADING in values
    after = values[values.index(HEADING) + 1]
    week = run_scenario(
        Filters(start=FIRST_WEEK, end=LAST_WEEK, week=date(2011, 12, 5)),
        REPO / "data" / "derived",
    ).selected
    for f in week.flags:
        assert f.reason in after
    swing = next(v for v in headings if v.startswith("**2011-09-19"))
    drivers = values[values.index(swing) + 1]
    for needle in [
        f"Top products: Set Of Tea Coffee Sugar Tins Pantry +£8{S}265",
        "(11.5% of the change)",
        f"Top countries: United Kingdom +£113{S}442",
        "(90.3% of the change)",
    ]:
        assert needle in drivers, needle
    oldest = next(v for v in headings if v.startswith("**2010-12-20"))
    assert "United Kingdom -394 orders" in values[values.index(oldest) + 1]
