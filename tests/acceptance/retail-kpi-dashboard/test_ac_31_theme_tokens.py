"""AC-31 — Given `.streamlit/config.toml` and `kpi/theme.py` (Graphite, DEC-16), then config has `base = "dark"`, its `backgroundColor`, `secondaryBackgroundColor`, `primaryColor`, `textColor` and `font` equal the tokens `BG`, `SURFACE`, `PRIMARY`, `TEXT` and `FONT`, `PRIMARY` is not `BLUE` (controls stay neutral so blue keeps its data meaning), and `kpi.theme.TEMPLATE` is a Plotly template registered as "graphite_dark"."""

import tomllib

import plotly.io as pio
from fixture import REPO


def test_ac_31_theme_tokens() -> None:
    import kpi.theme

    cfg = tomllib.loads((REPO / ".streamlit" / "config.toml").read_text())["theme"]
    assert cfg["base"] == "dark"
    assert cfg["backgroundColor"].lower() == kpi.theme.BG.lower()
    assert cfg["secondaryBackgroundColor"].lower() == kpi.theme.SURFACE.lower()
    primary: str = vars(kpi.theme)["PRIMARY"]
    assert cfg["primaryColor"].lower() == primary.lower()
    assert primary.lower() != kpi.theme.BLUE.lower()
    assert cfg["font"] == kpi.theme.FONT
    assert cfg["textColor"].lower() == kpi.theme.TEXT.lower()
    assert (
        pio.templates["graphite_dark"] is kpi.theme.TEMPLATE
        or pio.templates["graphite_dark"] == kpi.theme.TEMPLATE
    )
