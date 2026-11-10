import streamlit as st

st.title("Methodology & data")
st.markdown(
    """
Every number in this app is computed in code from the transaction lines of a real online retailer, then checked by tests (including hand-calculated cases). **All figures come from real public data; nothing in this app is synthetic.**

### KPIs (per ISO week, Monday–Sunday)

| KPI | Formula |
| --- | --- |
| Revenue | sum(Quantity × Price) over product lines |
| Orders | count of distinct invoices over product lines |
| Average order value | Revenue / Orders |
| Units | sum(Quantity) over product lines |
| Customers | count of distinct customer ids over product lines that have one |
| New customers | customers whose first product line in the whole dataset (from Dec 2009) falls in the week |
| Returning customers | Customers − New customers |
| Cancellation rate | cancellation invoices / (orders + cancellation invoices) × 100 |
| Cancelled value | −sum(Quantity × Price) over cancellation lines with a product code |
| Revenue after cancellations | Revenue − Cancelled value |

Change vs previous week = (this week − previous week) / previous week × 100, shown as n/a when the previous week is 0 or negative. The cancellation rate changes in percentage points (pp). Totals over a range add the weekly values; customer counts aren't added across weeks because one customer can buy in many weeks.

### Cleaning rules (each line gets the first rule it matches)

1. **Duplicate**: an exact copy of an earlier line (the source workbook's two sheets overlap).
2. **Cancellation**: invoice starts with "C".
3. **Adjustment**: invoice starts with "A".
4. **Non-product**: stock code isn't 5 digits plus optional letters (postage, fees, manual lines).
5. **Non-positive**: price or quantity ≤ 0.

Only the remaining **product lines** count towards revenue, orders, units and customers.

### Flag rules

| Flag | Rule | Fires when |
| --- | --- | --- |
| No sales | no_data | the week has no product lines |
| Partial week | partial_week | the data ends before the week's Sunday (2011-12-09) |
| Revenue swing | revenue_swing | revenue is ≥ 40.0% above or below its 4-week average |
| Orders swing | orders_swing | orders are ≥ 40.0% above or below their 4-week average |
| Large cancellations | large_cancellations | cancelled value ≥ 25% of revenue |
| One big order | top_line | one product line is more than 25% of the week's revenue |

The 4-week average is the mean of the previous 4 weeks that had sales. Swing flags skip a week with no sales and the week right after one, since there is nothing fair to compare with. The 40% threshold leaves 9 flagged weeks in the full year for all countries, so each flag is worth a look.

### Country filter

"All countries", "United Kingdom", "Outside UK" (every country except the UK) or one country. Customer counts are distinct within the filter. A new customer is new to the whole shop, not only to that country.

### Weekly summaries

The Overview shows, for all countries only, a weekly summary written by AI in an earlier offline run of a separate reporting tool. Every figure in those summaries was checked against the computed numbers at the time. This app makes no AI calls and no network calls.

### Data

Online Retail II (Chen, D. (2012)), UCI Machine Learning Repository, https://doi.org/10.24432/C5CG6D, licensed CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). A UK-based online retailer of giftware, many of whose customers are wholesalers; transactions from 2009-12-01 to 2011-12-09. This app shows the 53 ISO weeks from 2010-12-06 to 2011-12-11. The raw file is downloaded and checked by a script; only weekly aggregates without customer ids are stored with the app.

### With your data

On your own shop data the same dashboard can add margin, stock and targets, send a Monday email with the week's numbers and flags, and connect directly to your shop or ERP.

### Known limits

- Revenue is gross: cancellations are shown next to it, not netted against the week of the original order.
- Wholesale and retail buyers are mixed, so the average order value blends both.
- Many lines have no customer id; customer counts only include lines that have one.
"""
)
