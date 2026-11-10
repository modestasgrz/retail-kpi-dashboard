from datetime import timedelta
from html import escape

import streamlit as st

from kpi.fmt import count, grouped, money, pct, rounded
from kpi.models import FLAG_LABELS, Flag, Scenario

PLURAL = {"product": "products", "country": "countries"}


def header(title: str) -> Scenario:
    """Page title and the one-line range line shared by every data page (DEC-18)."""
    s: Scenario = st.session_state.scenario
    f, t = s.filters, s.totals
    st.title(title)
    with st.container(key="meta"):
        left, right = st.columns([4, 1], vertical_alignment="center")
        left.caption(
            f"Range {f.start} – {f.end + timedelta(days=6)} · net revenue {money(t.net_revenue)} · orders {count(t.orders)} · flagged weeks {count(t.flagged_weeks)}"
        )
        with right.container(key="asof"):
            st.caption(f":green[●] Data as of {s.data_end}")
    return s


def strip(question: str, now: str, do: str) -> None:
    """The 3-line reading strip under the range line (DEC-30): THE QUESTION, RIGHT NOW, DO THIS."""
    st.markdown(
        '<div class="how-to-read">'
        f"<div><b>THE QUESTION</b><span>{escape(question)}</span></div>"
        f'<div><b>RIGHT NOW</b><span class="now">{escape(now)}</span></div>'
        f"<div><b>DO THIS</b><span>{escape(do)}</span></div>"
        "</div>",
        unsafe_allow_html=True,
    )


def flag_line(flag: Flag, template: str) -> str:
    """One markdown list item: `template` with {label} and {reason}, or just "- reason" when the reason already starts with its label (Placed and cancelled); then one nested line per driver set (DEC-24), e.g. "Top products: Lamp +£50 · Mug Red +£29 (100.0% of the change)"."""
    label = FLAG_LABELS[flag.rule]
    lines = [
        f"- {flag.reason}"
        if flag.reason.startswith(f"{label}:")
        else template.format(label=label, reason=flag.reason)
    ]
    for d in flag.drivers:
        if not d.items:
            continue
        items = []
        for i in d.items:
            sign = "+" if i.change >= 0 else "-"
            if flag.rule == "revenue_swing":
                items.append(f"{i.label} {sign}{money(abs(i.change))}")
            else:
                n = rounded(abs(i.change), "0.1")
                n = n.to_integral_value() if n == n.to_integral_value() else n
                items.append(
                    f"{i.label} {sign}{grouped(n)} order{'' if n == 1 else 's'}"
                )
        lines.append(
            f"    - Top {PLURAL[d.by]}: {' · '.join(items)} ({pct(d.explained_pct)} of the change)"
        )
    return "\n".join(lines)
