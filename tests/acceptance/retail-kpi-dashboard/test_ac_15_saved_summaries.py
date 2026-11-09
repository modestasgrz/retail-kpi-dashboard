"""AC-15 — Given the committed data/derived/summaries.json, it has an entry for each of the 52 weeks with sales (2010-12-27 absent), no text contains a "[F" marker or a comma between digits, and week 2011-09-19's headline is "Revenue and orders jump to an unusually strong week, led by pantry products"."""

import json
import re
from datetime import date, timedelta

from fixture import REPO


def test_ac_15_saved_summaries() -> None:
    data = json.loads((REPO / "data" / "derived" / "summaries.json").read_text())
    weeks = {str(date(2010, 12, 6) + timedelta(days=7 * i)) for i in range(53)} - {
        "2010-12-27"
    }
    assert set(data) == weeks
    for entry in data.values():
        for text in (entry["headline"], entry["text"]):
            assert "[F" not in text
            assert not re.search(r"\d,\d", text)
        assert entry["text"].strip()
    assert (
        data["2011-09-19"]["headline"]
        == "Revenue and orders jump to an unusually strong week, led by pantry products"
    )
