import plotly.graph_objects as go
import plotly.io as pio

BG = "#0B1426"
SURFACE = "#13203A"
BORDER = "#22324F"
TEXT = "#E6ECF5"
MUTED = "#8B9AB4"
BLUE = "#3B82F6"
GREEN = "#22C55E"
AMBER = "#F59E0B"
RED = "#EF4444"
FONT = '"Inter", "Avenir Next", "Helvetica Neue", Arial, sans-serif'
NEW = "#d95926"
SERIES = [BLUE, NEW]

axis = {
    "gridcolor": BORDER,
    "linecolor": BORDER,
    "zeroline": False,
    "tickfont": {"color": MUTED, "size": 12},
    "title": {"font": {"color": MUTED, "size": 12}},
}
TEMPLATE = go.layout.Template(
    layout={
        "paper_bgcolor": SURFACE,
        "plot_bgcolor": SURFACE,
        "font": {"family": FONT, "color": TEXT, "size": 13},
        "colorway": SERIES,
        "xaxis": axis,
        "yaxis": axis,
        "hovermode": "x unified",
        "hoverlabel": {
            "bgcolor": BG,
            "bordercolor": BORDER,
            "font": {"color": TEXT, "family": FONT},
        },
        "legend": {"orientation": "h", "y": 1.12, "x": 0, "font": {"color": MUTED}},
        "margin": {"l": 56, "r": 16, "t": 48, "b": 40},
        "title": {"font": {"size": 15, "color": TEXT}, "x": 0, "xanchor": "left"},
        "bargap": 0.25,
        "barmode": "stack",
        "separators": ".\u202f",
    }
)
pio.templates["navy"] = TEMPLATE
pio.templates.default = "navy"
