"""
Moteur de risque AlphaCore — conforme à la stratégie du fonds :
drawdown, VaR, Expected Shortfall, ratios de performance,
contrôle UCITS (pondération max 5 % par titre).
"""

from __future__ import annotations

from statistics import NormalDist

import numpy as np
import pandas as pd

TRADING_DAYS = 252


# ---------------------------------------------------------------- VaR / ES
def var_historical(returns: pd.Series, level: float = 0.95) -> float:
    r = returns.dropna()
    if r.empty:
        return np.nan
    return float(-np.percentile(r, (1 - level) * 100))


def var_parametric(returns: pd.Series, level: float = 0.95) -> float:
    r = returns.dropna()
    if r.empty:
        return np.nan
    z = NormalDist().inv_cdf(1 - level)
    return float(-(r.mean() + z * r.std()))


def expected_shortfall(returns: pd.Series, level: float = 0.95) -> float:
    r = returns.dropna()
    if r.empty:
        return np.nan
    var = -var_historical(r, level)
    tail = r[r <= var]
    return float(-tail.mean()) if len(tail) else np.nan


# ---------------------------------------------------------------- Drawdown
def drawdown_series(returns: pd.Series) -> pd.Series:
    cum = (1 + returns.fillna(0)).cumprod()
    peak = cum.cummax()
    return cum / peak - 1


def max_drawdown(returns: pd.Series) -> float:
    dd = drawdown_series(returns)
    return float(dd.min()) if not dd.empty else np.nan


# ---------------------------------------------------------------- Ratios
def annualized_return(returns: pd.Series) -> float:
    r = returns.dropna()
    if r.empty:
        return np.nan
    total = (1 + r).prod()
    return float(total ** (TRADING_DAYS / len(r)) - 1)


def annualized_vol(returns: pd.Series) -> float:
    r = returns.dropna()
    return float(r.std() * np.sqrt(TRADING_DAYS)) if not r.empty else np.nan


def sharpe(returns: pd.Series, rf: float = 0.025) -> float:
    vol = annualized_vol(returns)
    if not vol or np.isnan(vol) or vol == 0:
        return np.nan
    return float((annualized_return(returns) - rf) / vol)


def sortino(returns: pd.Series, rf: float = 0.025) -> float:
    r = returns.dropna()
    if r.empty:
        return np.nan
    downside = r[r < 0].std() * np.sqrt(TRADING_DAYS)
    if not downside or np.isnan(downside) or downside == 0:
        return np.nan
    return float((annualized_return(r) - rf) / downside)


def beta_alpha(returns: pd.Series, bench: pd.Series, rf: float = 0.025):
    """Beta et alpha de Jensen annualisé vs benchmark."""
    df = pd.concat([returns, bench], axis=1).dropna()
    if len(df) < 30:
        return np.nan, np.nan
    x, y = df.iloc[:, 1], df.iloc[:, 0]
    b, a = np.polyfit(x, y, 1)
    alpha_ann = float((1 + a) ** TRADING_DAYS - 1)
    # Jensen : alpha = Rp - [Rf + beta*(Rb - Rf)]
    jensen = annualized_return(y) - (rf + b * (annualized_return(x) - rf))
    return float(b), float(jensen)


def tracking_error(returns: pd.Series, bench: pd.Series) -> float:
    df = pd.concat([returns, bench], axis=1).dropna()
    if len(df) < 30:
        return np.nan
    return float((df.iloc[:, 0] - df.iloc[:, 1]).std() * np.sqrt(TRADING_DAYS))


def information_ratio(returns: pd.Series, bench: pd.Series) -> float:
    te = tracking_error(returns, bench)
    if not te or np.isnan(te) or te == 0:
        return np.nan
    df = pd.concat([returns, bench], axis=1).dropna()
    excess = annualized_return(df.iloc[:, 0]) - annualized_return(df.iloc[:, 1])
    return float(excess / te)


# ---------------------------------------------------------------- Portefeuille
def portfolio_returns(prices: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    """Rendements du portefeuille à poids constants (rebalancement quotidien)."""
    cols = [c for c in weights if c in prices.columns]
    if not cols:
        return pd.Series(dtype=float)
    w = pd.Series({c: weights[c] for c in cols})
    w = w / w.sum()
    rets = prices[cols].pct_change().dropna(how="all")
    return (rets * w).sum(axis=1, min_count=1).dropna()


def ucits_check(weights: dict[str, float], etf_core: set[str] | None = None) -> pd.DataFrame:
    """Règle du fonds : max 5 % par titre vif. Les ETF core sont exemptés
    (diversifiés par construction). Dépassement toléré uniquement pour
    positions courtes ≤ 1 semaine, notifiées au client."""
    etf_core = etf_core or set()
    rows = []
    for t, w in weights.items():
        exempt = t in etf_core
        breach = (w > 5.0) and not exempt
        rows.append({
            "Ticker": t,
            "Poids (%)": round(w, 2),
            "Statut": "ETF core (exempté)" if exempt else ("⚠️ > 5 % — à justifier" if breach else "✅ Conforme"),
            "breach": breach,
        })
    return pd.DataFrame(rows)


def risk_summary(port: pd.Series, bench: pd.Series, rf: float = 0.025) -> dict:
    b, jensen = beta_alpha(port, bench, rf)
    return {
        "Rendement annualisé": annualized_return(port),
        "Volatilité annualisée": annualized_vol(port),
        "Sharpe": sharpe(port, rf),
        "Sortino": sortino(port, rf),
        "Max drawdown": max_drawdown(port),
        "VaR 95 % (1j, hist.)": var_historical(port, 0.95),
        "VaR 99 % (1j, hist.)": var_historical(port, 0.99),
        "ES 95 % (1j)": expected_shortfall(port, 0.95),
        "Beta vs MSCI World": b,
        "Alpha de Jensen (ann.)": jensen,
        "Tracking error": tracking_error(port, bench),
        "Information ratio": information_ratio(port, bench),
    }
