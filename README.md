# 🔭 SpyGlass

**Focused trading & research lenses on market risk.** Each tool is a *lens* — its
own small Streamlit app. Type a ticker in the sidebar, get a clean, actionable
answer. No code in sight, no install for the user.

The user-facing interface is in **Spanish**.

SpyGlass is **fully self-contained**: it depends only on `streamlit / pandas /
numpy / scipy / plotly / requests`, and pulls market data from public, keyless
Yahoo Finance endpoints. Drop it on Streamlit Community Cloud (or run it locally)
and it just works.

> ⚠️ Educational tools — **not financial advice.**

---

## Lenses

| Lens | Run it | What it does |
| --- | --- | --- |
| 🎯 **Calculadora de Riesgo** | `streamlit run lenses/position_sizer/app.py` | You choose the **dollars to risk**; it fetches the live price, computes **VaR / CVaR** and their stop prices (plus an ATR stop), sizes the position so a stop-out costs (about) your budget, draws the **return distribution** with VaR/CVaR markers, and prints a ready-to-enter **bracket order ticket**. |

*More lenses land here as they're built — each is one new directory (see [Adding a lens](#adding-a-lens)).*

---

## Quick start

```bash
pip install -r requirements.txt
streamlit run lenses/position_sizer/app.py
```

Opens at `http://localhost:8501`. Enter a ticker + your risk budget in the
sidebar, hit **Calcular**.

### Deploy (Streamlit Community Cloud)

1. Push this repo to GitHub.
2. On [share.streamlit.io](https://share.streamlit.io) → **New app** → pick the repo
   and the lens you want as the main file, e.g. `lenses/position_sizer/app.py`.
3. It builds from `requirements.txt` and gives you a public URL. Every push
   redeploys.

Each lens deploys as its own app (its own URL) from the same repo — point a second
app at a different `lenses/*/app.py`.

Free-tier apps sleep after inactivity (first visit wakes in a few seconds) — add a
keep-alive ping if you need it always-warm.

---

## The Calculadora de Riesgo, briefly

The risk-first rule: **decide the dollars you'll risk, and let that set your share
count.**

```
risk_per_share = entry − stop
shares         = risk_$ / risk_per_share
```

So a stop-out costs (about) your chosen dollar amount regardless of the ticker's
price or volatility. Shares round *down* to your lot size, so actual risk never
exceeds the budget. The **stop** is set three ways:

- **VaR** — `entry × (1 − VaR)`. The `1−confidence` historical loss quantile.
- **CVaR (tail)** — `entry × (1 − CVaR)`. The *average* loss in the worst
  `1−confidence` of days (Expected Shortfall) — fatter-tail-aware than VaR.
- **ATR** — `entry − multiple × ATR(14)`. A volatility-scaled stop (Wilder's ATR),
  computed from the daily high/low/close — no extra data source.

It shows historical VaR, CVaR, and parametric VaR side by side so you can see the
fat-tail gap (historical > parametric ⇒ tails), and renders a return-distribution
histogram with the VaR and CVaR percentiles marked.

### The order ticket

The tool prints a plain-text **bracket ticket** — a long entry plus a protective
**OCO stop** — that you enter in your broker or read the values from:

```
BUY  +38 SPY  @ MARKET
── OCO protective stop ──
SELL  -38 SPY  @ STOP 725.81   (VaR 95% · -1.74%)
```

> It is **not** an auto-paste string. thinkorswim's clipboard-order format is
> undocumented and exported templates don't reliably paste back, so emitting one
> risks a malformed order. The ticket is correct everywhere; enter the bracket
> yourself (in thinkorswim: *Buy Custom → With Stop*).

---

## Architecture

Built to grow: **each lens is its own standalone app**, so adding a tool never
touches an existing file. Lenses share only the pure `core/` package.

```
spyglass/
  lenses/
    position_sizer/      # tool #1 — one self-contained app
      app.py             # entry point: streamlit run lenses/position_sizer/app.py
      sidebar.py         # all inputs -> a frozen Inputs dataclass
      view.py            # renders the results from those Inputs
  core/                  # pure, UI-free, self-contained logic — the portable heart
    risk.py              # VaR, CVaR, ATR, position sizing
    data.py              # Yahoo OHLC + spot fetch (cached, graceful failure)
    charts.py            # Plotly figure builders (validated palette, theme-aware)
    order.py             # bracket order ticket
  tests/                 # offline, seeded tests for core
  requirements.txt
```

**Separation of concerns:** all math and data live in `core/` (pure functions, no
Streamlit — unit-testable and reusable); lenses are thin render layers. Within a
lens, `sidebar.py` owns every widget and `view.py` only draws results — so the
main area stays pure output. Keep it that way.

### Adding a lens

1. Create `lenses/your_tool/` with `app.py`, `sidebar.py` and `view.py` — copy the
   shape of `position_sizer/`.
2. Run it: `streamlit run lenses/your_tool/app.py`.

That's it — no registry to update, nothing else to touch. Put the heavy logic in
`core/`, not in the lens.

---

## Tests

```bash
python -m pytest tests/ -q
```

Offline and seeded — no network, no keys. Covers the risk math (VaR/CVaR ordering,
horizon scaling, ATR, sizing), the risk-dollar sizing formula, and the order ticket.

---

## Deployment notes

- **Caching:** data fetches use `@st.cache_data(ttl=300)`, so repeated interactions
  and concurrent users don't hammer Yahoo.
- **Resilience:** Yahoo's endpoint is unofficial and can rate-limit or change; the
  UI degrades to a friendly "try again" message rather than crashing.
- **Theme:** charts read the active Streamlit theme (light/dark) and swap palette
  steps accordingly.
