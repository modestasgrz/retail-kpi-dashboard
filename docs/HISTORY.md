# Project history

How this dashboard got to its current state, why it looks the way it does, and how to keep improving it without re-learning everything. The contract is still `specs/retail-kpi-dashboard.md`. This file explains the decisions behind it.

Dates are 2026-11-09 to 2026-11-11. PR numbers refer to this repository.

## 1. Current state

| Item | State |
| --- | --- |
| What it is | Weekly KPI review of an online giftware retailer (UCI Online Retail II, CC BY 4.0), Streamlit 1.67.0, 5 pages: Overview, Trends, Flagged weeks, Weekly table, Methodology & data |
| Shown range | 53 ISO weeks, 2010-12-06 .. 2011-12-05 (the last one is partial: data ends 2011-12-09). The build also keeps the 52 weeks before, as year-over-year and 4-week-average bases only |
| Headline figure | Net revenue (gross − cancelled value) everywhere; gross is secondary |
| Theme | "Graphite": near-black, hairline cards, system font, neutral controls; blue = data, green/red = good/bad change, amber = flagged weeks |
| Spec | `specs/retail-kpi-dashboard.md`, status approved, AC-01..AC-53 with 4 removed (AC-07, AC-21, AC-25, AC-26), so 49 active; 31 locked decisions (DEC-01..DEC-31) |
| Tests | 49 acceptance tests; 418 unit tests for PART-A (build, core) and 607 for PART-B (app, AppTest); `make check` = 1 025 passed, 10 skipped |
| Data | `data/derived/` (2 MB parquet + json, no customer ids) is committed; the raw xlsx is gitignored and downloaded with a SHA-256 check |
| Live URL | _not deployed yet_ (Streamlit Community Cloud steps prepared in `docs/deploy-streamlit-cloud.md`; the deploy needs the owner's login) |
| Open PRs | #2, a Dependabot bump of a CI action, left open on purpose (dependency changes need the owner) |

| Task | Command |
| --- | --- |
| Install | `uv sync` |
| Run | `make run` (127.0.0.1; `make run PORT=8780` for the usual port) |
| All checks | `make check` (ruff, ruff format, mypy strict, security scans, unit tests) |
| Acceptance tests | `uv run pytest tests/acceptance` or `python3 scripts/agent_guardrails.py run --feature retail-kpi-dashboard [--part PART-A]` |
| Spec ↔ tests check | `python3 scripts/agent_guardrails.py consistency` |
| Rebuild data | `uv run python -m kpi.build --raw data/raw/online_retail_II.xlsx --out data/derived` (~30 s; must give an empty `git diff`) |
| Screenshots | start the app on 8780, then `uv run python tools/screenshots.py` → 14 PNGs in `docs/screenshots/` (see the gotchas before committing them) |

Real-data check values (full year, All countries):
- Net revenue £9 593 707, from £10 066 085 gross less £472 377 cancelled, over 19 349 orders.
- 9 flagged weeks: revenue swing 6, orders swing 3, placed and cancelled 2, no sales 1, partial week 1.
- Default week 2011-11-28: net £306 112, +3.7% vs last week, −0.9% vs the same week last year.

## 2. Decision log

| Date | Decision | Why | Reversed? |
| --- | --- | --- | --- |
| 11-09 | Commit derived parquet tables; raw file gitignored, downloaded with a SHA-256 check; customer ids never leave the build step | The app must run without the 44 MB raw file and without personal data | No |
| 11-09 | One country at a time (All / UK / Outside UK / each country), dates snap to ISO weeks, 4 presets + Reset | Keeps every number reproducible and testable | No |
| 11-09 | Default week = last full week (2011-11-28), not the last week | 2011-12-05 is partial and looked like a crash or a spike | No |
| 11-09 | Saved weekly summaries (written by AI in an earlier offline run, figures checked) shown read-only, All countries only, always labelled; no AI or network calls at runtime | Summaries add reading value; the label keeps it honest | Moved: first under the title, then (round 3) only inside a labelled expander |
| 11-09 | A change shows "n/a" when the base week is ≤ 0 | A % change from a negative base has no meaningful sign | No |
| 11-09 | No swing flag in a no-sales week or the week after one (AC-32) | Nothing fair to compare with | No |
| 11-10 | Swing flags compare with the trailing 4-week average at 40%, replacing week-over-week | Week-over-week flagged too much; 25% flagged 21 weeks, 40% flags 9 | Yes (replaced the week-over-week rule) |
| 11-10 | Countries list = countries with sales in the shown weeks (40 filter values, 38 countries) | Korea sold only in hidden base weeks and showed an empty filter | No |
| 11-10 | Repo made public after a privacy check (no secrets, no personal data, aggregates only) | CI minutes for private repos ran out | No |
| 11-10 | Product names in title case, also inside flag reasons | Raw descriptions are all caps | No |
| 11-10 | Year over year: dropped in round 1, added in round 3 (base = week − 364 days; "—" for partial or no-sales weeks or a base ≤ 0) | Round 1 thought there was no prior year; the raw data starts 2009-12-01, so the build now keeps 105 weeks | Yes (drop reversed) |
| 11-10 | Net revenue is the headline; revenue swings use net | Two "revenue spikes" (2011-01-17 +55.9%, 2011-12-05 +44.1% on gross) were single huge orders cancelled the same week; on net they are ordinary weeks | Yes (gross headline replaced) |
| 11-10 | "Placed and cancelled" flag: same week, stock code, customer and price; fires when the matched value > 25% of gross; replaces "one big order" + "large cancellations" for that order | The two real cases are £77 184 and £168 470 (~35% of gross each); the next biggest match is 5.8%, so 25% separates them cleanly | No |
| 11-10 | One cancellation metric on the cards: Cancelled (£); the rate moves into its tooltip | Gross − cancelled = net, so the £ value bridges the two | No |
| 11-10 | Swing drivers: top 3 products (and countries for All / Outside UK) by contribution vs the 4-week average, with "% of the change" explained | On 2011-09-19 the top 3 products explain only 11.5%, the top 3 countries 90.3%; showing the % stops the list from overstating | No |
| 11-10 | Orders-swing drivers by country only | Order counts don't add up across products | No |
| 11-10 | Country driver % uses the filter's true change, not the sum of country rows | Review found Dec 2010 base weeks include countries that are not filter values (97.54% shown vs 97.42% true) | No |
| 11-10 | Accept two Streamlit limits: no last-point dot on metric sparklines, no per-cell tooltips in tables | `st.metric` and `st.dataframe` don't support them | No |
| 11-10 | Graphite theme, system font stack, neutral controls | Owner pick after a theme review; Inter renders the U+202F thousands space as zero width in bold numbers | Yes (replaced the navy theme) |
| 11-10 | Metric deltas keep green/red by meaning (Cancelled inverted); the shared CSS rule that greys them is not used | A KPI dashboard needs good/bad at a glance | No |
| 11-10 | A 3-line reading strip (THE QUESTION / RIGHT NOW / DO THIS) on 4 pages; every ? help starts with one plain sentence | Make each page readable for someone who doesn't build dashboards | No |
| 11-11 | RIGHT NOW says what the cards don't: "Biggest move vs last week", leaving out Cancelled | The computed headline repeated the Net revenue card; Cancelled won "biggest move" in 33 of 51 weeks because of its small base | Yes (headline in the strip replaced; the core still computes it) |
| 11-11 | Flag details open by default; Flagged weeks newest first; order drivers in whole numbers; table uses the same flag names as the badges; Avg order with 2 decimals | UX critique: the reason was hidden behind a click, 1 900 px of scrolling to reach recent weeks, "−393.8 orders", two naming schemes | Yes (newest-last, short table labels and whole-£ AOV reversed) |
| 11-11 | At 1280 px the table's Flags column may truncate; full reasons are on Flagged weeks | The 11 columns don't fit at 1280 with the system font otherwise | No |
| 11-11 | Leave the unused core headline (`Scenario.headline`, AC-46) and the "+0.0%" for a change that rounds to zero from below | Not worth a round | No |

## 3. Review rounds

| Round | Found | Changed | Dropped / later, and why |
| --- | --- | --- | --- |
| Build reviews (every PART PR) | An independent code review and a separate QA test pass on each PART PR. Round 1: CSV rounding off in 41 real cells, cancel lines over-counted, a float-noise threshold bug, negative change bases, a crash on data without customer ids | All fixed before merge; QA tests live in `tests/retail-kpi-dashboard/part-*/test_qa_*.py` | — |
| Persona review 1 (CEO + designer, after v1) | Charts dropped to £0 on the no-sales week; flags too noisy; flat hierarchy; table scrolled sideways; mixed fonts | Gaps and a hollow partial week; 4-week-average swings at 40%; range line, status pill, 3 big + 7 small cards, sparklines; Trends polish; top-5 share bars; Flagged weeks grouped; pinned table; one font; "With your data" line on Methodology | Year over year (wrongly thought impossible, added in round 3); margin, stock, targets (no data); walkthrough video (owner records it) |
| Persona review 2 (CEO + designer, after round 2) | Gross headline misleading; the AI line looked like a fact; no year comparison; flags gave no reason "why"; big order + its cancellation shown as two flags; two cancellation metrics | Net revenue first; computed headline (AI summary only in a labelled expander); YoY on the big cards; drivers with % explained; "Placed and cancelled"; one Cancelled metric; Trends net/gross toggle; 8-week table; polish | Monday email digest (outbound, needs the owner's yes); wholesale vs retail split (needs an invented rule); targets and margin (no data) |
| Round-3 code review | Negative-net weeks clipped off the axis; the Gross partial marker drawn above the plot; YoY "—" said "no sales" when the base was ≤ 0; base value missing below −100% | All fixed; DEC-27 text updated (#19) | — |
| Theme review → Graphite (owner pick) | The navy theme read as busy; non-builders found the pages hard to read | Graphite theme, reading strip, plain-words help, system font | — |
| UX critique of the Graphite build (scored 7/10) | Week dates clipped in the table; strip repeated the cards; flag reason hidden; Trends didn't show the selected week; oldest flags first; "RETURNING CUST…" cut; filled blue info box broke "blue = data" | All in-spec items fixed in #22; the spec-text items (RIGHT NOW wording, open details, newest first, whole-number drivers, one flag naming) in #23–#25 | Cancelled-chart y-axis clamp and month tick alignment (not judged worth a spec change); "Rule" column on Methodology kept because an AC needs the rule names |

## 4. Known limits, leftovers and "later"

| Item | Kind | Why it's like this |
| --- | --- | --- |
| A cancellation counts in the week it happens, not the week of the original order | Limit | The data has no reliable order-to-cancellation link across weeks |
| Placed-and-cancelled only matches within one week, lines with a customer id, same price | Limit | Stated on Methodology; wider matching would need an invented rule |
| Wholesale and retail buyers are mixed, so the average order value blends both | Limit / later | A split needs an invented segment rule (owner decision) |
| Customer counts only include lines with a customer id | Limit | Many lines have none |
| Country driver contributions may not add up exactly to the change | Limit | Base weeks before Dec 2010 contain countries that are not filter values |
| `Scenario.headline` is computed but not shown | Leftover | Owner chose to leave it (AC-46 still covers it) |
| "+0.0%" for a change that rounds to zero from below | Leftover | `kpi/fmt.py` `signed()`; owner chose to leave it |
| Monday email digest | Later | Outbound sending needs the owner's explicit yes |
| Margin, stock, targets | Dropped | No such data; the Methodology "With your data" line covers it |
| Walkthrough video | Later | The owner records it |
| Streamlit Community Cloud deploy | Later | Needs the owner's login; steps in `docs/deploy-streamlit-cloud.md` |
| Dependabot PR #2 | Open | Dependency and CI changes need the owner |

## 5. Gotchas

| Gotcha | What to do |
| --- | --- |
| `spec-guard` lanes: a PR may only touch its PART's files (see the spec's Work split). `README.md`, `docs/screenshots/`, `tools/` are PART-B; `docs/test-cases.md` and `data/derived/` are PART-A | Put cross-lane lines in the right PART PR, or in a `[no-spec]` docs PR |
| PR titles are parsed by CI | `[retail-kpi-dashboard/SPEC] …`, `[retail-kpi-dashboard/PART-A] …`, `[retail-kpi-dashboard/PART-B] …` or `[no-spec] …` |
| PART PRs fail while the spec's status line says `draft` | Every SPEC PR must leave `Status: approved` |
| A PART-A data change breaks PART-B unit tests that pin the old behaviour, and PART-A can't edit them | Merge PART-A and the matching PART-B PR back to back |
| PRs are squash-merged; a PR stacked on another keeps the old commits | After the base merges, merge `origin/main` into the stacked branch, push, and wait for the run on the new head (the run started by a retarget can be stale) |
| `spec-guard` diffs `base...HEAD` | A clean `git diff origin/main` locally doesn't help if the remote branch hasn't been pushed |
| Repo hooks block force-push, `rm -rf`, `curl`, inline `gh pr create` bodies and shell variables in `gh api` paths | Merge instead of rebase; delete specific files; use Python `urllib`; `--body-file`; literal API paths |
| Screenshots from a long-running server can show an old module's error page (it happened once: #18, fixed in #20) | Restart the app after changing any imported module, then **open every PNG** before committing. An error page comes out at exactly 900 px tall |
| Playwright's pinned Chromium build may be missing, and `playwright install` can hang | Point `executable_path` at a cached `chromium_headless_shell` build. Any recent build renders the same |
| Inter drops the U+202F thousands space in bold text (`£349968`) | Keep the system font stack in `kpi/theme.py` / config |
| `st.dataframe` widths depend on the font; AppTest can't see layout | Check the table in a real browser at 1280 and 1440 (scroller `scrollWidth` = `clientWidth`) |
| Plotly `add_vline(annotation=…)` fails on date axes | Add the label with a separate `add_annotation(yref="paper")` |
| The reading strip is HTML in `st.markdown` | Escape with `html.escape(…, quote=False)` so apostrophes stay literal |
| mypy runs over acceptance tests that use fields the code doesn't have yet | Read them through `Any` (`vars(module)[…]`, `s: Any = …`) |
| ruff's cache once hid an import-order error that CI caught | Use `--no-cache` |
| AppTest runs can hit the 60 s timeout when the machine is busy | Re-run alone before calling it a bug |
| The source data has a description with a space before a comma ("Paper Craft , Little Birdie") | That's the data, not a bug; flag reasons quote it as is |

## 6. How to resume

The process that built every round:
1. **Read** this file, the spec and `docs/test-cases.md`.
2. **Prototype risky numbers on the real data** (rebuild the derived tables or load the raw file) before writing them into an AC.
3. **SPEC PR first.** Edit `specs/retail-kpi-dashboard.md`: new or changed ACs, locked decisions, work split, test map, status `approved`. Also write the failing acceptance tests in `tests/acceptance/retail-kpi-dashboard/`. Run `consistency` and `make check`. Only the SPEC PR may touch `specs/` and `tests/acceptance/`.
4. **PART PRs**:
   - PART-A: `kpi/` core and build, `data/derived/`, `docs/test-cases.md`, `tests/retail-kpi-dashboard/part-a/`.
   - PART-B: `app.py`, `views/`, `kpi/theme.py`, `assets/`, `.streamlit/`, `tools/`, `docs/screenshots/`, `README.md`, `tests/retail-kpi-dashboard/part-b/`.
   - Each PART PR gets an independent code review and a QA test pass before merge.
5. **Gate 5 on main.** Restart the server on 8780 and rebuild the data (empty diff). Smoke-test every page in a browser. Regenerate the screenshots and view every one, then send a `[no-spec]` docs PR only if they changed. Update the README numbers if any changed.

| Where | What |
| --- | --- |
| `specs/retail-kpi-dashboard.md` | The contract: ACs, DEC-01..31, work split, test map |
| `kpi/build.py`, `kpi/data.py` | Raw → derived tables (cleaning rules DEC-04, placed-and-cancelled DEC-25) |
| `kpi/core.py`, `kpi/models.py`, `kpi/fmt.py` | Every number the pages show (`run_scenario`), flags, drivers, YoY, CSV, formatting |
| `views/*.py`, `views/ui.py`, `app.py` | Pages, the shared header, strip and flag lines, sidebar |
| `kpi/theme.py`, `assets/style.css`, `.streamlit/config.toml` | Graphite tokens, CSS, Plotly template |
| `docs/test-cases.md` | Hand calculations behind the fixture ACs |
| `docs/deploy-streamlit-cloud.md` | Deploy steps (not deployed) |

To pick up a "later" item:
- **Monday email digest:** the core already has every number and the strip texts; it needs an outbound channel, so get the owner's yes first, then spec it as a new PART.
- **Wholesale vs retail split:** agree a rule with the owner (e.g. order value or units per line), prototype it on the real data, then add a filter value or a segment column in the build (PART-A) and a filter in the sidebar (PART-B).
- **Deploy:** follow `docs/deploy-streamlit-cloud.md`, then put the live URL in section 1 and the README.
- **The two leftovers:** a small PART-A PR. Drop `Scenario.headline` (and AC-46 in a SPEC PR first), and make `signed()` print "0.0%" without a sign.
