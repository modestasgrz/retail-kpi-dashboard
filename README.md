# Retail KPI dashboard

A weekly KPI review for an online retailer, built in Streamlit on 53 weeks of real transactions (UCI Online Retail II, Dec 2010 – Dec 2011).

**The team task it replaces:** every Monday an ops manager pulls last week's sales into a spreadsheet: revenue, orders, average order value, cancellations, new vs returning customers, top products and countries, what changed and what looks odd. This app does that review in one place. Every number is computed in code, traceable to its formula and inputs, and the same on every page.

![Overview, week 2011-09-19](docs/screenshots/overview-week-2011-09-19-1440.png)

## What it does

| Page | What you see |
| --- | --- |
| Overview | The week's one-line summary under the title, a status pill ("● All clear" or "▲ 2 flags") with the flag details one click away, 3 large cards (revenue, orders, average order value) with a 12-week sparkline and 7 smaller ones, each with the change vs the previous week and a ? showing its formula and inputs. Top 5 products and countries with their share of the week, and the full saved summary in an expander |
| Trends | A 2×2 grid: revenue (with revenue after cancellations and flagged weeks marked), orders, returning and new customers, cancellation rate. The week with no sales is a gap, never a drop to 0, and the partial last week is drawn dotted with an open circle and a note on its cancellations |
| Flagged weeks | One card per flagged week with plain-English labels (No sales, Partial week, Revenue swing, Orders swing, Large cancellations, One big order) and each reason in full |
| Weekly table | The full weekly KPI table for the range with the Week column pinned, a Flags column, green and red changes, and a CSV download |
| Methodology & data | Every KPI formula, the cleaning rules, the flag rules, the data source, known limits, and what the dashboard can add on your own data |

The sidebar holds the filters, and every page recalculates from them: preset (Full year, Q4 2011, UK only, Outside UK), date range (snaps to whole ISO weeks), country (all, UK, outside UK or any single one of the 38 countries with sales in these weeks), week, and **Reset to Full year**. A bad input, such as a date range with only a start date, shows a plain error instead of numbers. Each data page has the same quiet range line under its title (range, revenue, orders, flagged weeks) and a "Data as of 2011-12-09" note, and a test checks the line matches on every page.

## How it works

```
UCI xlsx (downloaded, SHA-256 checked)
  ──► clean: each line gets one bucket: duplicate · cancellation · adjustment · non-product · non-positive · product
  ──► build: weekly KPI inputs per week × filter value (all / UK / outside UK / each country) + product revenue per week
            → data/derived/*.parquet (no customer ids; 2 MB, committed)
  ──► run_scenario(filters): one pure function computes every number the pages show (cached once per filter set)
  ──► 5 thin Streamlit pages
```

- **Calc core** (`kpi/`): Pydantic models and pure functions, no Streamlit imports. Pages only format and lay out what `run_scenario` returns.
- **Flags:** revenue or orders 40% or more above or below their 4-week average (the mean of the previous 4 weeks that had sales; skipped in a week with no sales and the week after one), cancelled value ≥ 25% of revenue, one line > 25% of revenue, no sales, partial week. The 40% threshold was tuned on this data: 25% would flag 21 weeks, 40% flags 9.
- **Numbers:** thousands use a narrow space (`£483 725`), never a comma; percentages and money round half-up; the CSV holds raw numbers for spreadsheets.
- **Weekly summaries:** for all countries, the Overview shows a short summary written by AI in an earlier offline run of a separate reporting tool, where every figure was checked against the computed numbers. This app makes no AI calls and no network calls at runtime.

## Results on the real data

Full year, all countries: revenue £10 066 085 over 19 349 orders, £472 377 cancelled. 9 of 53 weeks are flagged: 8 revenue swings, 3 order swings, 2 large-cancellation weeks, 2 one-big-order weeks, 1 week with no sales (2010-12-27) and 1 partial week (2011-12-05, data ends Friday 2011-12-09).

