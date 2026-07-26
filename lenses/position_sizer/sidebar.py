"""Sidebar inputs for the Position Sizer lens.

All user input lives here so the main area is pure output. ``render_sidebar``
returns a frozen :class:`Inputs` when the form is submitted, or ``None`` while
the user hasn't run it yet — so the caller never inspects widget state.
"""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st


@dataclass(frozen=True)
class Inputs:
    """One submitted run of the sizer form."""

    symbol: str
    risk_dollars: float
    confidence: float
    stop_method: str  # "VaR" | "CVaR" | "ATR"
    atr_mult: float
    lot: int


#: Stop-method options: internal key -> Spanish label shown to the user.
_STOP_METHODS = {
    "CVaR": "CVaR (cola)",
    "VaR": "VaR",
    "ATR": "ATR",
}


def render_sidebar() -> Inputs | None:
    """Draw the sidebar form. Returns ``Inputs`` on submit, else ``None``."""
    st.sidebar.title("🔭 SpyGlass")
    st.sidebar.caption(
        "Calculadora de Riesgo  \nby [EarningSpy.ai](https://earningspy.ai/)"
    )
    st.sidebar.divider()

    with st.sidebar.form("sizer"):
        symbol = st.text_input("Ticker", value="SPY").strip().upper()

        risk_dollars = st.number_input(
            "$ a arriesgar en esta operación",
            min_value=10.0,
            value=500.0,
            step=50.0,
            help=(
                "Cuánto perdés si salta el stop. El tamaño de la posición se "
                "despeja a partir de esto."
            ),
        )

        confidence = st.selectbox(
            "Confianza VaR/CVaR",
            [0.90, 0.95, 0.99],
            index=1,
            format_func=lambda x: f"{int(x * 100)}%",
        )

        stop_method = st.selectbox(
            "Método de stop",
            list(_STOP_METHODS),
            index=0,
            format_func=lambda k: _STOP_METHODS[k],
            help=(
                "VaR/CVaR atan el stop a la pérdida de cola histórica; ATR lo "
                "escala por volatilidad."
            ),
        )

        atr_mult = st.number_input(
            "Múltiplo de ATR",
            min_value=0.5,
            max_value=6.0,
            value=2.0,
            step=0.5,
            help="Stop = entrada − (múltiplo × ATR). Sólo se usa con el método ATR.",
        )

        lot = st.number_input("Redondear al lote", min_value=1, value=1, step=1)

        submitted = st.form_submit_button("Calcular", width="stretch")

    st.sidebar.divider()
    st.sidebar.caption("Herramientas educativas · no es asesoría financiera.")

    if not submitted:
        return None

    return Inputs(
        symbol=symbol,
        risk_dollars=float(risk_dollars),
        confidence=float(confidence),
        stop_method=stop_method,
        atr_mult=float(atr_mult),
        lot=int(lot),
    )
