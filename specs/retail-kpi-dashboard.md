# Retail KPI dashboard

Status: approved | Date: 2026-11-09 | Owner: Modestas

## Goal
An ops manager's Monday KPI review takes a spreadsheet pull and hand-typed figures. This Streamlit dashboard shows 53 weeks of a real online retailer's sales (UCI Online Retail II): weekly KPIs with week-over-week changes, trends, flagged weeks with their reason, and a CSV export. Every number is computed in code, traceable to its formula and inputs, and the same everywhere it appears.

## In scope
- Data build: download the raw UCI file (SHA-256 checked), clean it with the rules of DEC-04, write small derived tables without customer ids to `data/derived/` (committed with attribution).
- Calc core (no Streamlit imports): weekly KPIs per country filter, week-over-week changes, range totals, top 5 products and countries, flags with reasons, formula-and-inputs text per KPI, CSV export.
- Saved weekly summaries from an earlier offline run, shown read-only for All countries only, with the label in DEC-14.
- Streamlit app, 5 pages via `st.navigation`: Overview, Trends, Flagged weeks, Weekly table, Methodology & data.
- Shared sidebar: preset, date range, country, week, Reset.
- Dark navy theme in one theme file + `.streamlit/config.toml` + one CSS file + one Plotly template.
- Playwright screenshots at 1280 and 1440 px, README.

## Out of scope
- Any AI or network call at runtime; regenerating summaries.
- Deploying to Streamlit Community Cloud (prepared only; deploy is an owner step).
- Multi-select countries, custom flag thresholds, day-level date filtering (dates snap to ISO weeks).
- Margins, stock, returns other than cancellations (the dataset has none).
- Netting cancellations against the week of the original order.
- Customer-level views; customer ids never leave the build step.
- Login, user accounts, saving views.

## Acceptance criteria

Fixture F (hand-calculated, `docs/test-cases.md`): raw lines as in DEC-17. Weeks: W0 = 2011-09-05, W1 = 2011-09-12, W2 = 2011-09-19.

