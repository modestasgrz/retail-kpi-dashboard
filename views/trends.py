import plotly.graph_objects as go
import streamlit as st
from plotly.basedatatypes import BaseTraceType

from kpi.fmt import money
from kpi.theme import AMBER, MUTED, SERIES
from views.ui import header

s = header("Trends")
x = [w.week_start for w in s.weeks]
flagged = [w for w in s.weeks if w.flags]


def chart(title: str, traces: list[BaseTraceType], fmt: str) -> None:
    fig = go.Figure(traces)
    fig.add_vline(x=s.filters.week, line={"color": MUTED, "width": 1, "dash": "dot"})
    fig.update_layout(
        title=title, height=320, yaxis={"tickformat": fmt, "rangemode": "tozero"}
    )
    st.plotly_chart(fig, theme=None, width="stretch")


chart(
    "Revenue per week (£)",
    [
        go.Scatter(
            x=x,
            y=[w.revenue for w in s.weeks],
            name="Revenue",
            line={"color": SERIES[0], "width": 2},
            hovertemplate="£%{y:,.0f}",
        ),
        go.Scatter(
            x=x,
            y=[w.net_revenue for w in s.weeks],
            name="After cancellations",
            line={"color": MUTED, "width": 2, "dash": "dash"},
            hovertemplate="£%{y:,.0f}",
        ),
        go.Scatter(
            x=[w.week_start for w in flagged],
            y=[w.revenue for w in flagged],
            name="Flagged week",
            mode="markers",
            marker={"color": AMBER, "size": 9, "symbol": "diamond"},
            customdata=[
                ", ".join(f.rule.replace("_", " ") for f in w.flags) for w in flagged
            ],
            hovertemplate="%{customdata}",
        ),
    ],
    ",.0f",
)
left, right = st.columns(2)
with left:
    chart(
        "Orders per week",
        [
            go.Bar(
                x=x,
                y=[w.orders for w in s.weeks],
                name="Orders",
                marker={"color": SERIES[0]},
            )
        ],
        ",.0f",
    )
    chart(
        "Cancellation rate (%)",
        [
            go.Scatter(
                x=x,
                y=[w.cancellation_rate for w in s.weeks],
                name="Cancellation rate",
                line={"color": SERIES[0], "width": 2},
                hovertemplate="%{y:.1f}%",
                connectgaps=False,
            )
        ],
        ".0f",
    )
with right:
    chart(
        "Customers per week: new vs returning",
        [
            go.Bar(
                x=x,
                y=[w.returning_customers for w in s.weeks],
                name="Returning",
                marker={"color": SERIES[0]},
            ),
            go.Bar(
                x=x,
                y=[w.new_customers for w in s.weeks],
                name="New",
                marker={"color": SERIES[1]},
            ),
        ],
        ",.0f",
    )
    st.caption(
        f"Range revenue {money(s.totals.revenue)}, of which {money(s.totals.cancelled_value)} was cancelled. The dotted line marks the selected week; amber diamonds mark flagged weeks."
    )
