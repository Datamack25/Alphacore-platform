"""
Moteur de signaux AlphaCore.

Philosophie du fonds :
- La sélection repose sur le fondamental / thématique (intrants de l'IA).
- L'analyse technique sert UNIQUEMENT aux points d'entrée et de sortie.
- Le score alpha combine momentum, tendance, risque et force relative
  vs MSCI World pour prioriser les idées du screener.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------- Indicateurs
def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()


def rsi(s: pd.Series, n: int = 14) -> pd.Series:
    delta = s.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / down.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def macd(s: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_f = s.ewm(span=fast, adjust=False).mean()
    ema_s = s.ewm(span=slow, adjust=False).mean()
    line = ema_f - ema_s
    sig = line.ewm(span=signal, adjust=False).mean()
    return line, sig, line - sig


def atr_from_close(s: pd.Series, n: int = 14) -> pd.Series:
    """ATR approximé à partir des clôtures (fallback sans OHLC)."""
    tr = s.diff().abs()
    return tr.rolling(n).mean()


# ---------------------------------------------------------------- Scores
def momentum_12_1(s: pd.Series) -> float:
    """Momentum 12 mois hors dernier mois (classique académique)."""
    s = s.dropna()
    if len(s) < 273:
        return np.nan
    return float(s.iloc[-21] / s.iloc[-252] - 1)


def momentum_3m(s: pd.Series) -> float:
    s = s.dropna()
    if len(s) < 63:
        return np.nan
    return float(s.iloc[-1] / s.iloc[-63] - 1)


def relative_strength(s: pd.Series, bench: pd.Series, n: int = 63) -> float:
    """Surperformance vs benchmark sur n jours."""
    df = pd.concat([s, bench], axis=1).dropna()
    if len(df) < n:
        return np.nan
    a = df.iloc[-1, 0] / df.iloc[-n, 0] - 1
    b = df.iloc[-1, 1] / df.iloc[-n, 1] - 1
    return float(a - b)


def trend_score(s: pd.Series) -> float:
    """1 si prix > SMA50 > SMA200, gradations sinon."""
    s = s.dropna()
    if len(s) < 200:
        return np.nan
    p, s50, s200 = s.iloc[-1], sma(s, 50).iloc[-1], sma(s, 200).iloc[-1]
    score = 0.0
    score += 0.4 if p > s50 else 0.0
    score += 0.3 if p > s200 else 0.0
    score += 0.3 if s50 > s200 else 0.0
    return score


def vol_penalty(s: pd.Series, n: int = 63) -> float:
    r = s.pct_change().dropna().tail(n)
    if len(r) < 20:
        return np.nan
    return float(r.std() * np.sqrt(252))


def alpha_score(s: pd.Series, bench: pd.Series) -> dict:
    """Score composite 0-100 pour prioriser les idées d'investissement."""
    m12 = momentum_12_1(s)
    m3 = momentum_3m(s)
    rs = relative_strength(s, bench)
    tr = trend_score(s)
    vol = vol_penalty(s)
    parts, weights = [], []
    for value, scale, w in [
        (m12, 0.40, 0.30),   # normalisation grossière : ±40 % → 0-1
        (m3, 0.20, 0.25),
        (rs, 0.15, 0.25),
        (tr, 1.00, 0.20),
    ]:
        if value is not None and not np.isnan(value):
            parts.append(np.clip((value / scale + 1) / 2 if scale != 1 else value, 0, 1))
            weights.append(w)
    if not parts:
        return {"score": np.nan, "m12": m12, "m3": m3, "rs": rs, "trend": tr, "vol": vol}
    raw = float(np.average(parts, weights=weights))
    # pénalité de volatilité extrême (> 60 % ann.)
    if vol is not None and not np.isnan(vol) and vol > 0.60:
        raw *= 0.85
    return {"score": round(raw * 100, 1), "m12": m12, "m3": m3, "rs": rs, "trend": tr, "vol": vol}


# ---------------------------------------------------------------- Entrées / sorties
def entry_exit_signal(s: pd.Series) -> dict:
    """Signal technique d'entrée/sortie (usage : timing uniquement)."""
    s = s.dropna()
    if len(s) < 60:
        return {"signal": "Données insuffisantes", "detail": [], "rsi": np.nan}
    r = rsi(s).iloc[-1]
    line, sig, hist_ = macd(s)
    s20, s50 = sma(s, 20), sma(s, 50)
    price = s.iloc[-1]
    atr = atr_from_close(s).iloc[-1]

    detail, bull, bear = [], 0, 0
    if price > s50.iloc[-1]:
        bull += 1; detail.append("Prix > SMA50 (tendance haussière)")
    else:
        bear += 1; detail.append("Prix < SMA50 (tendance baissière)")
    if line.iloc[-1] > sig.iloc[-1] and hist_.iloc[-1] > hist_.iloc[-2]:
        bull += 1; detail.append("MACD haussier et en accélération")
    elif line.iloc[-1] < sig.iloc[-1]:
        bear += 1; detail.append("MACD sous sa ligne de signal")
    if r < 35:
        bull += 1; detail.append(f"RSI {r:.0f} — zone de survente (repli exploitable)")
    elif r > 70:
        bear += 1; detail.append(f"RSI {r:.0f} — zone de surachat (prise de profit)")
    else:
        detail.append(f"RSI {r:.0f} — zone neutre")
    if len(s20.dropna()) > 2 and s20.iloc[-2] < s50.iloc[-2] and s20.iloc[-1] > s50.iloc[-1]:
        bull += 1; detail.append("Croisement haussier SMA20/SMA50 (frais)")

    if bull >= 3:
        signal = "🟢 Fenêtre d'ENTRÉE favorable"
    elif bull == 2 and bear == 0:
        signal = "🟢 Entrée possible (confirmation partielle)"
    elif bear >= 2:
        signal = "🔴 Fenêtre de SORTIE / allègement"
    else:
        signal = "🟡 Neutre — attendre confirmation"

    stop = price - 2 * atr if not np.isnan(atr) else np.nan
    target = price + 3 * atr if not np.isnan(atr) else np.nan
    return {
        "signal": signal, "detail": detail, "rsi": float(r),
        "price": float(price), "stop": float(stop), "target": float(target),
        "sma50": float(s50.iloc[-1]),
    }
