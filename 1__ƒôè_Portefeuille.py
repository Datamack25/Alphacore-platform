"""Signaux techniques d'entrée / sortie — timing uniquement, conformément à la stratégie."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from core.data import get_history, get_intraday
from core.signals import entry_exit_signal, macd, rsi, sma
from core.ui import data_disclaimer, get_portfolio, hero, inject_style
from core.universe import all_tickers, name_of

st.set_page_config(page_title="Signaux — AlphaCore", page_icon="⚡", layout="wide")
inject_style()
hero(
    "Signaux d'entrée / sortie",
    "Règle du fonds : l'analyse technique sert uniquement au timing des points d'entrée "
    "et de sortie — jamais à la sélection, qui reste fondamentale.",
    ["SMA 20/50/200", "RSI 14", "MACD", "Stops ATR"],
)

port = get_portfolio()
port_tickers = [str(t) for t in port["Ticker"].dropna().tolist()]
univ = list(all_tickers().keys())
options = sorted(set(port_tickers + univ))

col_t, col_c = st.columns([2, 1])
with col_t:
    ticker = st.selectbox(
        "Valeur analysée",
        options=options,
        format_func=lambda t: f"{t} — {name_of(t)}",
        index=options.index("NVDA") if "NVDA" in options else 0,
    )
with col_c:
    custom = st.text_input("…ou ticker Yahoo libre", placeholder="ex. AIR.PA, NQ=F")
    if custom.strip():
        ticker = custom.strip().upper()

with st.spinner("Analyse en cours…"):
    prices = get_history((ticker,), period="2y")

if prices.empty or ticker not in prices.columns:
    st.error(f"Aucune donnée pour « {ticker} ». Vérifiez le format Yahoo Finance du ticker.")
    st.stop()

s = prices[ticker].dropna()
sig = entry_exit_signal(s)

# ------------------------------------------------------------------ Verdict
st.subheader(sig["signal"])
if "price" in sig:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Dernier cours", f"{sig['price']:,.2f}")
    c2.metric("RSI 14", f"{sig['rsi']:.0f}")
    c3.metric("Stop suggéré (2×ATR)", f"{sig['stop']:,.2f}",
              f"{(sig['stop'] / sig['price'] - 1) * 100:.1f} %")
    c4.metric("Objectif (3×ATR)", f"{sig['target']:,.2f}",
              f"{(sig['target'] / sig['price'] - 1) * 100:+.1f} %")
for d in sig["detail"]:
    st.markdown(f"- {d}")

# ------------------------------------------------------------------ Graphique journalier
st.subheader("Graphique journalier (2 ans)")
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.6, 0.2, 0.2],
                    vertical_spacing=0.03)
fig.add_trace(go.Scatter(x=s.index, y=s, name="Cours", line=dict(color="#E8EAF0", width=1.6)), 1, 1)
for n, color in [(20, "#C9A227"), (50, "#3E9CA6"), (200, "#7A8CA6")]:
    m = sma(s, n)
    fig.add_trace(go.Scatter(x=m.index, y=m, name=f"SMA{n}",
                             line=dict(color=color, width=1, dash="dot")), 1, 1)
r = rsi(s)
fig.add_trace(go.Scatter(x=r.index, y=r, name="RSI", line=dict(color="#C9A227", width=1.2)), 2, 1)
fig.add_hline(y=70, line_dash="dash", line_color="#E4572E", row=2, col=1)
fig.add_hline(y=30, line_dash="dash", line_color="#3E9CA6", row=2, col=1)
line, sg, hist_ = macd(s)
fig.add_trace(go.Bar(x=hist_.index, y=hist_, name="MACD hist.",
                     marker_color=["#3E9CA6" if v >= 0 else "#E4572E" for v in hist_]), 3, 1)
fig.update_layout(height=620, template="plotly_dark", hovermode="x unified",
                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                  margin=dict(l=10, r=10, t=20, b=10), legend=dict(orientation="h", y=1.05))
st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------ Intraday 15 min
st.subheader("Intraday 15 minutes (5 jours) — exécution")
intra = get_intraday(ticker, period="5d", interval="15m")
if intra.empty:
    st.info("Pas de données intraday disponibles pour ce ticker.")
else:
    figi = go.Figure(go.Candlestick(
        x=intra.index, open=intra["Open"], high=intra["High"],
        low=intra["Low"], close=intra["Close"],
        increasing_line_color="#3E9CA6", decreasing_line_color="#E4572E",
    ))
    figi.update_layout(height=420, template="plotly_dark", xaxis_rangeslider_visible=False,
                       paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                       margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(figi, use_container_width=True)
    st.caption("Bougies 15 minutes (données différées ~15 min) : utile pour affiner l'exécution "
               "des entrées/sorties validées sur le journalier.")

data_disclaimer()
