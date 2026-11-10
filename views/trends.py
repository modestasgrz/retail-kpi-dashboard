import plotly.graph_objects as go
import streamlit as st
from plotly.basedatatypes import BaseTraceType

from kpi.fmt import money, pct
from kpi.models import FLAG_LABELS
from kpi.theme import AMBER, BLUE, MUTED, NEW, RETURNING, TEXT
from views.ui import header, strip

s = header("Trends")
full_weeks = [
    w
    for w in s.weeks
    if w.product_lines > 0 and not any(f.rule == "partial_week" for f in w.flags)
]
full = [w in full_weeks for w in s.weeks]
sel = s.selected
if not full_weeks:
    now = "No full week with sales in this range."
elif sel in full_weeks:
    rank = 1 + sum(w.net_revenue > sel.net_revenue for w in full_weeks)
    suffix = (
        "th"
        if rank % 100 in (11, 12, 13)
        else {1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th")
    )
    now = f"Week {sel.week_start}: net revenue {money(sel.net_revenue)}, the {rank}{suffix} highest of {len(full_weeks)} full week{'s' if len(full_weeks) > 1 else ''} in range."
else:
    high = max(full_weeks, key=lambda w: w.net_revenue)
    state = (
        "had no sales" if sel.product_lines == 0 else "is partial, so it isn't ranked"
    )
    now = f"Week {sel.week_start} {state}; highest full week {high.week_start} ({money(high.net_revenue)})."
strip(
    "Is the selected week part of a trend or a one-off?",
    now,
    "Switch Net / Gross to see what cancellations took out; amber diamonds are flagged weeks.",
)
measure = (
    st.segmented_control(
        "Revenue",
        ["Net", "Gross"],
        key="measure",
        default="Net",
        help="Choose which revenue to plot: after or before cancellations. Net = revenue minus cancelled value (the headline figure); gross = before cancellations. Gaps are weeks with no sales; the grey open circle is the partial last week and does not stretch the axis; the solid vertical line marks the selected week; amber diamonds mark flagged weeks.",
    )
    or "Net"
)
key = "net_revenue" if measure == "Net" else "revenue"
x = [w.week_start for w in s.weeks]
values = [getattr(w, key) for w in s.weeks]
sold = [w.product_lines > 0 for w in s.weeks]
partial = next(
    (
        i
        for i, w in enumerate(s.weeks)
        if any(f.rule == "partial_week" for f in w.flags)
    ),
    None,
)
marked = [bool(w.flags) and ok for w, ok in zip(s.weeks, full, strict=True)]
shown_full = [v for v, ok in zip(values, full, strict=True) if ok]
top = 1.08 * max(shown_full, default=0.0)
bottom = 1.08 * min([0.0, *shown_full])
clipped = partial is not None and top > 0 and values[partial] > top


def chart(
    title: str,
    traces: list[BaseTraceType],
    money_axis: bool,
    notes: list[dict[str, object]],
    y_range: list[float] | None = None,
) -> None:
    st.markdown(f"**{title}**")
    fig = go.Figure(traces)
    fig.add_vline(x=s.filters.week, line={"color": TEXT, "width": 1}, opacity=0.5)
    fig.add_annotation(
        x=s.filters.week,
        y=1,
        yref="paper",
        yanchor="bottom",
        text="Selected week",
        showarrow=False,
        font={"color": MUTED, "size": 11},
    )
    fig.update_layout(
        height=330,
        yaxis={"rangemode": "tozero"}
        | ({"tickprefix": "£", "tickformat": "~s"} if money_axis else {})
        | ({"range": y_range} if y_range else {}),
    )
    for note in notes:
        fig.add_annotation(note)
    st.plotly_chart(fig, theme=None, width="stretch")


revenue: list[BaseTraceType] = [
    go.Scatter(
        x=x,
        y=[v if ok else None for v, ok in zip(values, full, strict=True)],
        name=f"{measure} revenue",
        mode="lines+markers",
        line={"color": BLUE, "width": 2},
        marker={"size": 4},
        hovertemplate="£%{y:,.0f}",
        connectgaps=False,
    )
]
notes: list[dict[str, object]] = []
if partial is not None and s.weeks[partial].revenue > 0:
    p = s.weeks[partial]
    joined = {partial} | ({partial - 1} if partial > 0 and full[partial - 1] else set())
    revenue.append(
        go.Scatter(
            x=x,
            y=[
                (min(v, top) if clipped else v) if i in joined else None
                for i, v in enumerate(values)
            ],
            customdata=values,
            name="Partial week",
            showlegend=False,
            mode="lines+markers",
            line={"color": MUTED, "width": 2, "dash": "dot"},
            marker={
                "symbol": "circle-open",
                "size": [11 if i == partial else 0 for i in range(len(x))],
                "color": MUTED,
                "line": {"width": 2},
            },
            hovertemplate="£%{customdata:,.0f} (partial)",
            cliponaxis=False,
        )
    )
    notes.append(
        {
            "x": p.week_start,
            "y": top if clipped else values[partial],
            "text": f"Partial · {pct(100 * p.cancelled_value / p.revenue)} cancelled",
            "showarrow": True,
            "arrowcolor": MUTED,
            "ax": -40,
            "ay": 36 if clipped else -36,
            "xanchor": "right",
            "font": {"color": MUTED, "size": 12},
        }
    )
revenue.append(
    go.Scatter(
        x=x,
        y=[v if m else None for v, m in zip(values, marked, strict=True)],
        name="Flagged week",
        mode="markers",
        marker={"color": AMBER, "size": 9, "symbol": "diamond"},
        customdata=[", ".join(FLAG_LABELS[f.rule] for f in w.flags) for w in s.weeks],
        hovertemplate="%{customdata}",
    )
)
top_left, top_right = st.columns(2)
bottom_left, bottom_right = st.columns(2)
with top_left:
    chart(
        f"{measure} revenue per week",
        revenue,
        True,
        notes,
        [bottom, top] if top > 0 else None,
    )
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
        "Cancelled value per week",
        [
            go.Scatter(
                x=x,
                y=[
                    w.cancelled_value if ok else None
                    for w, ok in zip(s.weeks, sold, strict=True)
                ],
                name="Cancelled",
                mode="lines+markers",
                line={"color": BLUE, "width": 2},
                marker={"size": 4},
                hovertemplate="£%{y:,.0f}",
                connectgaps=False,
            )
        ],
        True,
        [],
    )
