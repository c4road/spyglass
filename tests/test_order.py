"""Tests for the bracket ticket builder and risk-dollar sizing."""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core import risk
from core.order import build_bracket


def test_size_from_risk_dollars_matches_formula():
    """shares = risk_$ / (entry - stop); loss at stop ~= risk budget."""
    entry, stop, risk_d = 738.66, 725.81, 500.0
    ps = risk.size_from_risk_dollars(entry, stop, risk_d)
    assert ps.risk_per_share == pytest.approx(entry - stop)
    assert ps.shares_rounded == 38          # 500 / 12.85 = 38.9 -> 38
    assert ps.account_risk_amount <= risk_d  # rounding down never exceeds budget
    assert ps.account_risk_amount == pytest.approx(38 * (entry - stop))


def test_size_from_risk_dollars_lot():
    ps = risk.size_from_risk_dollars(100.0, 96.0, 500.0, lot=10)
    assert ps.shares_rounded % 10 == 0
    assert ps.shares_rounded == 120  # 500/4 = 125 -> floor to 120


def test_size_from_risk_dollars_rejects_bad():
    with pytest.raises(ValueError):
        risk.size_from_risk_dollars(100.0, 105.0, 500.0)  # stop above entry
    with pytest.raises(ValueError):
        risk.size_from_risk_dollars(100.0, 96.0, 0.0)      # zero risk


def test_bracket_ticket_fields():
    t = build_bracket("spy", 38, 738.66, 725.81, "VaR 95%")
    assert t.symbol == "SPY"
    assert t.risk_per_share == pytest.approx(12.85)
    assert t.stop_pct == pytest.approx(12.85 / 738.66)
    assert t.dollar_risk == pytest.approx(38 * 12.85)
    assert t.position_value == pytest.approx(38 * 738.66)


def test_bracket_ticket_text_market_and_limit():
    mkt = build_bracket("SPY", 38, 738.66, 725.81, "VaR 95%", entry_type="MARKET")
    txt = mkt.as_text()
    assert "BUY  +38 SPY  @ MARKET" in txt
    assert "SELL  -38 SPY  @ STOP 725.81" in txt
    assert "VaR 95%" in txt

    lmt = build_bracket("SPY", 38, 738.66, 725.81, "VaR 95%", entry_type="LIMIT")
    assert "BUY  +38 SPY  @ LMT 738.66" in lmt.as_text()