- **AC-01** — Given fixture F, when `build(raw, out_dir)` runs, then `out_dir` holds `weekly.parquet`, `products.parquet` and `meta.json`, no file has a column named `Customer ID`, and none of the fixture customer ids (90001–90004) appears as a value in any file.
- **AC-02** — Given fixture F built, when `run_scenario(Filters(start=2011-09-05, end=2011-09-19, country="All countries", week=2011-09-19), data_dir)` runs, then the selected week has revenue 203.00, orders 5, AOV 40.60, units 50, customers 3, new customers 2, returning customers 1, cancellation invoices 1, cancellation rate 16.666… (display "16.7%"), cancelled value 25.00, revenue after cancellations 178.00, product lines 6, lines without customer id 1.
- **AC-03** — Given fixture F built, when the week 2011-09-19 is read, then the data-quality counts are duplicate 1, cancellation 1, adjustment 1, non-product 1, non-positive 1, and none of those lines adds to revenue, orders or units.
- **AC-04** — Given fixture F built and week 2011-09-19 selected (All countries), then revenue week-over-week change is 153.75 (display "+153.8%") and orders change is 150.0 (display "+150.0%"); given week 2011-09-12 selected, revenue change is None (display "n/a") because W0 has no sales.
- **AC-05** — Given fixture F built and week 2011-09-19, when country is "United Kingdom", then revenue 178.00, orders 4, customers 3, cancellation rate 20.0; when "France", revenue 25.00, orders 1, customers 1, new customers 1; when "Outside UK", revenue 25.00; when "All countries", customer 90004 (UK + France) counts once (customers 3).
- **AC-06** — Given fixture F built and week 2011-09-19, All countries, then top products are LAMP £75, MUG BLUE £68, MUG RED £60 in that order, and top countries are United Kingdom £178, France £25.
- **AC-07** — Given fixture F built, then week 2011-09-19 (All countries) has flags `revenue_swing` with reason "Revenue +153.8% vs previous week (£203 vs £80)" and `orders_swing` with reason "Orders +150.0% vs previous week (5 vs 2)"; and `core.swing(24.94)` is False, `core.swing(-24.96)` is True, `core.swing(25.0)` is True, `core.swing(None)` is False (rule: |change rounded half-up to 0.1| ≥ 25.0).
- **AC-08** — Given a week with revenue 100.00 and cancelled value 25.00, when flags are computed, then it has `large_cancellations` with reason "£25 cancelled against £100 revenue (25.0%)"; with cancelled value 24.99 it has no such flag.
- **AC-09** — Given fixture F built, then week 2011-09-05 has exactly one flag, `no_data`, reason "No sales lines this week"; given fixture F plus one product line on 2011-12-07 12:00 (the last line of the data), week 2011-12-05 has `partial_week` with reason "Data ends 2011-12-07; the week is missing days", and week 2011-09-19 has no `partial_week` flag.
- **AC-10** — Given fixture F built, then week 2011-09-19 has `top_line` with reason "One line is 29.6% of revenue: MUG RED, £60 (invoice 500003)"; a week whose largest line is exactly 25.0% of revenue has no `top_line` flag.
- **AC-11** — Given any data dir, when `Filters` is built with start after end, then a `ValueError` is raised whose message contains "Start week must be on or before end week."; with a date before 2010-12-06 or after 2011-12-11: "Dates must be between 2010-12-06 and 2011-12-11."; with week outside start..end: "Selected week must be inside the date range."; and `run_scenario` with an unknown country raises `ValueError` containing "Unknown country: Atlantis.".
- **AC-12** — Given fixture F built and range 2011-09-12..2011-09-19, All countries, then totals are revenue 283.00, orders 7, units 85, cancelled value 25.00, revenue after cancellations 258.00, weeks 2, flagged weeks 2.
- **AC-13** — Given the formatters in `kpi.fmt`, then `money(483725.4)` = "£483 725", `money(0.5)` = "£1", `money2(950.336)` = "£950.34", `count(17225)` = "17 225", `pct(16.66667)` = "16.7%", `change(153.75)` = "+153.8%", `change(-23.15)` = "-23.2%", `change(0.0)` = "+0.0%", `change(None)` = "n/a", `points(-1.25)` = "-1.3 pp", where every thousands separator is U+202F.
- **AC-14** — Given the committed `data/derived/` tables, when `run_scenario` runs for All countries, then week 2011-09-19 shows revenue "£328 713", orders "463", AOV "£709.96", customers "383", new customers "64", cancellation rate "17.0%", cancelled value "£8 967", revenue after cancellations "£319 746", product lines 13 181, lines without customer id 2 517, revenue change "+46.8%"; and week 2011-12-05 shows revenue "£483 725", orders "509", AOV "£950.34", customers "415", new customers "17", cancellation rate "14.3%", cancelled value "£172 782", revenue after cancellations "£310 943", revenue change "+56.4%", orders change "-23.2%", and its set of flag rules is exactly {`partial_week`, `revenue_swing`, `large_cancellations`, `top_line`} (values from the earlier independent run in `_saved-runs/kpi-backfill2`).
- **AC-15** — Given the committed `data/derived/summaries.json`, then it has an entry for each of the 52 weeks with sales (2010-12-27 absent), no text contains a `[F` marker or a comma between digits, and week 2011-09-19's headline is "Revenue and orders jump to an unusually strong week, led by pantry products".
- **AC-16** — Given fixture F built and week 2011-09-19, All countries, then `scenario.sources["revenue"]` = "sum(Quantity × Price) over 6 product lines, 2011-09-19..2011-09-25", and `scenario.sources` has a non-empty entry for each of the 10 card KPIs of DEC-11.
- **AC-17** — Given fixture F built and range 2011-09-05..2011-09-19, when `weekly_csv(scenario)` runs, then the UTF-8 text has the header of DEC-12, 3 data rows in week order, and the 2011-09-19 row has revenue_gbp 203.00, orders 5, revenue_wow_pct 153.75, flags "revenue_swing; orders_swing; top_line".
- **AC-18** — Given `download(dest)` with the network mocked to return bytes whose SHA-256 differs from DEC-03, then `ChecksumError` is raised and no file is written to `dest`.
- **AC-19** — Given the committed data, when `app.py` runs in AppTest with no input, then there is no exception, each of the 5 pages of DEC-09 opens via `switch_page(<file>)` with no exception and shows its title as `st.title`, the sidebar preset is "Full year", country "All countries", week 2011-11-28 (the last full week; 2011-12-05 is partial), and the Overview metric "Revenue" shows "£309 378" with delta "+2.3%".
- **AC-20** — Given the app on defaults, when preset "UK only" is chosen, then the Overview "Revenue" metric equals `money()` of the core's United Kingdom revenue for 2011-11-28 and differs from "£309 378"; when Reset is clicked, then preset is "Full year", country "All countries", week 2011-11-28 and "Revenue" shows "£309 378" again.
- **AC-21** — Given the app on defaults and then on preset "Q4 2011", when each of Overview, Trends, Flagged weeks and Weekly table is opened, then each shows the strip metrics "Range revenue", "Range orders" and "Flagged weeks" with identical values across the four pages, equal to the core's totals for that range.
- **AC-22** — Given the app, when the date range input holds only a start date, then the page shows the error "Pick both a start and an end date." and no metric is shown, with no exception.
- **AC-23** — Given the app on defaults, when week 2011-09-19 is picked, then Overview "Revenue" shows "£328 713" with delta "+46.8%" and "Orders" shows "463".
- **AC-24** — Given the app on defaults, then the "Revenue" metric's help text equals the core's `sources["revenue"]` for 2011-11-28, All countries.
- **AC-25** — Given the app on defaults with week 2011-09-19, then the Overview shows the DEC-14 label and the headline "Revenue and orders jump to an unusually strong week, led by pantry products"; on preset "UK only" the summary is hidden and the note "The saved weekly summary covers all countries, so it is hidden while a country filter is on." is shown.
- **AC-26** — Given the app on defaults, when Flagged weeks is opened, then its table has a row for 2011-12-05 whose reasons include "Data ends 2011-12-09; the week is missing days" and "£172 782 cancelled against £483 725 revenue (35.7%)".
- **AC-27** — Given the app on defaults, when Weekly table is opened, then it shows a dataframe with 53 rows and a download button with file name "weekly-kpis_2010-12-06_2011-12-05_all-countries.csv".
- **AC-28** — Given the app, when Methodology & data is opened, then it shows "Chen, D. (2012)", "CC BY 4.0", "https://doi.org/10.24432/C5CG6D", the formula of each of the 10 card KPIs of DEC-11, each flag rule of DEC-08, and the sentence "All figures come from real public data; nothing in this app is synthetic."; and the sidebar of every page shows "Data: UCI Online Retail II (Chen 2012), CC BY 4.0".
- **AC-29** — Given the app on defaults, when Trends is opened, then it shows 4 Plotly charts with no exception.
- **AC-30** — Given every socket connect attempt raises, when the app runs each of the 5 pages in AppTest, then no page has an exception (no network use at runtime).
- **AC-31** — Given `.streamlit/config.toml` and `kpi/theme.py`, then config has `base = "dark"` and its `backgroundColor`, `secondaryBackgroundColor`, `primaryColor` and `textColor` equal the tokens `BG`, `SURFACE`, `BLUE`, `TEXT` in `kpi/theme.py`, and `kpi.theme.TEMPLATE` is a Plotly template registered as "navy".

