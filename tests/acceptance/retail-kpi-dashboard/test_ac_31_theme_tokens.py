"""AC-31 — config.toml has base = "dark" and backgroundColor, secondaryBackgroundColor, primaryColor, textColor equal kpi.theme BG, SURFACE, BLUE, TEXT; kpi.kpi.theme.TEMPLATE is a Plotly template registered as "navy"."""

import tomllib

from fixture import REPO


def test_ac_31_theme_tokens() -> None:
    import kpi.theme
    import plotly.io as pio

    cfg = tomllib.loads((REPO / ".streamlit" / "config.toml").read_text())["theme"]
    assert cfg["base"] == "dark"
    assert cfg["backgroundColor"].lower() == kpi.theme.BG.lower()
    assert cfg["secondaryBackgroundColor"].lower() == kpi.theme.SURFACE.lower()
    assert cfg["primaryColor"].lower() == kpi.theme.BLUE.lower()
    assert cfg["textColor"].lower() == kpi.theme.TEXT.lower()
    assert (
        pio.templates["navy"] is kpi.theme.TEMPLATE
        or pio.templates["navy"] == kpi.theme.TEMPLATE
    )
