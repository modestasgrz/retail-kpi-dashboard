"""AC-05 — Given fixture F built and week 2011-09-19: United Kingdom revenue 178.00, orders 4, customers 3, cancellation rate 20.0; France revenue 25.00, orders 1, customers 1, new 1; Outside UK revenue 25.00; All countries counts customer 90004 (UK + France) once (customers 3)."""

from pathlib import Path

import pytest
from fixture import UK, W2, built, week_row


def test_ac_05_country_filters(tmp_path: Path) -> None:
    out = built(tmp_path)
    uk = week_row(out, W2, UK)
    assert (uk.revenue, uk.orders, uk.customers) == (pytest.approx(178.0), 4, 3)
    assert uk.cancellation_rate == pytest.approx(20.0)
    fr = week_row(out, W2, "France")
    assert (fr.revenue, fr.orders, fr.customers, fr.new_customers) == (
        pytest.approx(25.0),
        1,
        1,
        1,
    )
    assert week_row(out, W2, "Outside UK").revenue == pytest.approx(25.0)
    assert week_row(out, W2).customers == 3