| Week | Revenue | What the dashboard shows |
| --- | --- | --- |
| 2011-11-28 (default, last full week) | £309 378 (+2.3%) | 663 orders, AOV £466.63, 514 customers (31 new), no flags |
| 2011-09-19 | £328 713 (+46.8%) | revenue swing: +83.0% vs its 4-week average (£179 625); top product Set Of Tea Coffee Sugar Tins Pantry |
| 2011-12-05 | £483 725 (+56.4%) | 4 flags: partial week (data ends 2011-12-09); revenue swing (+44.1% vs its 4-week average); £172 782 cancelled (35.7% of revenue); one line is 34.8% of revenue (PAPER CRAFT , LITTLE BIRDIE, £168 470). Revenue after cancellations £310 943 |

These weekly figures match an earlier, independently written implementation of the same rules on both check weeks (acceptance test AC-14).

## Measured

- 39 acceptance tests, one per acceptance criterion in `specs/retail-kpi-dashboard.md`. The core tests run on a 15-line fixture whose every value was worked out by hand first (`docs/test-cases.md`). The app tests run every page through Streamlit's `AppTest`: defaults, a preset moving the KPIs, Reset, the same KPI on every page, a bad date range, the week picker, help text, the summary label and expander, the flag status pill, the sparklines, chart gaps and the partial week, the grouped flagged page, the pinned weekly table, the CSV download, attribution, and no network use.
- 336 unit tests on the calc core: rounding boundaries, cleaning rules, country filters, the 4-week-average swing rule and its thresholds, CSV, and real-data invariants over all 40 filter values × 53 weeks. The invariants include revenue after cancellations = revenue − cancelled, UK + outside UK = all countries, and the sum of single countries = all countries.
- 150 app tests through `AppTest`: every preset, Custom and Reset, week fallback when the range changes, sparse countries on all 5 pages, every card's value, delta, help text and sparkline against the core, gaps in every chart for sparse countries, flag pills and groups, and the CSV download bytes against the core.
- Rebuilding `data/derived/` from the raw file gives byte-identical tables.

## Run it yourself

```bash
uv sync
make run                      # http://127.0.0.1:8780
```

The derived tables are committed, so the app runs without the raw file. To rebuild them:

```bash
uv run python -m kpi.build    # downloads data/raw/online_retail_II.xlsx (SHA-256 checked) if missing, ~30 s
```

Development: `make check` (ruff, mypy strict, security scans, unit tests) · `uv run pytest tests/acceptance` · `uv run python tools/screenshots.py` (with the app running) writes `docs/screenshots/`.

Streamlit Community Cloud: main file `app.py`, dependencies from `requirements.txt` (exported from `uv.lock` with `make requirements`), Python 3.12.

## Screenshots

| | 1280 px | 1440 px |
| --- | --- | --- |
| Overview (default week) | [overview-1280](docs/screenshots/overview-1280.png) | [overview-1440](docs/screenshots/overview-1440.png) |
| Overview, week 2011-09-19 | [1280](docs/screenshots/overview-week-2011-09-19-1280.png) | [1440](docs/screenshots/overview-week-2011-09-19-1440.png) |
| Overview, UK only | [1280](docs/screenshots/overview-uk-only-1280.png) | [1440](docs/screenshots/overview-uk-only-1440.png) |
| Trends | [1280](docs/screenshots/trends-1280.png) | [1440](docs/screenshots/trends-1440.png) |
| Flagged weeks | [1280](docs/screenshots/flags-1280.png) | [1440](docs/screenshots/flags-1440.png) |
| Weekly table | [1280](docs/screenshots/table-1280.png) | [1440](docs/screenshots/table-1440.png) |
| Methodology & data | [1280](docs/screenshots/methodology-1280.png) | [1440](docs/screenshots/methodology-1440.png) |

## Known limits

- Revenue is gross. Cancellations are shown next to it and flagged at 25% of revenue, not netted against the week of the original order.
- Wholesale and retail buyers are mixed, so the average order value blends both. The dataset has no margin or stock data.
- Many lines have no customer id, so customer counts include only lines that have one.
- The ±40% swing rule against the 4-week average is simple: it flags a week for a look; it doesn't judge it, and it doesn't know about seasons (the data has no prior year inside the window).
- Customer counts are not added up across weeks (one customer can buy in many weeks), so the range line shows revenue and orders only.

## Data

Data: Online Retail II (Chen, D., 2012), UCI Machine Learning Repository, https://doi.org/10.24432/C5CG6D, licensed CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).

The raw file is downloaded by a script and is not committed. Only weekly aggregates without customer ids are stored in this repo.