## Security
| Area | Rule for this feature | Test |
| --- | --- | --- |
| Who | n/a — public read-only demo over public data, no accounts, no per-user data | n/a — no users |
| State | n/a — no writes and no multi-step workflow; session state holds only filter choices | n/a — read-only |
| Limits | Inputs are fixed-choice widgets bounded to 2010-12-06..2011-12-11 and the country list; anything else is refused with a plain message | AC-11, AC-22 |
| Logging | loguru, operation level only (build counts, file names); never data rows; derived data has no customer ids | AC-01 |
| CORS | n/a — no API endpoint of our own; Streamlit serves the page | n/a — no endpoint |
| LLM | n/a — no model call at runtime; saved summaries are static committed text | AC-30 |
| Errors | Invalid filters show the DEC-15 message via `st.error`, never a traceback | AC-11, AC-22 |
| Image | n/a — no image built; Streamlit Cloud installs `requirements.txt` exported from `uv.lock` | n/a — no image |

## Locked decisions
| ID | Decision | Owner part |
| --- | --- | --- |
| DEC-01 | Test stack: pytest, run with `uv run pytest`; app tests use `streamlit.testing.v1.AppTest` on `app.py` with the committed `data/derived/`; core tests build fixture F into `tmp_path`. Playwright (bundled Chromium) only for screenshots in `tools/`, not tests. Acceptance helpers (fixture F builder) live in `tests/acceptance/retail-kpi-dashboard/fixture.py`. | — |
| DEC-02 | Layout: flat, not packaged. `app.py` entry, `kpi/` package (core, no Streamlit imports), `views/` page scripts, `assets/style.css`, `.streamlit/config.toml`, `data/derived/`, `tools/`. Streamlit pinned 1.67.0. | PART-B (app/views), PART-A (kpi core) |
| DEC-03 | Raw data: `kpi.download.download(dest: Path) -> Path` fetches `https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip`, checks SHA-256 `572e36277c2390fbfde10664750731e0a86f55e33470d91919085f0408e67bfb`, extracts `online_retail_II.xlsx` to `dest/`; mismatch raises `kpi.download.ChecksumError` before writing anything. Timeout 120 s. Raw lives in `data/raw/` (gitignored). | PART-A |
| DEC-04 | Cleaning (same as the source project): input columns `Invoice, StockCode, Description, Quantity, InvoiceDate, Price, Customer ID, Country`, all sheets concatenated. Each line gets one bucket, first match wins: `duplicate` (exact duplicate of an earlier line over all 8 columns), `cancellation` (Invoice starts "C"), `adjustment` (Invoice starts "A"), `non_product` (StockCode not matching `^\d{5}[A-Za-z]*$`), `non_positive` (Price ≤ 0 or Quantity ≤ 0), else `product`. Line revenue = Quantity × Price. Description and Country stripped. | PART-A |
| DEC-05 | Weeks: ISO weeks Monday..Sunday. Shown weeks `FIRST_WEEK = 2010-12-06` .. `LAST_WEEK = 2011-12-05` (53 weeks), constants in `kpi.models`. The build also computes week 2010-11-29 as the change base for the first shown week. Date inputs are limited to 2010-12-06..2011-12-11 and snap to the Monday of their ISO week. | PART-A |
| DEC-06 | Build: `kpi.build.build(raw: pd.DataFrame, out_dir: Path) -> None` writes `weekly.parquet` (one row per week × filter value, all KPI columns of DEC-11 + data-quality counts + top line fields), `products.parquet` (week × filter value × StockCode: description, revenue, units), `meta.json` (`data_end` ISO datetime of the last line in the raw data, `countries` list). CLI: `uv run python -m kpi.build --raw data/raw/online_retail_II.xlsx --out data/derived` (downloads the raw file first if missing). Filter values: "All countries", "United Kingdom", "Outside UK" (every country except United Kingdom), then every other country alphabetically. New customer = customer in the filtered week whose first product line in the whole raw data (any country) is in that week; returning = customers − new. Customer counts are distinct within the filter value. | PART-A |
| DEC-07 | Core interface: `kpi.core.run_scenario(filters: Filters, data_dir: Path = DATA_DIR) -> Scenario`, `kpi.core.countries(data_dir: Path = DATA_DIR) -> list[str]` (filter values of DEC-06 in order), `kpi.core.weekly_csv(scenario: Scenario) -> bytes`, `kpi.core.swing(change: float | None) -> bool`, `kpi.core.week_flags(...)` internal. `DATA_DIR = <repo>/data/derived`. Models in `kpi.models` (Pydantic): `Filters(start: date, end: date, country: str = "All countries", week: date)`; `WeekRow` (week_start, every DEC-11 KPI, cancellation_invoices, product_lines, lines_without_customer_id, revenue_wow, orders_wow, aov_wow, units_wow, customers_wow, new_customers_wow, returning_customers_wow, cancellation_rate_change_pp, cancelled_value_wow, net_revenue_wow, flags: list[Flag]); `Flag(week_start: date, rule: str, reason: str)`; `Ranked(label: str, revenue: float)`; `Totals(revenue, orders, units, cancelled_value, net_revenue, weeks, flagged_weeks)`; `Scenario(filters, weeks: list[WeekRow], selected: WeekRow, totals: Totals, top_products: list[Ranked], top_countries: list[Ranked], flags: list[Flag], sources: dict[str, str], summary: Summary | None)`; `Summary(headline: str, text: str)`. Changes are percentages (153.75 means +153.75%), None when the base is 0 or missing. | PART-A |
| DEC-08 | Flags per week and filter value, rule names exact, in this order: `no_data` (0 product lines) "No sales lines this week"; `partial_week` (the week contains `data_end` and `data_end` date is before its Sunday) "Data ends {YYYY-MM-DD}; the week is missing days"; `revenue_swing` / `orders_swing` (`swing(change)`: abs of change rounded half-up to 0.1 ≥ 25.0) "Revenue {change} vs previous week ({money now} vs {money prev})" / "Orders {change} vs previous week ({count now} vs {count prev})"; `large_cancellations` (cancelled value ≥ 25% of revenue, revenue > 0) "{money cancelled} cancelled against {money revenue} revenue ({pct share})"; `top_line` (largest product line > 25.0% of revenue) "One line is {pct share} of revenue: {description}, {money line} (invoice {invoice})". | PART-A |
| DEC-09 | Pages, titles and files, in navigation order: "Overview" `views/overview.py` (default), "Trends" `views/trends.py`, "Flagged weeks" `views/flags.py`, "Weekly table" `views/table.py`, "Methodology & data" `views/methodology.py`. Each page starts with `st.title(<its title>)`. | PART-B |
| DEC-10 | Sidebar (in `app.py`), widget keys: `preset` selectbox ["Full year", "Q4 2011", "UK only", "Outside UK", "Custom"]; `dates` date_input range; `country` selectbox (DEC-06 values); `week` selectbox of the weeks in range (label "YYYY-MM-DD – YYYY-MM-DD"), default and fallback = last week in range without a `partial_week` flag (the last week in range if every week is partial), so Full year and Q4 2011 open on 2011-11-28; `reset` button "Reset to Full year". Presets: Full year = 2010-12-06..2011-12-05, All countries; Q4 2011 = 2011-10-03..2011-12-05, All countries; UK only = full year, United Kingdom; Outside UK = full year, Outside UK. Changing dates or country by hand sets preset to "Custom". Reset = Full year, week 2011-11-28. The scenario is computed once per run with `st.cache_data(run_scenario)` and passed to pages via `st.session_state["scenario"]`. Sidebar footer text: "Data: UCI Online Retail II (Chen 2012), CC BY 4.0". | PART-B |
| DEC-11 | The 10 card KPIs, label → Scenario key → display: "Revenue" revenue money; "Orders" orders count; "Average order value" aov money2; "Units" units count; "Customers" customers count; "New customers" new_customers count; "Returning customers" returning_customers count; "Cancellation rate" cancellation_rate pct (delta in points); "Cancelled value" cancelled_value money; "Revenue after cancellations" net_revenue money. Delta = WoW change display; `delta_color="inverse"` for cancellation rate and cancelled value. Each metric's help = `scenario.sources[key]`. Revenue source format: "sum(Quantity × Price) over {count lines} product lines, {start}..{end}". | PART-A (keys, sources) / PART-B (cards) |
| DEC-12 | CSV header, in order: `week_start,revenue_gbp,orders,aov_gbp,units,customers,new_customers,returning_customers,cancellation_invoices,cancellation_rate_pct,cancelled_value_gbp,net_revenue_gbp,product_lines,lines_without_customer_id,revenue_wow_pct,orders_wow_pct,flags`. Money and percentages with 2 decimals, empty cell for None, flags = rule names joined by "; ". Download file name `weekly-kpis_{start}_{end}_{country-slug}.csv` (slug: lowercase, spaces → dashes). | PART-A (csv) / PART-B (file name) |
| DEC-13 | Formatters in `kpi.fmt`: `money` (£, whole pounds, half-up), `money2` (£, 2 decimals, half-up), `count`, `pct` (1 decimal + "%"), `change` (sign always, 1 decimal + "%", None → "n/a"), `points` (sign always, 1 decimal + " pp"). Thousands separator U+202F. Half-up applied after snapping the float to 9 decimals. | PART-A |
| DEC-14 | Saved summaries: `kpi.summaries.build_summaries(src: Path, out: Path) -> int` reads `<src>/<week>/report.md` of the earlier run, keeps the headline (first `## ` heading) and the narrative paragraphs before "## Worth a look", removes ` [Fn]` markers, turns a comma between a digit and exactly 3 digits into U+202F, writes `data/derived/summaries.json` `{week: {headline, text}}`. Shown on Overview only for "All countries", under the label "Weekly summary written by AI in an earlier run; every figure was checked against the computed numbers. This app makes no AI calls." | PART-A (file) / PART-B (display) |
| DEC-15 | Error messages, exact: "Start week must be on or before end week.", "Dates must be between 2010-12-06 and 2011-12-11.", "Selected week must be inside the date range.", "Unknown country: {name}." (core, `ValueError`); "Pick both a start and an end date." (app). The app shows them with `st.error` and stops the page. | PART-A (core) / PART-B (app) |
| DEC-16 | Theme: tokens in `kpi/theme.py` (`BG #0B1426`, `SURFACE #13203A`, `BORDER #22324F`, `TEXT #E6ECF5`, `MUTED #8B9AB4`, `BLUE #3B82F6`, `GREEN #22C55E`, `AMBER #F59E0B`, `RED #EF4444`, `FONT "Inter", "Avenir Next", "Helvetica Neue", Arial, sans-serif`) + `TEMPLATE` (Plotly template registered as "navy" and set as default); `.streamlit/config.toml` mirrors the colours; `assets/style.css` styles cards and spacing, loaded once in `app.py`. | PART-B |
| DEC-17 | Fixture F (columns of DEC-04; customer ids numeric): 400001,20001,MUG RED,1,2010-01-10 09:00,2.00,90003,France · 500001,20001,MUG RED,10,2011-09-13 10:00,2.00,90001,United Kingdom · 500001,20002,MUG BLUE,5,2011-09-13 10:00,4.00,90001,United Kingdom · 500002,20001,MUG RED,20,2011-09-14 11:00,2.00,90003,France · 500003,20001,MUG RED,30,2011-09-20 09:00,2.00,90002,United Kingdom · 500003,20003,LAMP,2,2011-09-20 09:00,25.00,90002,United Kingdom · 500004,20002,MUG BLUE,10,2011-09-21 12:00,4.00,90004,United Kingdom · 500004 line repeated exactly once (duplicate) · 500005,20003,LAMP,1,2011-09-22 12:00,25.00,90004,France · 500006,20002,MUG BLUE,5,2011-09-23 15:00,4.00,(empty),United Kingdom · C500007,20003,LAMP,-1,2011-09-24 10:00,25.00,90002,United Kingdom · A500008,B,Adjust bad debt,1,2011-09-24 11:00,100.00,(empty),United Kingdom · 500009,POST,POSTAGE,1,2011-09-24 12:00,15.00,90004,France · 500010,20001,MUG RED,3,2011-09-25 10:00,0.00,90001,United Kingdom · 500011,20002,MUG BLUE,2,2011-09-25 11:00,4.00,90001,United Kingdom. Hand calculations in `docs/test-cases.md`. | — |

