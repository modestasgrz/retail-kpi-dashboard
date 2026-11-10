import plotly.graph_objects as go
import plotly.io as pio

BG = "#0A0A0B"
SURFACE = "#111113"
SURFACE_2 = "#1C1C1F"
BORDER = "#26262A"
TEXT = "#EDEDEF"
MUTED = "#8A8A93"
PRIMARY = "#EDEDEF"
BLUE = "#3B82F6"
GREEN = "#22C55E"
AMBER = "#F59E0B"
RED = "#EF4444"
SLATE = "#9A9AA3"
GOOD = GREEN
BAD = RED
FONT = '-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", "Helvetica Neue", Arial, sans-serif'
RADIUS = "6px"
NEW = BLUE
RETURNING = SLATE
SERIES = [BLUE, RETURNING]
CSS_VARS = {
    "surface": SURFACE,
    "surface-2": SURFACE_2,
    "border": BORDER,
    "text": TEXT,
    "muted": MUTED,
    "font": FONT,
    "radius": RADIUS,
    "card-fill": "transparent",
}

axis = {
    "showgrid": True,
    "gridcolor": BORDER,
    "linecolor": BORDER,
    "zeroline": False,
    "tickfont": {"color": MUTED, "size": 12},
    "title": {"font": {"color": MUTED, "size": 12}},
}
TEMPLATE = go.layout.Template(
    layout={
        "paper_bgcolor": BG,
        "plot_bgcolor": BG,
        "font": {"family": FONT, "color": TEXT, "size": 13},
        "colorway": SERIES,
        "xaxis": {**axis, "showgrid": False},
        "yaxis": axis,
        "hovermode": "x unified",
        "hoverlabel": {
            "bgcolor": SURFACE_2,
            "bordercolor": BORDER,
            "font": {"color": TEXT, "family": FONT},
        },
        "legend": {
            "bgcolor": "rgba(0,0,0,0)",
            "orientation": "h",
            "y": 1.02,
            "yanchor": "bottom",
            "x": 0,
            "xanchor": "left",
            "font": {"color": MUTED},
        },
        "margin": {"l": 56, "r": 16, "t": 30, "b": 40},
        "title": {"font": {"size": 15, "color": TEXT}, "x": 0, "xanchor": "left"},
        "bargap": 0.15,
        "barmode": "stack",
        "separators": ". ",
    }
)
pio.templates["graphite_dark"] = TEMPLATE
pio.templates.default = "graphite_dark"
