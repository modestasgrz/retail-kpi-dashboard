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
| W1 | top_line | largest line 40 / 80 = 50.0% > 25% | One line is 50.0% of revenue: MUG RED, £40 (invoice 500002) |
| W2 | revenue_swing | +153.8% ≥ 25 | Revenue +153.8% vs previous week (£203 vs £80) |
| W2 | orders_swing | +150.0% ≥ 25 | Orders +150.0% vs previous week (5 vs 2) |
| W2 | top_line | 60 / 203 = 29.56% > 25% | One line is 29.6% of revenue: MUG RED, £60 (invoice 500003) |
| W2 | (no large_cancellations) | 25 / 203 = 12.3% < 25% | |
| W2 | (no partial_week) | data ends Sunday 2011-09-25, the last day of W2 | |

Boundaries: a week with £100 revenue and £25.00 cancelled is flagged (25.0% ≥ 25%), £24.99 isn't. Four £10 lines (largest = exactly 25.0%) give no top_line flag (rule is strictly above 25%). `swing(24.94)` is False (rounds to 24.9), `swing(-24.96)` is True (rounds to −25.0).

## Range totals, W1..W2

Revenue 80 + 203 = 283.00, orders 2 + 5 = 7, units 35 + 50 = 85, cancelled 25.00, after cancellations 258.00, 2 weeks, both flagged.

## Real-data cross-check

The committed tables are also checked against an earlier, independently written implementation of the same rules (53-week run): week 2011-09-19 revenue £328 713, 463 orders, AOV £709.96, 383 customers (64 new); week 2011-12-05 revenue £483 725, 509 orders, £172 782 cancelled, £310 943 after cancellations (AC-14).
