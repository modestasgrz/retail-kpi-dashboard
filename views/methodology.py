import streamlit as st

st.title("Methodology & data")
with st.container(key="prose"):
    st.markdown(
        """
Every number in this app is computed in code from the transaction lines of a real online retailer, then checked by tests (including hand-calculated cases). **All figures come from real public data; nothing in this app is synthetic.**

### Gross and net

Net revenue is revenue minus cancelled value; it is the headline figure on every page. Gross revenue (before cancellations) is shown next to it. A cancellation counts in the week it was made, not in the week of the original order.

### KPIs (per ISO week, Monday–Sunday)

| Card | Formula |
| --- | --- |
| Net revenue | Gross revenue − Cancelled |
| Orders | count of distinct invoices over product lines |
| Avg order (net) | Net revenue / Orders |
| Gross revenue | sum(Quantity × Price) over product lines |
| Units | sum(Quantity) over product lines |
| Customers | count of distinct customer ids over product lines that have one |
| New customers | customers whose first product line in the whole dataset (from Dec 2009) falls in the week |
| Returning customers | Customers − New customers |
| Cancelled | −sum(Quantity × Price) over cancellation lines with a product code; its tooltip also shows the share of gross revenue and the cancellation rate (cancellation invoices / (orders + cancellation invoices)) |

Change vs last week = (this week − last week) / last week × 100, shown as n/a when last week is 0 or negative. Change vs same week last year compares with the week 52 weeks earlier (the same ISO week); it shows — when either week has no sales, the base week's value is zero or negative, or this week is partial. Totals over a range add the weekly values; customer counts aren't added across weeks because one customer can buy in many weeks.

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
| Revenue swing | revenue_swing | net revenue is ≥ 40.0% above or below its 4-week average |
| Orders swing | orders_swing | orders are ≥ 40.0% above or below their 4-week average |
| Large cancellations | large_cancellations | cancelled value ≥ 25% of gross revenue (leaving out a placed-and-cancelled order) |
| One big order | top_line | one product line is more than 25% of the week's gross revenue |
| Placed and cancelled | placed_cancelled | an order and its cancellation in the same week are more than 25% of the week's gross revenue |

The 4-week average is the mean of the previous 4 weeks that had sales. Swing flags skip a week with no sales and the week right after one, since there is nothing fair to compare with. The 40% threshold leaves 9 flagged weeks in the full year for all countries, so each flag is worth a look.

**Drivers.** Each swing flag lists its top 3 drivers. The contribution of a product or country = its value this week − its average over the same base weeks (0 when it had no sales), so all contributions add up to the whole change. Shown are the 3 largest in the direction of the swing, and how much of the change they explain. Revenue swings are split by product and, for all countries or outside the UK, by country; orders swings by country only, because one order can hold many products.

**Placed and cancelled.** An order line and a cancellation line match when they have the same week, same stock code, same customer and same price; the matched value is the smaller of the two quantities × the price. Customer ids are only used while building the tables and never leave that step. Limits: a cancellation in a later week is not matched; lines without a customer id never match; an order cancelled at a different price does not match.

### Country filter

"All countries", "United Kingdom", "Outside UK" (every country except the UK) or one country. Customer counts are distinct within the filter. A new customer is new to the whole shop, not only to that country.

### Weekly summaries

The Overview keeps, for all countries only, a weekly summary written by AI in an earlier offline run of a separate reporting tool, in a labelled expander. Every figure in those summaries was checked against the computed numbers at the time. The headline at the top of the Overview is computed from the numbers, not written by AI. This app makes no AI calls and no network calls.

### Data

Online Retail II (Chen, D. (2012)), UCI Machine Learning Repository, https://doi.org/10.24432/C5CG6D, licensed CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). A UK-based online retailer of giftware, many of whose customers are wholesalers; transactions from 2009-12-01 to 2011-12-09. This app shows the 53 ISO weeks from 2010-12-06 to 2011-12-11; the year before is used only as a comparison base. The raw file is downloaded and checked by a script; only weekly aggregates without customer ids are stored with the app.

### With your data

On your own shop data the same dashboard can add margin, stock and targets, send a Monday email with the week's numbers and flags, and connect directly to your shop or ERP.

### Known limits

- Cancellations count in the week they happen, so a week can show a cancellation of an order placed weeks before.
- Wholesale and retail buyers are mixed, so the average order value blends both.
- Many lines have no customer id; customer counts only include lines that have one.
"""
    )
