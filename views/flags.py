from collections import Counter
from datetime import timedelta

import streamlit as st

from kpi.models import FLAG_LABELS
from views.ui import flag_line, header, strip

GRAY = {"no_data", "partial_week"}

s = header("Flagged weeks")
counts = Counter(f.rule for f in s.flags)
strip(
    "Which weeks need a look, and why?",
    f"{s.totals.flagged_weeks} of {s.totals.weeks} week{'s' if s.totals.weeks > 1 else ''} flagged: "
    + " · ".join(f"{FLAG_LABELS[rule]} {n}" for rule, n in counts.items())
    + "."
    if s.flags
    else "No week flagged in this range.",
    "Read each reason; for swings, the drivers show which products and countries moved."
    if counts.keys() & {"revenue_swing", "orders_swing"}
    else "Read each reason."
    if s.flags
    else "Widen the date range or pick another country in the sidebar.",
)
st.caption(
    "A flag asks for a look; it is not an error in the data.",
    help="Why weeks get flagged and how to read them. The rules and thresholds are on Methodology & data.",
)
if not s.flags:
    st.success(
        "No flagged weeks in the selected range.", icon=":material/check_circle:"
    )
else:
    with st.container(key="flags"):
        for w in reversed(s.weeks):
            if not w.flags:
                continue
            with st.container(border=True):
                st.markdown(
                    f"**{w.week_start} – {w.week_start + timedelta(days=6)}** "
                    + " ".join(
                        f":{'gray' if f.rule in GRAY else 'orange'}-badge[{FLAG_LABELS[f.rule]}]"
                        for f in w.flags
                    )
                )
                st.markdown(
                    "\n".join(flag_line(f, "- **{label}:** {reason}") for f in w.flags)
                )
