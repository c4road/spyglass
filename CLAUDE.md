# CLAUDE.md

Guidance for Claude Code (and other agents) working in the **SpyGlass** repo.

## What this is

SpyGlass is a small, self-contained **Streamlit** app of *lenses* — focused
trading/research tools over live market data. Each lens (e.g. the Position Sizer)
is one pluggable tool the user picks from the sidebar. It is a standalone product:
it depends on **nothing** outside its own `requirements.txt` and public Yahoo
Finance endpoints, and is meant to be deployed free on Streamlit Community Cloud
and given away.

**These are educational tools, not financial advice** — keep that framing in any
user-facing copy, and never present output as a recommendation to trade.

## Setup & commands

- **Python:** 3.10+ (uses `list[...]`/`X | Y` typing).
- **Install:** `pip install -r requirements.txt` (a virtualenv is recommended).
- **Run the app:** `streamlit run app.py` → opens on `http://localhost:8501`.
- **Tests:** `python -m pytest tests/ -q` — offline, seeded, no network.

There is no `PYTHONPATH` dance: `app.py` inserts its own directory on `sys.path`
so `lenses/` and `core/` import cleanly under `streamlit run`, and the tests add
the repo root themselves.

## Architecture

Data flows: **live fetch → pure risk math → thin lens UI.**

```
app.py            # entry: builds the sidebar from the registry, renders the chosen lens
lenses/
  base.py         # Lens ABC: name, icon, description, render()
  __init__.py     # LENSES = [...]  — the registry app.py reads (sidebar order)
  position_sizer.py
core/             # pure, UI-free, self-contained — the portable heart, fully tested
  risk.py         # VaR / CVaR (historical + parametric), ATR, position sizing
  data.py         # Yahoo OHLC + intraday spot; raises DataError on failure
  charts.py       # Plotly figure builders (validated palette, light/dark aware)
  order.py        # BracketTicket — human-readable long entry + OCO stop
tests/            # test_risk.py, test_order.py
```

- **`core/` is the boundary that matters.** Everything in `core/` is a pure
  function or a dataclass with no Streamlit import — so it's unit-testable and
  reusable. `lenses/` are thin: fetch → call `core` → render widgets. Do **not**
  put math or data logic in a lens.
- **The Lens registry is the extension point.** `app.py` and existing lenses never
  change when you add a tool.

## Conventions

- **Adding a lens:** create `lenses/<tool>.py` with a `Lens` subclass (set
  `name`/`icon`/`description`, implement `render()`); import it in
  `lenses/__init__.py` and append an instance to `LENSES`. Put its computation in
  `core/`, not the lens.
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
- Verify changes end-to-end: `streamlit run app.py` and click the flow, or drive it
  with `streamlit.testing.v1.AppTest` (it executes the app and exposes widgets),
  then run the pytest suite. A green suite alone isn't proof the UI renders.
- Don't commit or push unless asked.
