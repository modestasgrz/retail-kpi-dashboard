"""AC-48 — Given the app on defaults, then the Overview big cards show "Net revenue" "£306 112", "Orders" "663", "Avg order (net)" "£461.71", each with `delta_description` "vs last week", and right below each a caption "-0.9% vs same week last year", "+1.7% vs same week last year", "-2.6% vs same week last year"; when week 2011-12-05 is picked, each of the three captions is "— vs same week last year"."""

from datetime import date

from fixture import app, metric

S = "\u202f"
CARDS = {
    "Net revenue": (f"£306{S}112", "-0.9% vs same week last year"),
    "Orders": ("663", "+1.7% vs same week last year"),
    "Avg order (net)": ("£461.71", "-2.6% vs same week last year"),
}


def test_ac_48_big_cards_year_over_year() -> None:
    at = app()
    assert not at.exception
    captions = [str(c.value) for c in at.caption]
    for label, (value, yoy) in CARDS.items():
        m = metric(at, label)
        assert m.value == value, label
        assert m.proto.delta_description == "vs last week", label
        assert yoy in captions, label
    at.selectbox(key="week").select(date(2011, 12, 5)).run()
    assert not at.exception
    captions = [str(c.value) for c in at.caption]
    assert captions.count("— vs same week last year") == 3
