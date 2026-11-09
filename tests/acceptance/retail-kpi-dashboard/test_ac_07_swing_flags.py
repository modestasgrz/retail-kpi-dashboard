"""AC-07 — Given fixture F built, week 2011-09-19 (All countries) has revenue_swing "Revenue +153.8% vs previous week (£203 vs £80)" and orders_swing "Orders +150.0% vs previous week (5 vs 2)"; swing(24.94) False, swing(-24.96) True, swing(25.0) True, swing(None) False."""

from pathlib import Path

from fixture import built, reasons, scenario


def test_ac_07_swing_flags(tmp_path: Path) -> None:
    from kpi.core import swing

    got = reasons(scenario(built(tmp_path)).selected)
    assert got["revenue_swing"] == "Revenue +153.8% vs previous week (£203 vs £80)"
    assert got["orders_swing"] == "Orders +150.0% vs previous week (5 vs 2)"
    assert swing(24.94) is False
    assert swing(-24.96) is True
    assert swing(25.0) is True
    assert swing(None) is False
