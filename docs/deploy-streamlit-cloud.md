# Deploy to Streamlit Community Cloud (owner step, not done yet)

Status: prepared, not deployed. The repo is public.

## What's already in place

| Need | Where | State |
| --- | --- | --- |
| Entry file | `app.py` | ✓ |
| Dependencies | `requirements.txt`, exported from `uv.lock` (`make requirements`), 42 pinned packages, Streamlit 1.67.0, no dev tools | ✓ |
| Python version | 3.12 (`.python-version`) | pick it in Advanced settings |
| Data | `data/derived/` (2 MB, committed, no customer ids); the app never downloads anything | ✓ |
| Secrets | none: no API keys, no network calls at runtime | ✓ |
| Theme | `.streamlit/config.toml` (dark navy, telemetry off) | ✓ |

## Steps (about 5 minutes, needs the owner's GitHub login)

1. Refresh the dependency export on main if `uv.lock` changed: `make requirements`, commit through a PR.
2. Go to https://share.streamlit.io and sign in with GitHub as `modestasgrz`. Grant Streamlit access to `modestasgrz/retail-kpi-dashboard` when asked.
3. **Create app** → **Deploy a public app from GitHub**: repository `modestasgrz/retail-kpi-dashboard`, branch `main`, main file path `app.py`.
4. **App URL**: pick a readable subdomain, e.g. `retail-kpi-dashboard`.
5. **Advanced settings**: Python **3.12**. No secrets.
6. **Deploy**. The first build installs the requirements (a few minutes). Then open every page once: Overview, Trends, Flagged weeks, Weekly table, Methodology & data.
7. Check the result: Overview shows week 2011-11-28, Revenue £309 378 (+2.3%); Download CSV gives `weekly-kpis_2010-12-06_2011-12-05_all-countries.csv`.

## Decisions for the owner before deploying

- **Who can open it.** Apps from a public repo can be opened by anyone with the link; check **Settings → Sharing** after deploying.
- **Which dependency file Cloud reads.** The repo has both `uv.lock` and `requirements.txt`. Check the build log to see which one Cloud picked; both pin the same runtime versions.

## After deploying

- Add the live URL to the README (top line) through a `[no-spec]` PR.
- Cloud apps sleep after a period without visitors; the first visit wakes them in under a minute. Open the link before sending it to a client.
