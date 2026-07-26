"""Self-contained risk primitives for SpyGlass — VaR, CVaR, ATR, position sizing.

SpyGlass is a standalone product (destined for its own repo), so this module
deliberately depends on NOTHING from the earningspy platform — only numpy/pandas.
When SpyGlass is stripped out, `core/` travels with it unchanged.

All functions are pure (no I/O, no Streamlit) and unit-testable.

Conventions
-----------
- Returns are simple daily returns unless noted.
- ``confidence`` is the VaR confidence (0.95 → 95%); the loss tail is the lower
  ``1 - confidence`` quantile.
- VaR/CVaR are reported as POSITIVE fractional losses (0.023 = a 2.3% loss),
  the trader-friendly convention ("my 1-day 95% VaR is 2.3%").
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def daily_returns(prices: pd.Series) -> pd.Series:
    """Simple daily returns from a price series, NaNs dropped."""
    return pd.Series(prices).astype(float).pct_change().dropna()


def historical_var(
    returns: pd.Series,
    confidence: float = 0.95,
    horizon_days: int = 1,
) -> float:
    """Historical (non-parametric) VaR as a positive fractional loss.

    The ``1 - confidence`` empirical quantile of returns, scaled to ``horizon_days``
    by √t. Returns 0.0 if there is no data.
    """
    r = pd.Series(returns).dropna()
    if r.empty:
        return 0.0
    q = np.percentile(r, (1.0 - confidence) * 100.0)
    var_1d = max(0.0, -float(q))  # positive loss
    return var_1d * np.sqrt(horizon_days)


def historical_cvar(
    returns: pd.Series,
    confidence: float = 0.95,
    horizon_days: int = 1,
) -> float:
    """Historical CVaR / Expected Shortfall — mean loss BEYOND the VaR threshold.

    The average of returns at or below the ``1 - confidence`` quantile, as a
    positive fractional loss, √t-scaled. CVaR ≥ VaR by construction.
    """
    r = pd.Series(returns).dropna()
    if r.empty:
        return 0.0
    q = np.percentile(r, (1.0 - confidence) * 100.0)
    tail = r[r <= q]
    if tail.empty:
        cvar_1d = max(0.0, -float(q))
    else:
        cvar_1d = max(0.0, -float(tail.mean()))
    return cvar_1d * np.sqrt(horizon_days)


def parametric_var(
    returns: pd.Series,
    confidence: float = 0.95,
    horizon_days: int = 1,
) -> float:
    """Normal-distribution (parametric) VaR as a positive fractional loss.

    ``VaR = -(μ + z·σ)`` at the ``1 - confidence`` z-score, √t-scaled. Shown
    alongside historical VaR so the user sees the fat-tail gap between them.
    """
    from scipy.stats import norm

    r = pd.Series(returns).dropna()
    if len(r) < 2:
        return 0.0
    mu, sigma = float(r.mean()), float(r.std(ddof=1))
    z = norm.ppf(1.0 - confidence)  # negative
    var_1d = max(0.0, -(mu + z * sigma))
    return var_1d * np.sqrt(horizon_days)


def average_true_range(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> float:
    """Wilder's Average True Range (ATR) over ``period`` bars, in price units.

    True Range = max(H−L, |H−prev_close|, |L−prev_close|); ATR is the Wilder
    (EMA-style, α = 1/period) smoothing of TR. Returns the latest ATR value.
    """
    high = pd.Series(high).astype(float)
    low = pd.Series(low).astype(float)
    close = pd.Series(close).astype(float)

    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1).dropna()
    if tr.empty:
        return 0.0
    # Wilder smoothing == EMA with alpha = 1/period.
    atr = tr.ewm(alpha=1.0 / period, adjust=False, min_periods=1).mean()
    return float(atr.iloc[-1])


@dataclass
class PositionSize:
    """Result of a risk-based position sizing calculation.

    All monetary fields are in account currency; ``shares`` is unrounded (the
    caller rounds to a lot). ``risk_per_share`` is the stop distance used.
    """

    shares: float
    shares_rounded: int
    position_value: float
    account_risk_amount: float     # dollars risked if the stop is hit
    risk_per_share: float          # entry − stop (long) distance
    stop_price: float
    stop_method: str
    position_pct_of_account: float  # position_value / account_equity


def position_size(
    account_equity: float,
    entry_price: float,
    stop_price: float,
    risk_pct: float = 0.01,
    lot: int = 1,
) -> PositionSize:
    """Size a position so a stop-out loses exactly ``risk_pct`` of the account.

    The canonical risk-first rule:

        shares = (account_equity · risk_pct) / (entry − stop)

    so the dollar loss at the stop equals your risk budget regardless of the
    instrument's price or volatility.

    Parameters
    ----------
    account_equity : float
        Total account value.
    entry_price, stop_price : float
        Entry and stop-loss prices (``entry > stop`` for a long).
    risk_pct : float, default 0.01
        Fraction of the account to risk on this trade (0.01 = 1%).
    lot : int, default 1
        Round shares down to a multiple of this (1 = whole shares).

    Raises
    ------
    ValueError
        If inputs are non-positive or the stop is not below entry.
    """
    if account_equity <= 0 or entry_price <= 0:
        raise ValueError("account_equity and entry_price must be positive")
    if not (0.0 < risk_pct <= 1.0):
        raise ValueError("risk_pct must be in (0, 1]")
    risk_per_share = entry_price - stop_price
    if risk_per_share <= 0:
        raise ValueError("stop_price must be below entry_price for a long")

    account_risk_amount = account_equity * risk_pct
    raw_shares = account_risk_amount / risk_per_share
    shares_rounded = int(raw_shares // lot) * lot
    position_value = shares_rounded * entry_price

    return PositionSize(
        shares=raw_shares,
        shares_rounded=shares_rounded,
        position_value=position_value,
        account_risk_amount=account_risk_amount,
        risk_per_share=risk_per_share,
        stop_price=stop_price,
        stop_method="",  # set by caller (e.g. "ATR×2", "CVaR 95%")
        position_pct_of_account=position_value / account_equity,
    )


def size_from_risk_dollars(
    entry_price: float,
    stop_price: float,
    risk_dollars: float,
    lot: int = 1,
) -> PositionSize:
    """Size a long from a fixed DOLLAR risk budget and a stop.

    The user's model: "I'm willing to lose ``risk_dollars`` if stopped out."

        risk_per_share = entry − stop
        shares         = risk_dollars / risk_per_share

    so the loss at the stop equals ``risk_dollars`` (before lot rounding).
    ``position_pct_of_account`` is left as NaN here — this entry point doesn't
    know the account size; the caller can fill it if desired.

    Raises
    ------
    ValueError
        If prices/risk are non-positive or the stop is not below entry.
    """
    if entry_price <= 0 or risk_dollars <= 0:
        raise ValueError("entry_price and risk_dollars must be positive")
    risk_per_share = entry_price - stop_price
    if risk_per_share <= 0:
        raise ValueError("stop_price must be below entry_price for a long")

    raw_shares = risk_dollars / risk_per_share
    shares_rounded = int(raw_shares // lot) * lot
    position_value = shares_rounded * entry_price

    return PositionSize(
        shares=raw_shares,
        shares_rounded=shares_rounded,
        position_value=position_value,
        account_risk_amount=shares_rounded * risk_per_share,  # actual $ risk after rounding
        risk_per_share=risk_per_share,
        stop_price=stop_price,
        stop_method="",
        position_pct_of_account=float("nan"),
    )


def atr_stop(entry_price: float, atr: float, multiple: float = 2.0) -> float:
    """Long stop from an ATR band: ``entry − multiple·ATR`` (price units)."""
    return entry_price - multiple * atr


def var_stop(entry_price: float, var_fraction: float) -> float:
    """Long stop from a VaR/CVaR fraction: ``entry·(1 − var_fraction)``.

    ``var_fraction`` is a positive fractional loss (e.g. CVaR 0.032 → stop 3.2%
    below entry). Ties the stop to the tail-loss estimate rather than a raw ATR.
    """
    return entry_price * (1.0 - var_fraction)
