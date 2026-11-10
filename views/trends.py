import plotly.graph_objects as go
import streamlit as st
from plotly.basedatatypes import BaseTraceType

from kpi.fmt import money, pct
from kpi.models import FLAG_LABELS
from kpi.theme import AMBER, BLUE, MUTED, NEW, RETURNING
from views.ui import header

s = header("Trends")
x = [w.week_start for w in s.weeks]
sold = [w.product_lines > 0 for w in s.weeks]
partial = next(
    (
        i
        for i, w in enumerate(s.weeks)
        if any(f.rule == "partial_week" for f in w.flags)
    ),
    None,
)
full = [ok and i != partial for i, ok in enumerate(sold)]
flagged = [
    w for i, w in enumerate(s.weeks) if w.flags and w.product_lines > 0 and i != partial
]


def chart(
    title: str,
    traces: list[BaseTraceType],
    money_axis: bool,
    notes: list[dict[str, object]],
) -> None:
    fig = go.Figure(traces)
    fig.add_vline(x=s.filters.week, line={"color": MUTED, "width": 1, "dash": "dot"})
    fig.update_layout(
        title={"text": title, "yref": "container", "y": 0.97, "yanchor": "top"},
        height=360,
        margin={"t": 96},
        yaxis={"tickformat": "~s", "rangemode": "tozero"}
        | ({"tickprefix": "£"} if money_axis else {}),
    )
    for note in notes:
        fig.add_annotation(note)
    st.plotly_chart(fig, theme=None, width="stretch")


revenue = [
    go.Scatter(
        x=x,
        y=[w.revenue if ok else None for w, ok in zip(s.weeks, full, strict=True)],
        name="Revenue",
        line={"color": BLUE, "width": 2},
        hovertemplate="£%{y:,.0f}",
        connectgaps=False,
    ),
    go.Scatter(
        x=x,
        y=[w.net_revenue if ok else None for w, ok in zip(s.weeks, full, strict=True)],
        name="After cancellations",
        line={"color": MUTED, "width": 2, "dash": "dash"},
        hovertemplate="£%{y:,.0f}",
        connectgaps=False,
    ),
]
notes: list[dict[str, object]] = []
if partial is not None and s.weeks[partial].revenue > 0:
    p = s.weeks[partial]
    span = s.weeks[max(partial - 1, 0) : partial + 1]
    revenue.append(
        go.Scatter(
            x=[w.week_start for w in span],
            y=[w.revenue for w in span],
            name="Partial week",
            mode="lines+markers",
            line={"color": BLUE, "width": 2, "dash": "dot"},
            marker={
                "symbol": "circle-open",
                "size": [0] * (len(span) - 1) + [11],
                "color": BLUE,
                "line": {"width": 2},
            },
            hovertemplate="£%{y:,.0f} (partial)",
        )
    )
    notes.append(
        {
            "x": p.week_start,
            "y": p.revenue,
            "text": f"Partial week, {money(p.cancelled_value)} cancelled ({pct(100 * p.cancelled_value / p.revenue)})",
            "showarrow": True,
            "arrowcolor": MUTED,
            "ax": -40,
            "ay": -46,
            "xanchor": "right",
            "font": {"color": MUTED, "size": 12},
        }
    )
revenue.append(
    go.Scatter(
        x=[w.week_start for w in flagged],
        y=[w.revenue for w in flagged],
        name="Flagged week",
        mode="markers",
        marker={"color": AMBER, "size": 9, "symbol": "diamond"},
        customdata=[", ".join(FLAG_LABELS[f.rule] for f in w.flags) for w in flagged],
        hovertemplate="%{customdata}",
    )
)

top_left, top_right = st.columns(2)
bottom_left, bottom_right = st.columns(2)
with top_left:
    chart("Revenue per week", revenue, True, notes)
with top_right:
    chart(
        "Orders per week",
        [
            go.Bar(
                x=x,
                y=[
                    w.orders if ok else None
                    for w, ok in zip(s.weeks, sold, strict=True)
                ],
                name="Orders",
                marker={"color": BLUE},
            )
        ],
        False,
        [],
    )
with bottom_left:
    chart(
        "Customers per week: returning and new",
        [
            go.Bar(
                x=x,
                y=[
                    w.returning_customers if ok else None
                    for w, ok in zip(s.weeks, sold, strict=True)
                ],
                name="Returning",
                marker={"color": RETURNING},
            ),
            go.Bar(
                x=x,
                y=[
                    w.new_customers if ok else None
                    for w, ok in zip(s.weeks, sold, strict=True)
                ],
                name="New",
                marker={"color": NEW},
            ),
        ],
        False,
        [],
    )
with bottom_right:
    chart(
        "Cancellation rate (%)",
        [
            go.Scatter(
                x=x,
                y=[
                    w.cancellation_rate if ok else None
                    for w, ok in zip(s.weeks, sold, strict=True)
                ],
                name="Cancellation rate",
                line={"color": BLUE, "width": 2},
                hovertemplate="%{y:.1f}%",
                connectgaps=False,
            )
        ],
        False,
        [],
    )
st.caption(
    f"Range revenue {money(s.totals.revenue)}; cancellations in range {money(s.totals.cancelled_value)}. Gaps are weeks with no sales; the dotted segment with the open circle is the partial last week. The dotted vertical line marks the selected week; amber diamonds mark flagged weeks."
)
