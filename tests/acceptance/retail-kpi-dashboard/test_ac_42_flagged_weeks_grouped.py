"""AC-42 — Given the app on defaults, when Flagged weeks is opened, then there is one group per flagged week (9 groups), and the group for 2011-12-05 is a markdown heading exactly "**2011-12-05 – 2011-12-11** :gray-badge[Partial week] :blue-badge[Revenue swing] :orange-badge[Large cancellations] :orange-badge[One big order]" followed by a markdown list whose text contains each of the week's full reasons."""

from datetime import date

from fixture import REPO, app

HEADING = "**2011-12-05 – 2011-12-11** :gray-badge[Partial week] :blue-badge[Revenue swing] :orange-badge[Large cancellations] :orange-badge[One big order]"


def test_ac_42_flagged_weeks_grouped() -> None:
    from kpi.core import run_scenario
    from kpi.models import FIRST_WEEK, LAST_WEEK, Filters

    at = app()
    at.switch_page("views/flags.py").run()
    assert not at.exception
    values = [str(m.value) for m in at.markdown]
    headings = [v for v in values if v.startswith("**20")]
    assert len(headings) == 9
    assert HEADING in values
    after = values[values.index(HEADING) + 1]
    week = run_scenario(
        Filters(start=FIRST_WEEK, end=LAST_WEEK, week=date(2011, 12, 5)),
        REPO / "data" / "derived",
    ).selected
    for f in week.flags:
        assert f.reason in after
