"""AC-45 — Given fixture F plus the AC-33 line, when week 2011-09-19 is read (All countries), then the `revenue_swing` flag has drivers by "product" = [("Mug Blue", 58.0), ("Lamp", 50.0), ("Mug Red", 29.0)] with `explained_pct` 100.0 and by "country" = [("United Kingdom", 132.0), ("France", 5.0)] with 100.0; the `orders_swing` flag has drivers by "country" = [("United Kingdom", 3.0), ("France", 0.5)] with 100.0 and none by product; with country "United Kingdom" the `revenue_swing` flag has drivers by "product" only and the `orders_swing` flag has no drivers."""

from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from fixture import UK, W2, built, week_row

EXTRA = [("500100", "20001", "MUG RED", 1, datetime(2011, 8, 30, 10), 2.00, 90001, UK)]


def drivers(flag: Any) -> dict[str, tuple[list[tuple[str, float]], float | None]]:
    return {
        d.by: ([(i.label, i.change) for i in d.items], d.explained_pct)
        for d in flag.drivers
    }


def flag(row: Any, rule: str) -> Any:
    return next(f for f in row.flags if f.rule == rule)


def test_ac_45_swing_drivers(tmp_path: Path) -> None:
    data = built(tmp_path, EXTRA)
    w = week_row(data, W2)
    revenue = drivers(flag(w, "revenue_swing"))
    assert set(revenue) == {"product", "country"}
    items, explained = revenue["product"]
    assert [label for label, _ in items] == ["Mug Blue", "Lamp", "Mug Red"]
    assert [c for _, c in items] == pytest.approx([58.0, 50.0, 29.0])
    assert explained == pytest.approx(100.0)
    items, explained = revenue["country"]
    assert [label for label, _ in items] == ["United Kingdom", "France"]
    assert [c for _, c in items] == pytest.approx([132.0, 5.0])
    assert explained == pytest.approx(100.0)
    orders = drivers(flag(w, "orders_swing"))
    assert set(orders) == {"country"}
    items, explained = orders["country"]
    assert [label for label, _ in items] == ["United Kingdom", "France"]
    assert [c for _, c in items] == pytest.approx([3.0, 0.5])
    assert explained == pytest.approx(100.0)
    uk = week_row(data, W2, country=UK)
    assert set(drivers(flag(uk, "revenue_swing"))) == {"product"}
    assert flag(uk, "orders_swing").drivers == []
