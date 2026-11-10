"""AC-39 — Given the app on defaults (week 2011-11-28), then the Overview shows the markdown ":green-badge[● All clear]" and no expander labelled "Flag details"; when week 2011-12-05 is picked, it shows ":orange-badge[▲ 2 flags]" and an expander "Flag details" whose text contains each flag's label from `FLAG_LABELS` and its full reason; when week 2011-09-19 is picked, the "Flag details" text also contains the drivers line "Top products: Set Of Tea Coffee Sugar Tins Pantry +£8 265"."""

from datetime import date

from fixture import REPO, app

S = "\u202f"


def test_ac_39_flag_status_pill() -> None:
    import kpi.models
    from kpi.core import run_scenario
    from kpi.models import FIRST_WEEK, LAST_WEEK, Filters

    labels: dict[str, str] = vars(kpi.models)["FLAG_LABELS"]
    at = app()
    assert ":green-badge[● All clear]" in [m.value for m in at.markdown]
    assert not [e for e in at.expander if e.label == "Flag details"]
    at.selectbox(key="week").select(date(2011, 12, 5)).run()
    assert not at.exception
    assert ":orange-badge[▲ 2 flags]" in [m.value for m in at.markdown]
    details = [e for e in at.expander if e.label == "Flag details"]
    assert len(details) == 1
    text = "\n".join(str(m.value) for m in details[0].markdown)
    flags = run_scenario(
        Filters(start=FIRST_WEEK, end=LAST_WEEK, week=date(2011, 12, 5)),
        REPO / "data" / "derived",
    ).selected.flags
    assert len(flags) == 2
    for f in flags:
        assert labels[f.rule] in text
        assert f.reason in text
    at.selectbox(key="week").select(date(2011, 9, 19)).run()
    details = [e for e in at.expander if e.label == "Flag details"]
    text = "\n".join(str(m.value) for m in details[0].markdown)
    assert f"Top products: Set Of Tea Coffee Sugar Tins Pantry +£8{S}265" in text
