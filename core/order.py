"""Human-readable bracket order ticket builder — pure, no Streamlit.

Produces an unambiguous, copy-pasteable *text* ticket for a long entry plus an
OCO (one-cancels-other) protective stop, in the shape a broker bracket takes.

Deliberately NOT a thinkorswim clipboard-paste string: ToS's paste format is
undocumented and, per the ToS community, exported templates don't reliably paste
back into a working order. Emitting a fake paste-string risks a malformed order
in the user's account. So we emit a clean text ticket the user reads/enters, or
grabs values from — correct everywhere, misleading nowhere.
"""

from dataclasses import dataclass


@dataclass
class BracketTicket:
    """A long entry + protective OCO stop, ready to render as text."""

    symbol: str
    shares: int
    entry_price: float
    stop_price: float
    stop_label: str          # e.g. "VaR 95%", "CVaR 95%", "ATR×2"
    entry_type: str = "MARKET"  # "MARKET" or "LIMIT"

    @property
    def risk_per_share(self) -> float:
        return self.entry_price - self.stop_price

    @property
    def stop_pct(self) -> float:
        return (self.entry_price - self.stop_price) / self.entry_price

    @property
    def dollar_risk(self) -> float:
        return self.shares * self.risk_per_share

    @property
    def position_value(self) -> float:
        return self.shares * self.entry_price

    def as_text(self) -> str:
        """Render the ticket as a monospace-friendly block.

        Entry can be MARKET or a LIMIT at the entry price. The stop is a SELL
        STOP for the same quantity (the OCO protective leg).
        """
        entry_line = (
            f"BUY  +{self.shares} {self.symbol}  @ MARKET"
            if self.entry_type == "MARKET"
            else f"BUY  +{self.shares} {self.symbol}  @ LMT {self.entry_price:.2f}"
        )
        return (
            f"{entry_line}\n"
            f"── OCO protective stop ──\n"
            f"SELL  -{self.shares} {self.symbol}  @ STOP {self.stop_price:.2f}   "
            f"({self.stop_label} · -{self.stop_pct * 100:.2f}%)"
        )


def build_bracket(
    symbol: str,
    shares: int,
    entry_price: float,
    stop_price: float,
    stop_label: str,
    entry_type: str = "MARKET",
) -> BracketTicket:
    """Construct a :class:`BracketTicket` (thin wrapper for a clean call site)."""
    return BracketTicket(
        symbol=symbol.upper(),
        shares=int(shares),
        entry_price=float(entry_price),
        stop_price=float(stop_price),
        stop_label=stop_label,
        entry_type=entry_type,
    )
