"""AC-11 — Filters with start after end -> ValueError "Start week must be on or before end week."; a date before 2010-12-06 or after 2011-12-11 -> "Dates must be between 2010-12-06 and 2011-12-11."; week outside start..end -> "Selected week must be inside the date range."; run_scenario with an unknown country -> "Unknown country: Atlantis."."""

from datetime import date
from pathlib import Path

import pytest
from fixture import W0, W1, W2, built


def test_ac_11_invalid_filters(tmp_path: Path) -> None:
    from kpi.core import run_scenario
    from kpi.models import Filters

    with pytest.raises(ValueError, match="Start week must be on or before end week."):
        Filters(start=W2, end=W1, week=W2)
    with pytest.raises(
        ValueError, match="Dates must be between 2010-12-06 and 2011-12-11."
    ):
        Filters(start=date(2010, 11, 1), end=W2, week=W2)
    with pytest.raises(
        ValueError, match="Dates must be between 2010-12-06 and 2011-12-11."
    ):
        Filters(start=W2, end=date(2011, 12, 12), week=W2)
    with pytest.raises(
        ValueError, match="Selected week must be inside the date range."
    ):
        Filters(start=W1, end=W2, week=W0)
    with pytest.raises(ValueError, match="Unknown country: Atlantis."):
        run_scenario(
            Filters(start=W0, end=W2, country="Atlantis", week=W2), built(tmp_path)
        )
