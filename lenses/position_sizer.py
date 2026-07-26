"""Position Sizer lens — risk-based sizing with VaR/CVaR and ATR stops.

Answers the trader's first question: *how many shares can I buy such that, if my
stop is hit, I lose only X% of my account?* — with the stop itself derived from a
real volatility measure (ATR) or a tail-loss measure (VaR/CVaR), not a guess.

Thin UI only: all math is in ``core.risk``; market data in ``core.data``.
"""

from __future__ import annotations

import streamlit as st

from lenses.base import Lens
from core.data import fetch_ohlc, fetch_spot, DataError
from core import risk
from core.charts import return_distribution
from core.order import build_bracket


# Cache fetches so repeated interactions (and concurrent users) don't hammer
# Yahoo; TTL keeps it fresh enough for sizing decisions.
@st.cache_data(ttl=300, show_spinner=False)
def _load(symbol: str):
    ohlc = fetch_ohlc(symbol, lookback_days=400)
    quote = fetch_spot(symbol)
    return ohlc, quote


class PositionSizerLens(Lens):
    name = "Position Sizer"
    icon = "🎯"
    description = (
        "Size a position so a stop-out costs a fixed % of your account — with the "
        "stop set by ATR or tail-risk (VaR/CVaR), not a guess."
    )

    def render(self) -> None:
        st.subheader(f"{self.icon} {self.name}")
        st.caption(self.description)

        with st.form("sizer"):
            c1, c2, c3 = st.columns(3)
            symbol = c1.text_input("Ticker", value="SPY").strip().upper()
            risk_dollars = c2.number_input(
                "$ to risk on this trade", min_value=10.0, value=500.0, step=50.0,
                help="How much you'll lose if the stop is hit. Position size is solved from this.",
            )
            confidence = c3.selectbox(
                "VaR/CVaR confidence", [0.90, 0.95, 0.99], index=1,
                format_func=lambda x: f"{int(x*100)}%",
            )

            c4, c5, c6 = st.columns(3)
            stop_method = c4.selectbox(
                "Stop method", ["VaR", "CVaR (tail)", "ATR"], index=1,
            )
            atr_mult = c5.number_input(
                "ATR multiple", min_value=0.5, max_value=6.0, value=2.0, step=0.5,
                help="Stop = entry − (multiple × ATR). Used only for the ATR method.",
            )
            lot = c6.number_input("Round to lot size", min_value=1, value=1, step=1)
            submitted = st.form_submit_button("Compute", width="stretch")

        if not submitted:
            st.info("Enter your ticker and $ to risk, then click **Compute**.")
            return

        try:
            with st.spinner(f"Fetching {symbol}…"):
                ohlc, quote = _load(symbol)
        except DataError as exc:
            st.error(f"Couldn't load market data for **{symbol}**: {exc}")
            st.caption("Check the ticker, or try again in a moment (Yahoo rate limits).")
            return

        entry = quote.price
        rets = risk.daily_returns(ohlc["close"])
        atr = risk.average_true_range(ohlc["high"], ohlc["low"], ohlc["close"], period=14)
        var = risk.historical_var(rets, confidence=confidence)
        cvar = risk.historical_cvar(rets, confidence=confidence)
        pvar = risk.parametric_var(rets, confidence=confidence)

        # Stop prices for every method (shown side by side; the chosen one sizes).
        var_stop_px = risk.var_stop(entry, var)
        cvar_stop_px = risk.var_stop(entry, cvar)
        atr_stop_px = risk.atr_stop(entry, atr, multiple=atr_mult)

        if stop_method == "ATR":
            stop, stop_label = atr_stop_px, f"ATR×{atr_mult:g}"
        elif stop_method == "CVaR (tail)":
            stop, stop_label = cvar_stop_px, f"CVaR {int(confidence*100)}%"
        else:  # VaR
            stop, stop_label = var_stop_px, f"VaR {int(confidence*100)}%"

        try:
            ps = risk.size_from_risk_dollars(entry, stop, risk_dollars, lot=int(lot))
        except ValueError as exc:
            st.error(f"Can't size this position: {exc}")
            return

        # --- price & stop panel ---
        st.markdown("### Price & stops")
        p1, p2, p3 = st.columns(3)
        p1.metric("Current price", f"${entry:,.2f}", help=f"live, as of {quote.as_of}")
        p2.metric(
            f"VaR {int(confidence*100)}%", f"{var*100:.2f}%",
            help="Historical 1-day loss quantile",
        )
        p2.caption(f"stop **${var_stop_px:,.2f}**")
        p3.metric(
            f"CVaR {int(confidence*100)}%", f"{cvar*100:.2f}%",
            help="Average loss beyond VaR (Expected Shortfall)",
        )
        p3.caption(f"stop **${cvar_stop_px:,.2f}**")

        # --- sizing result ---
        st.markdown("### Position")
        r1, r2, r3 = st.columns(3)
        r1.metric("Buy", f"{ps.shares_rounded:,} sh", help=f"{ps.shares:,.1f} before rounding")
        r2.metric("Chosen stop", f"${ps.stop_price:,.2f}",
                  f"−{ps.risk_per_share/entry*100:.2f}%  ({stop_label})")
        r3.metric("Position value", f"${ps.position_value:,.0f}")
        r4, r5, _ = st.columns(3)
        r4.metric("Risk if stopped", f"${ps.account_risk_amount:,.0f}",
                  help=f"target was ${risk_dollars:,.0f}; differs only by lot rounding")
        r5.metric("Risk / share", f"${ps.risk_per_share:,.2f}")

        # --- copy-paste bracket ticket ---
        st.markdown("### Order ticket")
        ticket = build_bracket(symbol, ps.shares_rounded, entry, ps.stop_price, stop_label)
        st.code(ticket.as_text(), language=None)
        st.caption(
            "A long entry + protective **OCO stop**. Enter it in your broker (thinkorswim: "
            "*Buy Custom → With Stop*), or grab the values by hand. Not an auto-paste string — "
            "read the numbers and place the bracket yourself."
        )

        # --- return distribution with VaR / CVaR markers ---
        st.markdown("### Return distribution")
        st.caption(
            f"Daily returns over {len(rets)} days. The red tail is the worst "
            f"{int((1-confidence)*100)}% of days; **VaR** marks its edge, **CVaR** the "
            "average loss inside it (deeper in the tail)."
        )
        theme = st.get_option("theme.base") or "light"
        fig = return_distribution(rets, var, cvar, confidence=confidence, theme=theme)
        st.plotly_chart(fig, width="stretch")

        # --- risk context table ---
        with st.expander("Volatility & tail-risk detail"):
            st.write(
                {
                    "Entry (live)": f"${entry:,.2f}",
                    "ATR(14)": f"${atr:,.2f} ({atr/entry*100:.2f}%)  → stop ${atr_stop_px:,.2f}",
                    f"Historical VaR {int(confidence*100)}%": f"{var*100:.2f}%  → stop ${var_stop_px:,.2f}",
                    f"CVaR {int(confidence*100)}% (tail)": f"{cvar*100:.2f}%  → stop ${cvar_stop_px:,.2f}",
                    f"Parametric VaR {int(confidence*100)}%": f"{pvar*100:.2f}%",
                }
            )
            st.caption(
                "CVaR ≥ VaR (it's the *average* loss beyond VaR). Historical > parametric "
                "usually means fat tails. All are 1-day, daily-return based."
            )

        st.caption(
            "⚠️ Educational tool, not financial advice. Live data from Yahoo; sizes assume "
            "a long position and that you honor the stop."
        )
