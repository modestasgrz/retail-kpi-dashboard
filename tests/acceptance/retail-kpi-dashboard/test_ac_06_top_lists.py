"""AC-06 — Given fixture F built and week 2011-09-19, All countries, then top products are LAMP 75, MUG BLUE 68, MUG RED 60 in that order, and top countries are United Kingdom 178, France 25."""

from pathlib import Path

import pytest
from fixture import built, scenario


def test_ac_06_top_lists(tmp_path: Path) -> None:
    s = scenario(built(tmp_path))
    assert [(r.label, r.revenue) for r in s.top_products] == [
        ("LAMP", pytest.approx(75.0)),
        ("MUG BLUE", pytest.approx(68.0)),
        ("MUG RED", pytest.approx(60.0)),
    ]
    assert [(r.label, r.revenue) for r in s.top_countries] == [
        ("United Kingdom", pytest.approx(178.0)),
        ("France", pytest.approx(25.0)),
    ]
