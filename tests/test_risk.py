"""Offline tests for SpyGlass core.risk — no network, seeded, deterministic."""

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core import risk


@pytest.fixture
def rets():
    rng = np.random.default_rng(0)
    return pd.Series(rng.normal(0.0003, 0.012, 400))


def test_cvar_ge_var(rets):
    var = risk.historical_var(rets, 0.95)
    cvar = risk.historical_cvar(rets, 0.95)
    assert cvar >= var > 0


def test_var_scales_with_horizon(rets):
    v1 = risk.historical_var(rets, 0.95, horizon_days=1)
    v4 = risk.historical_var(rets, 0.95, horizon_days=4)
    assert v4 == pytest.approx(v1 * 2, rel=1e-9)  # √4 = 2


def test_higher_confidence_higher_var(rets):
    assert risk.historical_var(rets, 0.99) > risk.historical_var(rets, 0.90)


def test_var_empty_returns_zero():
    assert risk.historical_var(pd.Series(dtype=float)) == 0.0
    assert risk.historical_cvar(pd.Series(dtype=float)) == 0.0


def test_atr_positive_and_price_scaled():
    idx = pd.date_range("2024-01-01", periods=50)
    close = pd.Series(np.linspace(100, 110, 50), index=idx)
    high = close * 1.01
    low = close * 0.99
    atr = risk.average_true_range(high, low, close, period=14)
    assert atr > 0
    # roughly the ~2% H-L band on a ~105 price
    assert 1.0 < atr < 4.0


def test_position_size_risks_exactly_budget():
    ps = risk.position_size(25_000, entry_price=100.0, stop_price=96.0, risk_pct=0.01)
    # 1% of 25k = $250 risk; $4 risk/share -> 62.5 -> 62 shares
    assert ps.risk_per_share == pytest.approx(4.0)
    assert ps.shares_rounded == 62
    assert ps.shares_rounded * ps.risk_per_share <= ps.account_risk_amount + ps.risk_per_share


def test_position_size_lot_rounding():
    ps = risk.position_size(25_000, 100.0, 96.0, risk_pct=0.01, lot=10)
    assert ps.shares_rounded % 10 == 0
    assert ps.shares_rounded == 60


def test_position_size_rejects_bad_stop():
    with pytest.raises(ValueError):
        risk.position_size(25_000, 100.0, 105.0)  # stop above entry (long)


def test_position_size_rejects_bad_inputs():
    with pytest.raises(ValueError):
        risk.position_size(0, 100.0, 96.0)
    with pytest.raises(ValueError):
        risk.position_size(25_000, 100.0, 96.0, risk_pct=1.5)


def test_atr_and_var_stops():
    assert risk.atr_stop(100.0, atr=2.0, multiple=2.0) == 96.0
    assert risk.var_stop(100.0, var_fraction=0.03) == pytest.approx(97.0)
