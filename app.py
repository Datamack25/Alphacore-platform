"""AlphaCore Capital — Tableau de bord principal."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import risk
from core.data import get_history, get_quotes
from core.ui import data_disclaimer, fmt_pct, get_portfolio, hero, inject_style, weights_dict
from core.universe import BENCHMARK, MARKET_DASHBOARD, RISK_FREE_ANNUAL

st.set_page_config(
    page_title="AlphaCore Capital",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_style()

hero(
    "AlphaCore Capital",
    "Gestion dynamique Core/Satellite · Event-driven · Thématique « intrants de l'IA » · "
    "Objectif : ≥ 14 % net/an vs MSCI World (~7 % net).",
    ["Core / Satellite", "Event-driven", "UCITS ≤ 5 %", "Python & données 15 min"],
)

# ------------------------------------------------------------------ Marchés
st.subheader("Panorama des marchés")
tickers = tuple(MARKET_DASHBOARD.keys())
with st.spinner("Chargement des marchés…"):
    quotes = get_quotes(tickers)

cols = st.columns(len(MARKET_DASHBOARD) // 3 + (1 if len(MARKET_DASHBOARD) % 3 else 0))
cols = st.columns(3)
for i, (t, label) in enumerate(MARKET_DASHBOARD.items()):
    with cols[i % 3]:
        if t in quotes.index and pd.notna(quotes.loc[t, "last"]):
            last = quotes.loc[t, "last"]
            chg = quotes.loc[t, "chg_pct"]
            st.metric(label, f"{last:,.2f}", f"{chg:+.2f} %")
        else:
            st.metric(label, "—", "indisponible")

st.divider()

# ------------------------------------------------------- Portefeuille vs bench
st.subheader("Portefeuille modèle vs MSCI World")

port_df = get_portfolio()
weights = weights_dict(port_df)
period = st.select_slider(
    "Période d'analyse",
    options=["6mo", "1y", "2y", "5y"],
    value="2y",
    help="Historique utilisé pour le backtest à poids constants et les métriques.",
)

all_t = tuple(sorted(set(list(weights.keys()) + [BENCHMARK["ticker"]])))
with st.spinner("Téléchargement des historiques…"):
    prices = get_history(all_t, period=period)

if prices.empty or BENCHMARK["ticker"] not in prices.columns:
    st.error(
        "Impossible de charger les données de marché pour le moment. "
        "Réessayez dans quelques minutes (limites Yahoo Finance)."
    )
    st.stop()

port_ret = risk.portfolio_returns(prices, weights)
bench_ret = prices[BENCHMARK["ticker"]].pct_change().dropna()
common = port_ret.index.intersection(bench_ret.index)
port_ret, bench_ret = port_ret.loc[common], bench_ret.loc[common]

if port_ret.empty:
    st.warning("Pas assez de données pour calculer la performance du portefeuille.")
    st.stop()

cum_port = (1 + port_ret).cumprod() * 100
cum_bench = (1 + bench_ret).cumprod() * 100

fig = go.Figure()
fig.add_trace(go.Scatter(x=cum_port.index, y=cum_port, name="AlphaCore (modèle)",
                         line=dict(color="#C9A227", width=2.4)))
fig.add_trace(go.Scatter(x=cum_bench.index, y=cum_bench, name=BENCHMARK["name"],
                         line=dict(color="#7A8CA6", width=1.8, dash="dot")))
fig.update_layout(
    height=420, margin=dict(l=10, r=10, t=30, b=10),
    yaxis_title="Base 100", legend=dict(orientation="h", y=1.08),
    hovermode="x unified", template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------ Métriques
summary = risk.risk_summary(port_ret, bench_ret, RISK_FREE_ANNUAL)
bench_ann = risk.annualized_return(bench_ret)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Rendement annualisé", fmt_pct(summary["Rendement annualisé"]),
          f"{(summary['Rendement annualisé'] - bench_ann) * 100:+.1f} pts vs MSCI World")
c2.metric("Volatilité ann.", fmt_pct(summary["Volatilité annualisée"]))
c3.metric("Sharpe", f"{summary['Sharpe']:.2f}" if pd.notna(summary["Sharpe"]) else "—")
c4.metric("Max drawdown", fmt_pct(summary["Max drawdown"]))
c5.metric("Alpha de Jensen", fmt_pct(summary["Alpha de Jensen (ann.)"]),
          help="Surperformance ajustée du beta vs MSCI World.")

st.caption(
    "Backtest à poids constants (rebalancement quotidien) sur le portefeuille modèle. "
    "Les performances passées ne préjugent pas des performances futures."
)

st.divider()
st.markdown(
    """
**Navigation** — utilisez le menu latéral :
📊 **Portefeuille** : édition des positions, contrôle UCITS, allocation Core/Satellite ·
🛡️ **Risque** : VaR, Expected Shortfall, drawdown, corrélations ·
🔍 **Screener** : univers « intrants de l'IA » et score alpha ·
⚡ **Signaux** : points d'entrée/sortie techniques ·
📄 **Rapports** : rapport mensuel investisseurs.
"""
)
data_disclaimer()
