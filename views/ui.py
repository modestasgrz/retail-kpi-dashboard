from datetime import timedelta

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


def flag_line(flag: Flag, template: str) -> str:
    """One markdown list item: `template` with {label} and {reason}, or just "- reason" when the reason already starts with its label (Placed and cancelled); then the driver lines, nested."""
    label = FLAG_LABELS[flag.rule]
    head = (
        f"- {flag.reason}"
        if flag.reason.startswith(f"{label}:")
        else template.format(label=label, reason=flag.reason)
    )
    return head + "".join(f"\n    - {line}" for line in driver_lines(flag))


def driver_lines(flag: Flag) -> list[str]:
    """One line per driver set of a swing flag (DEC-24), e.g. "Top products: Lamp +£50 · Mug Red +£29 (100.0% of the change)"."""
    lines = []
    for d in flag.drivers:
        if not d.items:
            continue
        if flag.rule == "revenue_swing":
            items = [
                f"{i.label} {'+' if i.change >= 0 else ''}{money(i.change)}"
                for i in d.items
            ]
        else:
            items = []
            for i in d.items:
                n = rounded(abs(i.change), "0.1")
                n = n.to_integral_value() if n == n.to_integral_value() else n
                items.append(
                    f"{i.label} {'+' if i.change >= 0 else '-'}{grouped(n)} orders"
                )
        lines.append(
            f"Top {PLURAL[d.by]}: {' · '.join(items)} ({pct(d.explained_pct)} of the change)"
        )
    return lines
