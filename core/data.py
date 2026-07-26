"""Self-contained market-data fetch for SpyGlass (Yahoo Finance v8 chart API).

Standalone by design — no dependency on the earningspy package, so SpyGlass can
be lifted into its own repo. Fetches daily OHLC (ATR needs high/low, not just
close) and the latest intraday spot.

Public, keyless Yahoo endpoints. Best-effort with light retries; raises
``DataError`` on failure so the UI can show a friendly message.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd
import requests

_BASE = "https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SpyGlass/1.0)"}
_TIMEOUT = 10


class DataError(RuntimeError):
    """Raised when market data cannot be fetched or parsed."""


@dataclass
class Quote:
    """Latest spot for a symbol."""

    symbol: str
    price: float
    as_of: str


def _get(url: str, params: dict) -> dict:
    try:
        resp = requests.get(url, params=params, headers=_HEADERS, timeout=_TIMEOUT)
    except requests.RequestException as exc:
        raise DataError(f"network error fetching {url}: {exc}") from exc
    if not resp.ok:
        raise DataError(f"Yahoo returned HTTP {resp.status_code} for {url}")
    try:
        payload = resp.json()
        result = payload["chart"]["result"]
        if not result:
            err = (payload.get("chart") or {}).get("error")
            raise DataError(f"Yahoo returned no data ({err})")
        return result[0]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise DataError(f"could not parse Yahoo response: {exc}") from exc


def fetch_ohlc(symbol: str, lookback_days: int = 400) -> pd.DataFrame:
    """Daily OHLC(V) for ``symbol`` over ~``lookback_days`` calendar days.

    Returns a DataFrame indexed by date with columns open/high/low/close/volume.
    Raises :class:`DataError` on any failure.
    """
    end = datetime.now()
    start = end - timedelta(days=lookback_days)
    result = _get(
        _BASE.format(symbol=symbol.upper()),
        {
            "period1": int(start.timestamp()),
            "period2": int(end.timestamp()),
            "interval": "1d",
            "events": "history",
        },
    )
    ts = result.get("timestamp") or []
    quote = (result.get("indicators", {}).get("quote") or [{}])[0]
    if not ts or not quote:
        raise DataError(f"no OHLC bars returned for {symbol!r}")

    df = pd.DataFrame(
        {
            "open": quote.get("open"),
            "high": quote.get("high"),
            "low": quote.get("low"),
            "close": quote.get("close"),
            "volume": quote.get("volume"),
        },
        index=pd.to_datetime(ts, unit="s"),
    )
    df.index.name = "date"
    df = df.dropna(subset=["high", "low", "close"])
    if df.empty:
        raise DataError(f"all OHLC bars were empty for {symbol!r}")
    return df


def fetch_spot(symbol: str) -> Quote:
    """Latest intraday price for ``symbol`` (1-day / 5-minute bars).

    Falls back to the most recent daily close if intraday is unavailable.
    Raises :class:`DataError` if nothing can be fetched.
    """
    try:
        result = _get(
            _BASE.format(symbol=symbol.upper()),
            {"range": "1d", "interval": "5m", "includePrePost": "true"},
        )
        ts = result.get("timestamp") or []
        closes = (result.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
        pairs = [(t, c) for t, c in zip(ts, closes) if c is not None]
        if pairs:
            t, c = pairs[-1]
            return Quote(symbol.upper(), float(c), str(pd.to_datetime(t, unit="s")))
    except DataError:
        pass  # fall back to daily close below

    ohlc = fetch_ohlc(symbol, lookback_days=10)
    last = ohlc.iloc[-1]
    return Quote(symbol.upper(), float(last["close"]), str(ohlc.index[-1]))
