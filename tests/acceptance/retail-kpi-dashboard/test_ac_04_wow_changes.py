"""AC-04 — Given fixture F built and week 2011-09-19 selected (All countries), then revenue WoW change is 153.75 ("+153.8%") and orders change is 150.0 ("+150.0%"); given week 2011-09-12 selected, revenue change is None ("n/a") because W0 has no sales."""

from pathlib import Path

import pytest
from fixture import W1, built, scenario


def test_ac_04_wow_changes(tmp_path: Path) -> None:
    from kpi.fmt import change

    out = built(tmp_path)
    w2 = scenario(out).selected
    assert w2.revenue_wow == pytest.approx(153.75)
    assert change(w2.revenue_wow) == "+153.8%"
    assert w2.orders_wow == pytest.approx(150.0)
    assert change(w2.orders_wow) == "+150.0%"
    w1 = scenario(out, week=W1).selected
    assert w1.revenue_wow is None
    assert change(w1.revenue_wow) == "n/a"
