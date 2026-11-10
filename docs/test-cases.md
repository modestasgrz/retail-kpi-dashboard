# Hand-calculated test cases

Fixture F (spec DEC-17, `tests/acceptance/retail-kpi-dashboard/fixture.py`) is 15 raw lines across three ISO weeks: W0 = 2011-09-05 (no lines), W1 = 2011-09-12, W2 = 2011-09-19, plus one 2010 line that only sets a customer's first purchase. Every value below was worked out by hand before the code existed. The acceptance tests assert exactly these numbers.

## Cleaning (week W2)

| Line | Rule hit | Bucket |
| --- | --- | --- |
| 500004 repeated, identical in all 8 columns | exact duplicate of an earlier line | duplicate |
| C500007 LAMP −1 | invoice starts with C | cancellation |
| A500008 "Adjust bad debt" | invoice starts with A (checked before the stock code) | adjustment |
| 500009 POST | stock code isn't 5 digits + letters | non_product |
| 500010 MUG RED price 0.00 | price ≤ 0 | non_positive |
| 500003 ×2, 500004, 500005, 500006, 500011 | none | product (6 lines) |

## Week W2, All countries

| KPI | Working | Value |
| --- | --- | --- |
| Revenue | 30×2.00 + 2×25.00 + 10×4.00 + 1×25.00 + 5×4.00 + 2×4.00 = 60 + 50 + 40 + 25 + 20 + 8 | 203.00 |
| Orders | distinct invoices 500003, 500004, 500005, 500006, 500011 | 5 |
| Average order value | 203 / 5 | 40.60 |
| Units | 30 + 2 + 10 + 1 + 5 + 2 | 50 |
| Customers | 90002, 90004, 90001 (500006 has no id; 90004 bought in UK and France, counted once) | 3 |
| New customers | 90002 (first line 2011-09-20) and 90004 (first line 2011-09-21) | 2 |
| Returning customers | 3 − 2 (90001 first bought 2011-09-13) | 1 |
| Cancellation rate | 1 cancellation invoice / (5 orders + 1) × 100 = 16.666… | 16.7% |
| Cancelled value | −(−1 × 25.00) | 25.00 |
| Revenue after cancellations | 203 − 25 | 178.00 |
| Lines without customer id | 500006 | 1 |

## Week-over-week (W2 vs W1)

W1 = 10×2 + 5×4 + 20×2 = 80.00 revenue, 2 orders (500001, 500002), 35 units.

| KPI | Working | Value | Display |
| --- | --- | --- | --- |
| Revenue change | (203 − 80) / 80 × 100 | 153.75 | +153.8% (half-up) |
| Orders change | (5 − 2) / 2 × 100 | 150.0 | +150.0% |
| W1 revenue change | base W0 = 0 → no change | None | n/a |

## Country filters, week W2

| Filter | Lines | Revenue | Orders | Customers | Other |
| --- | --- | --- | --- | --- | --- |
| United Kingdom | 60 + 50 + 40 + 20 + 8 | 178.00 | 4 | 3 | cancellation rate 1 / (4 + 1) = 20.0% |
| France | 25 | 25.00 | 1 | 1 | new customers 1 (90004 first bought this week) |
| Outside UK | France only | 25.00 | 1 | 1 | |

## Top lists, week W2

Products: LAMP 50 + 25 = 75, MUG BLUE 40 + 20 + 8 = 68, MUG RED 60. Countries: United Kingdom 178, France 25.

## Flags

| Week | Rule | Working | Reason |
| --- | --- | --- | --- |
| W0 | no_data | 0 product lines | No sales lines this week |
| W1 | top_line | largest line 40 / 80 = 50.0% > 25% | One line is 50.0% of revenue: Mug Red, £40 (invoice 500002) |
| W2 | revenue_swing | on net revenue (round 3): W2 net = 203 − 25 = £178; 4-week average = £80 (W1 is the only one of the 4 previous weeks with sales, no cancellations); +122.5% ≥ 40 | Net revenue +122.5% vs 4-week average (£178 vs £80) |
| W2 | orders_swing | 4-week average = 2 orders; +150.0% ≥ 40 | Orders +150.0% vs 4-week average (5 vs 2.0) (base < 10 keeps 1 decimal) |
| W2 | top_line | 60 / 203 = 29.56% > 25% | One line is 29.6% of revenue: Mug Red, £60 (invoice 500003) |
| W2 | (no large_cancellations) | 25 / 203 = 12.3% < 25% | |
| W2 | (no partial_week) | data ends Sunday 2011-09-25, the last day of W2 | |

