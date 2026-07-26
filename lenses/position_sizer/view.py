"""Position Sizer — results rendering (main area).

Answers the trader's first question: *how many shares can I buy such that, if my
stop is hit, I lose only X?* — with the stop itself derived from a real
volatility measure (ATR) or a tail-loss measure (VaR/CVaR), not a guess.

Thin UI only: all math is in ``core.risk``; market data in ``core.data``. Inputs
arrive already validated from ``sidebar.py``. User-facing copy is Spanish.
"""

from __future__ import annotations

import streamlit as st

from core import risk
from core.charts import return_distribution
from core.data import DataError, fetch_ohlc, fetch_spot
from core.order import build_bracket
from lenses.position_sizer.sidebar import Inputs


# Cache fetches so repeated interactions (and concurrent users) don't hammer
# Yahoo; TTL keeps it fresh enough for sizing decisions.
@st.cache_data(ttl=300, show_spinner=False)
def _load(symbol: str):
    ohlc = fetch_ohlc(symbol, lookback_days=400)
    quote = fetch_spot(symbol)
    return ohlc, quote


def render_results(inp: Inputs) -> None:
    """Fetch, compute and draw everything below the header."""
    try:
        with st.spinner(f"Buscando datos de {inp.symbol}…"):
            ohlc, quote = _load(inp.symbol)
    except DataError as exc:
        st.error(f"No se pudieron cargar los datos de mercado de **{inp.symbol}**: {exc}")
        st.caption(
            "Revisá el ticker, o probá de nuevo en un momento (Yahoo limita las consultas)."
        )
        return

    pct = int(inp.confidence * 100)
    entry = quote.price
    rets = risk.daily_returns(ohlc["close"])
    atr = risk.average_true_range(ohlc["high"], ohlc["low"], ohlc["close"], period=14)
    var = risk.historical_var(rets, confidence=inp.confidence)
    cvar = risk.historical_cvar(rets, confidence=inp.confidence)
    pvar = risk.parametric_var(rets, confidence=inp.confidence)

    # Stop prices for every method (shown side by side; the chosen one sizes).
    var_stop_px = risk.var_stop(entry, var)
    cvar_stop_px = risk.var_stop(entry, cvar)
    atr_stop_px = risk.atr_stop(entry, atr, multiple=inp.atr_mult)

    if inp.stop_method == "ATR":
        stop, stop_label = atr_stop_px, f"ATR×{inp.atr_mult:g}"
    elif inp.stop_method == "CVaR":
        stop, stop_label = cvar_stop_px, f"CVaR {pct}%"
    else:  # VaR
        stop, stop_label = var_stop_px, f"VaR {pct}%"

    try:
        ps = risk.size_from_risk_dollars(entry, stop, inp.risk_dollars, lot=inp.lot)
    except ValueError as exc:
        st.error(f"No se puede dimensionar esta posición: {exc}")
        return

    # Rounding down to the lot can land on zero shares (budget too chico for one
    # lot). Sizing is correct, but there's no position to show — bail out before
    # rendering an absurd "+0 acciones" order ticket.
    if ps.shares_rounded == 0:
        min_budget = ps.risk_per_share * inp.lot
        st.warning(
            f"Con **${inp.risk_dollars:,.0f}** de riesgo no alcanza para comprar "
            f"ni un lote de **{inp.lot:,}** {'acción' if inp.lot == 1 else 'acciones'} "
            f"de **{inp.symbol}**."
        )
        st.markdown(
            f"El stop elegido ({stop_label}) queda a **${ps.risk_per_share:,.2f}** "
            f"por acción, así que necesitás al menos **${min_budget:,.2f}** para "
            f"un lote de {inp.lot:,}."
        )
        st.caption(
            "Subí el monto a arriesgar, reducí el tamaño del lote, o elegí un stop "
            "más ajustado (VaR en vez de CVaR, o un múltiplo de ATR menor)."
        )
        return

    # --- price & stop panel ---
    st.markdown("### Precio y stops")
    p1, p2, p3 = st.columns(3)
    p1.metric("Precio actual", f"${entry:,.2f}", help=f"en vivo, al {quote.as_of}")
    p2.metric(
        f"VaR {pct}%", f"{var * 100:.2f}%",
        help="Cuantil histórico de pérdida a 1 día",
    )
    p2.caption(f"stop **${var_stop_px:,.2f}**")
    p3.metric(
        f"CVaR {pct}%", f"{cvar * 100:.2f}%",
        help="Pérdida promedio más allá del VaR (Expected Shortfall)",
    )
    p3.caption(f"stop **${cvar_stop_px:,.2f}**")

    # --- sizing result ---
    st.markdown("### Posición")
    r1, r2, r3 = st.columns(3)
    r1.metric(
        "Comprar", f"{ps.shares_rounded:,} acc.",
        help=f"{ps.shares:,.1f} antes de redondear",
    )
    r2.metric(
        "Stop elegido", f"${ps.stop_price:,.2f}",
        f"−{ps.risk_per_share / entry * 100:.2f}%  ({stop_label})",
    )
    r3.metric("Valor de la posición", f"${ps.position_value:,.0f}")
    r4, r5, _ = st.columns(3)
    r4.metric(
        "Pérdida si salta el stop", f"${ps.account_risk_amount:,.0f}",
        help=(
            f"el objetivo era ${inp.risk_dollars:,.0f}; la diferencia es sólo por "
            "el redondeo al lote"
        ),
    )
    r5.metric("Riesgo por acción", f"${ps.risk_per_share:,.2f}")

    # Spell out what the confidence level does and does NOT promise, right where
    # the user reads the stop. See glossary.py for the full caveats.
    if inp.stop_method in ("VaR", "CVaR"):
        tail = int(round((1 - inp.confidence) * 100))
        st.caption(
            f"Este stop está en el nivel **{stop_label}**: históricamente, sólo el "
            f"**{tail}%** de las ruedas tuvo una caída diaria que lo hubiera tocado "
            f"— las otras **{pct}%** no. Ojo: es sobre *días* históricos, no una "
            f"probabilidad de éxito de la operación (si la sostenés varios días, el "
            "riesgo de tocarlo se acumula)."
        )
    else:
        st.caption(
            f"Este stop está a **{inp.atr_mult:g}×** el movimiento diario típico "
            f"(ATR de 14 ruedas). Cuanto mayor el múltiplo, más ruido tolerás "
            "antes de salir."
        )

    # --- copy-paste bracket ticket ---
    st.markdown("### Orden")
    ticket = build_bracket(inp.symbol, ps.shares_rounded, entry, ps.stop_price, stop_label)
    st.code(ticket.as_text(), language=None)
    st.caption(
        "Una compra más un **stop de protección OCO**. Cargalo en tu bróker "
        "(en thinkorswim: *Buy Custom → With Stop*), o tomá los valores a mano. "
        "No es un texto para pegar automáticamente — leé los números y armá la "
        "orden vos mismo."
    )

    # --- return distribution with VaR / CVaR markers ---
    st.markdown("### Distribución de retornos")
    st.caption(
        f"Retornos diarios de {len(rets)} días. La cola roja es el peor "
        f"{int((1 - inp.confidence) * 100)}% de los días; **VaR** marca su borde y "
        "**CVaR** la pérdida promedio dentro de ella (más adentro de la cola)."
    )
    theme = st.get_option("theme.base") or "light"
    fig = return_distribution(rets, var, cvar, confidence=inp.confidence, theme=theme)
    st.plotly_chart(fig, width="stretch")

    # --- risk context table ---
    with st.expander("Detalle de volatilidad y riesgo de cola"):
        st.write(
            {
                "Entrada (en vivo)": f"${entry:,.2f}",
                "ATR(14)": (
                    f"${atr:,.2f} ({atr / entry * 100:.2f}%)  → stop ${atr_stop_px:,.2f}"
                ),
                f"VaR histórico {pct}%": f"{var * 100:.2f}%  → stop ${var_stop_px:,.2f}",
                f"CVaR {pct}% (cola)": f"{cvar * 100:.2f}%  → stop ${cvar_stop_px:,.2f}",
                f"VaR paramétrico {pct}%": f"{pvar * 100:.2f}%",
            }
        )
        st.caption(
            "CVaR ≥ VaR (es el promedio de las pérdidas que superan el VaR). Que el "
            "histórico supere al paramétrico suele indicar colas pesadas. Todos son "
            "a 1 día, sobre retornos diarios."
        )

    st.caption(
        "⚠️ Herramienta educativa, no es asesoría financiera. Datos en vivo de Yahoo; "
        "los cálculos asumen una posición larga, son retrospectivos (sobre el "
        "historial del activo) y suponen que respetás el stop. Un *gap* de apertura "
        "puede saltearlo."
    )
