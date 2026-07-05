"""
Couche de données — Yahoo Finance via yfinance.
Données gratuites, différées d'environ 15 minutes selon les places.
Tous les appels sont mis en cache pour rester dans les limites de l'API.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
import yfinance as yf


@st.cache_data(ttl=900, show_spinner=False)
def get_history(tickers: tuple[str, ...], period: str = "2y", interval: str = "1d") -> pd.DataFrame:
    """Prix de clôture ajustés pour une liste de tickers. Colonnes = tickers."""
    if not tickers:
        return pd.DataFrame()
    try:
        raw = yf.download(
            list(tickers),
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
            group_by="column",
            threads=True,
        )
    except Exception:
        return pd.DataFrame()
    if raw is None or raw.empty:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"] if "Close" in raw.columns.get_level_values(0) else pd.DataFrame()
    else:
        close = raw[["Close"]].rename(columns={"Close": tickers[0]})
    close = close.dropna(how="all")
    # forward-fill limité pour aligner les places (jours fériés différents)
    return close.ffill(limit=3)


@st.cache_data(ttl=900, show_spinner=False)
def get_intraday(ticker: str, period: str = "5d", interval: str = "15m") -> pd.DataFrame:
    """OHLCV intraday (différé ~15 min) pour un ticker."""
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600, show_spinner=False)
def get_quotes(tickers: tuple[str, ...]) -> pd.DataFrame:
    """Dernier prix + variation journalière pour un panneau de marché."""
    rows = []
    hist = get_history(tickers, period="10d")
    for t in tickers:
        if t in hist.columns:
            s = hist[t].dropna()
            if len(s) >= 2:
                last, prev = float(s.iloc[-1]), float(s.iloc[-2])
                rows.append({"ticker": t, "last": last, "chg_pct": (last / prev - 1) * 100})
                continue
        rows.append({"ticker": t, "last": None, "chg_pct": None})
    return pd.DataFrame(rows).set_index("ticker")


@st.cache_data(ttl=3600, show_spinner=False)
def get_currency(ticker: str) -> str:
    try:
        fi = yf.Ticker(ticker).fast_info
        return getattr(fi, "currency", None) or fi.get("currency", "USD")
    except Exception:
        return "USD"


def returns_from_prices(prices: pd.DataFrame) -> pd.DataFrame:
    return prices.pct_change().dropna(how="all")
