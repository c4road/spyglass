# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

SpyGlass is a collection of *lenses* — focused **Streamlit** trading/research
tools over live market data. **Each lens is its own standalone app** with its own
`app.py`; there is no shared router, registry, or multi-lens picker. They share
only the pure `core/` package. The repo depends on **nothing** outside its own
`requirements.txt` and public Yahoo Finance endpoints, and each lens is meant to
be deployed free on Streamlit Community Cloud and given away.

**User-facing copy is in Spanish** (Rioplatense *voseo*: "completá", "tocá",
"respetás"). Code — identifiers, docstrings, comments, and this file — stays in
English. When adding UI text, write it in Spanish; when adding code, don't.

**These are educational tools, not financial advice** — keep that framing in any
user-facing copy, and never present output as a recommendation to trade.

## Setup & commands

- **Python:** 3.10+ (uses `list[...]`/`X | Y` typing).
- **Install (app):** `pip install -r requirements.txt` (a virtualenv is recommended).
- **Install (tests):** `pip install -r requirements.txt -r requirements-dev.txt` —
  `pytest` lives in `requirements-dev.txt` and is **not** in `requirements.txt`, so
  Streamlit Cloud never installs it. A bare `python -m pytest` failing with
  "No module named pytest" means the dev deps aren't installed.
- **Run a lens:** `streamlit run lenses/position_sizer/app.py` → opens on
  `http://localhost:8501`. One lens per app; run the one you want.
- **Tests:** `python -m pytest tests/ -q` — offline, seeded, no network.
  - One file: `python -m pytest tests/test_risk.py -q`
  - One test: `python -m pytest tests/test_risk.py::test_cvar_ge_var -q`

There is no `PYTHONPATH` dance: each lens's `app.py` walks **two levels up** to
the repo root and inserts it on `sys.path`, so `core/` and `lenses/` import
cleanly under `streamlit run` from any cwd. Tests add the repo root themselves.
A lens moved to a different depth must have that bootstrap adjusted.

## Architecture

Data flows: **live fetch → pure risk math → thin lens UI.**

```
lenses/
  position_sizer/     # one lens = one self-contained app ("Calculadora de Riesgo")
    app.py            # ENTRY: page config, title, sys.path bootstrap, orchestration
    sidebar.py        # ALL inputs; returns a frozen Inputs dataclass (or None)
    view.py           # renders results into the main area from those Inputs
    glossary.py       # user-facing explainer copy (VaR/CVaR/ATR + caveats)
core/                 # pure, UI-free, self-contained — the portable heart, fully tested
  risk.py             # VaR / CVaR (historical + parametric), ATR, position sizing
  data.py             # Yahoo OHLC + intraday spot; raises DataError on failure
  charts.py           # Plotly figure builders (validated palette, light/dark aware)
  order.py            # BracketTicket — human-readable long entry + OCO stop
tests/                # test_risk.py, test_order.py  (cover core/ only)
```

- **`core/` is the boundary that matters.** Everything in `core/` is a pure
  function or a dataclass with no Streamlit import — so it's unit-testable and
  reusable. Lenses are thin: fetch → call `core` → render widgets. Do **not**
  put math or data logic in a lens.
- **Lenses are independent apps, not plugins.** No registry, no `Lens` base class,
  no shared entry point. Adding a lens touches no existing file. Two lenses never
  import each other — only `core/`.
- **Input and output are separate modules.** `sidebar.py` owns every widget and
  hands `view.py` a frozen `Inputs`; `view.py` reads no widget state. Keeping that
  split is what makes the main area pure output.
- **Sidebar selectboxes map key → label.** `stop_method` uses internal English keys
  (`"CVaR"`, `"VaR"`, `"ATR"`) with `format_func` supplying Spanish labels, so
  `view.py` branches on stable keys, not translated display text. Follow that
  pattern for any new choice widget.