Boundaries: a week with £100 revenue and £25.00 cancelled is flagged (25.0% ≥ 25%), £24.99 isn't. Four £10 lines (largest = exactly 25.0%) give no top_line flag (rule is strictly above 25%). `swing(39.94)` is False (rounds to 39.9), `swing(-39.96)` is True (rounds to −40.0).

Add one £2 line on 2011-08-30 (AC-33): the 4 weeks before W2 with sales are W1 (£80, 2 orders) and 2011-08-29 (£2, 1 order), so the 4-week average is £41 and 1.5 orders. Net revenue (178 − 41) / 41 = +334.1%, reason "Net revenue +334.1% vs 4-week average (£178 vs £41)"; orders (5 − 1.5) / 1.5 = +233.3%, reason "Orders +233.3% vs 4-week average (5 vs 1.5)".

## Round 3: net revenue, year over year, placed and cancelled, drivers

Net AOV, W2: net £178 / 5 orders = £35.60. Net change vs W1: (178 − 80) / 80 = +122.5%.

Year over year (AC-43). Add one line 400100, MUG RED × 30 at £2.00 on 2010-09-21 (customer 90005, UK). Its week 2010-09-20 is 2011-09-19 − 364 days. Base: net £60, 1 order, net AOV £60. W2: net (178 − 60) / 60 = +196.7%; orders (5 − 1) / 1 = +400.0%; net AOV (35.60 − 60) / 60 = −40.7%. W1's base week 2010-09-13 has no sales, so all three are None. Headline (AC-46): "Net revenue £178, +122.5% vs last week, +196.7% vs same week last year; 3 flags." (revenue swing, orders swing, one big order).

Placed and cancelled (AC-44). Add C500012, MUG RED × −30 at £2.00 on 2011-09-21, customer 90002, UK.
- Pairs in W2, matched on stock code, customer and price:
  - Mug Red (90002, £2): placed 30, cancelled 30, matched £60.
  - Lamp (90002, £25): placed 2, cancelled 1, matched £25.
- Matched total £85. Cancelled value 25 + 60 = £85, so net = 203 − 85 = £118.
- Largest pair: £60 / £203 = 29.6% > 25%, so `placed_cancelled` fires: "Placed and cancelled: £60, net £0 (Mug Red, invoice 500003)".
- `top_line` is not raised: its line (invoice 500003, Mug Red) is the matched pair.
- `large_cancellations` uses (85 − 85) / 203 = 0%, so it is not raised.
- Revenue swing: (118 − 80) / 80 = +47.5%. Orders swing unchanged.

Drivers (AC-45, fixture + the AC-33 line). Base weeks are W1 and 2011-08-29; each contribution = this week − mean of the two.

| By | Item | W2 | W1 | 08-29 | Mean | Contribution |
| --- | --- | --- | --- | --- | --- | --- |
| product (net £) | Mug Blue | 40 + 20 + 8 = 68 | 20 | 0 | 10 | +58 |
| product (net £) | Lamp | 50 + 25 − 25 = 50 | 0 | 0 | 0 | +50 |
| product (net £) | Mug Red | 60 | 20 + 40 = 60 | 2 | 31 | +29 |
| country (net £) | United Kingdom | 153 | 40 | 2 | 21 | +132 |
| country (net £) | France | 25 | 40 | 0 | 20 | +5 |
| country (orders) | United Kingdom | 4 | 1 | 1 | 1 | +3 |
| country (orders) | France | 1 | 1 | 0 | 0.5 | +0.5 |

Product contributions add up to 58 + 50 + 29 = 137 = 178 − 41, the total net change. Each driver list therefore explains 100.0% of the change.

## Range totals, W1..W2

Revenue 80 + 203 = 283.00, orders 2 + 5 = 7, units 35 + 50 = 85, cancelled 25.00, after cancellations 258.00, 2 weeks, both flagged.

## Real-data cross-check

The committed tables are also checked against an earlier, independently written implementation of the same rules (53-week run): week 2011-09-19 revenue £328 713, 463 orders, AOV £709.96, 383 customers (64 new); week 2011-12-05 revenue £483 725, 509 orders, £172 782 cancelled, £310 943 after cancellations (AC-14). Round 3 (AC-47, from a separate prototype on the raw data): week 2011-11-28 net £306 112, −0.9% vs 2010-11-29 (£309 009); 2011-09-19 net +82.0% vs its 4-week average £175 656, top 3 products explain 11.5% of the +£144 090 change, top 3 countries 90.3%; the two placed-and-cancelled orders are invoice 541431 (£77 184, 2011-01-17) and 581483 (£168 470, 2011-12-05).