## Work split
| Part | Builds | Owns (files/folders) | ACs | Depends on |
| --- | --- | --- | --- | --- |
| PART-A | Download, cleaning, build of derived tables, saved summaries, calc core, formatters, committed derived data, hand-calculated test cases doc | `kpi/__init__.py`, `kpi/models.py`, `kpi/data.py`, `kpi/build.py`, `kpi/core.py`, `kpi/fmt.py`, `kpi/download.py`, `kpi/summaries.py`, `data/derived/`, `docs/test-cases.md`, `tests/retail-kpi-dashboard/part-a/` | AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18 | — |
| PART-B | Streamlit app, sidebar, 5 pages, theme, CSS, screenshots tool, README | `app.py`, `views/`, `kpi/theme.py`, `assets/`, `.streamlit/`, `tools/`, `docs/screenshots/`, `README.md`, `tests/retail-kpi-dashboard/part-b/` | AC-19, AC-20, AC-21, AC-22, AC-23, AC-24, AC-25, AC-26, AC-27, AC-28, AC-29, AC-30, AC-31 | PART-A |

## Test map
| AC | Part | Test |
| --- | --- | --- |
| AC-01 | PART-A | `tests/acceptance/retail-kpi-dashboard/test_ac_01_build_outputs.py::test_ac_01_build_outputs` |
| AC-02 | PART-A | `tests/acceptance/retail-kpi-dashboard/test_ac_02_week_kpis.py::test_ac_02_week_kpis` |
| AC-03 | PART-A | `tests/acceptance/retail-kpi-dashboard/test_ac_03_cleaning_counts.py::test_ac_03_cleaning_counts` |
| AC-04 | PART-A | `tests/acceptance/retail-kpi-dashboard/test_ac_04_wow_changes.py::test_ac_04_wow_changes` |
| AC-05 | PART-A | `tests/acceptance/retail-kpi-dashboard/test_ac_05_country_filters.py::test_ac_05_country_filters` |
| AC-06 | PART-A | `tests/acceptance/retail-kpi-dashboard/test_ac_06_top_lists.py::test_ac_06_top_lists` |
| AC-07 | PART-A | `tests/acceptance/retail-kpi-dashboard/test_ac_07_swing_flags.py::test_ac_07_swing_flags` |
| AC-08 | PART-A | `tests/acceptance/retail-kpi-dashboard/test_ac_08_cancellation_flag.py::test_ac_08_cancellation_flag` |
| AC-09 | PART-A | `tests/acceptance/retail-kpi-dashboard/test_ac_09_no_data_partial.py::test_ac_09_no_data_partial` |
| AC-10 | PART-A | `tests/acceptance/retail-kpi-dashboard/test_ac_10_top_line_flag.py::test_ac_10_top_line_flag` |
| AC-11 | PART-A | `tests/acceptance/retail-kpi-dashboard/test_ac_11_invalid_filters.py::test_ac_11_invalid_filters` |
| AC-12 | PART-A | `tests/acceptance/retail-kpi-dashboard/test_ac_12_range_totals.py::test_ac_12_range_totals` |
| AC-13 | PART-A | `tests/acceptance/retail-kpi-dashboard/test_ac_13_formatters.py::test_ac_13_formatters` |
| AC-14 | PART-A | `tests/acceptance/retail-kpi-dashboard/test_ac_14_real_data_matches_saved_run.py::test_ac_14_real_data_matches_saved_run` |
| AC-15 | PART-A | `tests/acceptance/retail-kpi-dashboard/test_ac_15_saved_summaries.py::test_ac_15_saved_summaries` |
| AC-16 | PART-A | `tests/acceptance/retail-kpi-dashboard/test_ac_16_sources.py::test_ac_16_sources` |
| AC-17 | PART-A | `tests/acceptance/retail-kpi-dashboard/test_ac_17_csv_export.py::test_ac_17_csv_export` |
| AC-18 | PART-A | `tests/acceptance/retail-kpi-dashboard/test_ac_18_download_checksum.py::test_ac_18_download_checksum` |
| AC-19 | PART-B | `tests/acceptance/retail-kpi-dashboard/test_ac_19_app_defaults.py::test_ac_19_app_defaults` |
| AC-20 | PART-B | `tests/acceptance/retail-kpi-dashboard/test_ac_20_preset_and_reset.py::test_ac_20_preset_and_reset` |
| AC-21 | PART-B | `tests/acceptance/retail-kpi-dashboard/test_ac_21_same_kpi_every_page.py::test_ac_21_same_kpi_every_page` |
| AC-22 | PART-B | `tests/acceptance/retail-kpi-dashboard/test_ac_22_bad_date_input.py::test_ac_22_bad_date_input` |
| AC-23 | PART-B | `tests/acceptance/retail-kpi-dashboard/test_ac_23_week_picker.py::test_ac_23_week_picker` |
| AC-24 | PART-B | `tests/acceptance/retail-kpi-dashboard/test_ac_24_metric_help.py::test_ac_24_metric_help` |
| AC-25 | PART-B | `tests/acceptance/retail-kpi-dashboard/test_ac_25_summary_label.py::test_ac_25_summary_label` |
| AC-26 | PART-B | `tests/acceptance/retail-kpi-dashboard/test_ac_26_flagged_page.py::test_ac_26_flagged_page` |
| AC-27 | PART-B | `tests/acceptance/retail-kpi-dashboard/test_ac_27_table_and_download.py::test_ac_27_table_and_download` |
| AC-28 | PART-B | `tests/acceptance/retail-kpi-dashboard/test_ac_28_methodology_attribution.py::test_ac_28_methodology_attribution` |
| AC-29 | PART-B | `tests/acceptance/retail-kpi-dashboard/test_ac_29_trend_charts.py::test_ac_29_trend_charts` |
| AC-30 | PART-B | `tests/acceptance/retail-kpi-dashboard/test_ac_30_no_network.py::test_ac_30_no_network` |
| AC-31 | PART-B | `tests/acceptance/retail-kpi-dashboard/test_ac_31_theme_tokens.py::test_ac_31_theme_tokens` |

## Smoke run
After both parts merge: `uv run python -m kpi.build --raw data/raw/online_retail_II.xlsx --out data/derived` reproduces the committed tables (git diff empty), then `make run PORT=8780` on 127.0.0.1. Playwright script `tools/screenshots.py` opens every page at 1280 and 1440 px on defaults, plus Overview on week 2011-09-19 and preset "UK only", and saves PNGs to `docs/screenshots/`. Expected: Overview defaults show week 2011-11-28, Revenue £309 378 (+2.3%); picking 2011-12-05 shows £483 725 (+56.4%) with 4 flags; week 2011-09-19 shows £328 713 (+46.8%) and its saved summary; Flagged weeks lists 2011-01-17 and 2011-12-05 with large cancellations; no error, no network call, no exception in the server log.

## Open questions
(none)