- **Theme reaches charts through the lens, not the chart.** `core/charts.py` is
  pure and takes `theme="light"|"dark"`; `view.py` reads
  `st.get_option("theme.base")` and passes it in. A chart never queries Streamlit.

## Conventions

- **Adding a lens:** copy the `lenses/position_sizer/` shape — a package with
  `app.py` (page config + `sys.path` bootstrap + orchestration), `sidebar.py`
  (inputs → `Inputs`), and `view.py` (results). Nothing outside the new directory
  changes. Put its computation in `core/`, not the lens.
- **Inputs go in the sidebar,** the main area is results only. The pre-submit state
  shows an `st.info` telling the user what to fill in.
- **Charts:** build figures in `core/charts.py` as pure factory functions returning
  a Plotly `Figure`; the lens only calls `st.plotly_chart`. Colors come from the
  **validated palette** already in `charts.py` (categorical/status roles, checked
  for colorblind separation) — reuse those roles; don't hand-pick new hexes. Every
  chart is theme-aware (reads Streamlit's light/dark base).
- **Data fetches** go through `core/data.py`, are wrapped in `@st.cache_data(ttl=…)`
  at the lens boundary, and must fail into a friendly UI message (catch
  `DataError`), never a traceback. Yahoo's endpoints are unofficial and change —
  parse defensively.
- **Risk conventions:** VaR/CVaR are reported as **positive fractional losses**
  (`0.0174` = a 1.74% loss); CVaR ≥ VaR by construction; stops are for **long**
  positions (`entry > stop`). Sizing is risk-first: shares solved from a dollar (or
  %) risk budget, rounded **down** to the lot so actual risk never exceeds target.
  Horizon scaling is √t; both sizing entry points raise `ValueError` on a
  non-positive input or a stop at/above entry — lenses catch it and `st.error`.
- **Two sizing entry points, different contracts.** Both return `PositionSize`:
  `position_size(account_equity, …, risk_pct=)` knows the account, so
  `account_risk_amount` is the *budget* (pre-rounding) and `position_pct_of_account`
  is real. `size_from_risk_dollars(entry, stop, risk_dollars, …)` doesn't know the
  account, so `account_risk_amount` is the *actual* post-rounding risk and
  `position_pct_of_account` is **NaN** — don't render it without a guard.
  `stop_method` is always `""` from the constructors; the caller sets it.
- **Confidence claims must stay honest.** A 95% VaR is exceeded on ~5% of *historical
  days* — it is **not** a 95% win rate, a per-trade success probability, or a
  guaranteed loss cap. Over a multi-day hold the chance of touching the stop
  compounds; gaps can skip the stop entirely; all estimates are backward-looking.
  `glossary.py` states these limits explicitly and `view.py` repeats the day-vs-trade
  distinction next to the stop. Marketing copy may be confident about the *method*
  (institutional-grade, quantitative) but must never oversell the *number*.
- **Broker orders:** emit the **human-readable `BracketTicket`**, never a fabricated
  broker paste-string. thinkorswim's clipboard-order format is undocumented and
  unreliable; a plausible-but-wrong string could place a malformed order. If a
  verified auto-paste format is ever added, it must be confirmed against a real
  broker instance first.
- **Deprecations:** use current Streamlit APIs (e.g. `width="stretch"`, not
  `use_container_width`).

## Guardrails

- Keep SpyGlass **dependency-light and self-contained** — no new heavy deps, and
  never import from an external/parent project. Portability is the point.
- **Tests stay offline and seeded** — no network, no live API in tests. Mock or use
  synthetic series (see `tests/`).
- Verify changes end-to-end: `streamlit run lenses/<tool>/app.py` and click the
  flow, or drive it with `streamlit.testing.v1.AppTest` (it executes the app and
  exposes widgets — `at.sidebar.*` vs `at.main.*` proves widget placement, and
  monkeypatching the lens's `_load` keeps it offline), then run the pytest suite.
  The suite covers `core/` only, so a green run is never proof the UI renders.
- Don't commit or push unless asked.
