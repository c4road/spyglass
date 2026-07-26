# 🔭 SpyGlass

**Focused trading & research lenses on market risk.** A small Streamlit app where
each tool is a *lens* — pick one from the sidebar, type a ticker, get a clean,
actionable answer. No code in sight, no install for the user.

SpyGlass is **fully self-contained**: it depends only on `streamlit / pandas /
numpy / scipy / plotly / requests`, and pulls market data from public, keyless
Yahoo Finance endpoints. Drop it on Streamlit Community Cloud (or run it locally)
and it just works.

> ⚠️ Educational tools — **not financial advice.**

---

## Lenses

| Lens | What it does |
| --- | --- |
| 🎯 **Position Sizer** | You choose the **dollars to risk**; it fetches the live price, computes **VaR / CVaR** and their stop prices (plus an ATR stop), sizes the position so a stop-out costs (about) your budget, draws the **return distribution** with VaR/CVaR markers, and prints a ready-to-enter **bracket order ticket**. |

*More lenses land here as they're built — each is one new file (see [Adding a lens](#adding-a-lens)).*

---

## Quick start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opens at `http://localhost:8501`. Pick a lens, enter a ticker + your risk budget,
hit **Compute**.

### Deploy (Streamlit Community Cloud)

1. Push this repo to GitHub.
2. On [share.streamlit.io](https://share.streamlit.io) → **New app** → pick the repo
   and `app.py`.
3. It builds from `requirements.txt` and gives you a public URL. Every push
   redeploys.

Free-tier apps sleep after inactivity (first visit wakes in a few seconds) — add a
keep-alive ping if you need it always-warm.

---

## The Position Sizer, briefly

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

Built to grow: adding a tool never touches `app.py` or any other lens.

```
spyglass/
  app.py                 # entry: sidebar picks a lens, renders it (never changes)
  lenses/
    base.py              # the Lens contract (name, icon, render())
    __init__.py          # LENSES registry (sidebar order)
    position_sizer.py    # tool #1
  core/                  # pure, UI-free, self-contained logic — the portable heart
    risk.py              # VaR, CVaR, ATR, position sizing
    data.py              # Yahoo OHLC + spot fetch (cached, graceful failure)
    charts.py            # Plotly figure builders (validated palette, theme-aware)
    order.py             # bracket order ticket
  tests/                 # offline, seeded tests for core
  requirements.txt
```

**Separation of concerns:** all math and data live in `core/` (pure functions, no
Streamlit — unit-testable and reusable); lenses are thin render layers. Keep it
that way.

### Adding a lens

1. Write `lenses/your_tool.py` with a class that subclasses `Lens` (set `name`,
   `icon`, `description`; implement `render()`).
2. Import it in `lenses/__init__.py` and append an instance to `LENSES`.

That's it — the sidebar and routing pick it up automatically. Put the heavy logic
in `core/`, not in the lens.

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
