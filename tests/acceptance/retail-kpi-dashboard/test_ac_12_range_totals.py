"""AC-12 — Given fixture F built and range 2011-09-12..2011-09-19, All countries, then totals are revenue 283.00, orders 7, units 85, cancelled value 25.00, revenue after cancellations 258.00, weeks 2, flagged weeks 2."""

from pathlib import Path

import pytest
from fixture import W1, built, scenario


def test_ac_12_range_totals(tmp_path: Path) -> None:
    t = scenario(built(tmp_path), start=W1).totals
    assert t.revenue == pytest.approx(283.0)
    assert t.orders == 7
    assert t.units == 85
    assert t.cancelled_value == pytest.approx(25.0)
    assert t.net_revenue == pytest.approx(258.0)
    assert t.weeks == 2
    assert t.flagged_weeks == 2
