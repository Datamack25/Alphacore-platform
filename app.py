"""Analyse de risque : VaR, Expected Shortfall, drawdown, corrélations."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core import risk
from core.data import get_history
from core.ui import data_disclaimer, fmt_num, fmt_pct, get_portfolio, hero, inject_style, weights_dict
from core.universe import BENCHMARK, RISK_FREE_ANNUAL

st.set_page_config(page_title="Risque — AlphaCore", page_icon="🛡️", layout="wide")
inject_style()
hero(
    "Risque",
    "Cadre quantitatif du fonds : drawdown, VaR, Expected Shortfall, "
    "suivi automatisé Python. Analyse fondamentale titre par titre en amont.",
    ["VaR 95/99", "Expected Shortfall", "Drawdown", "Beta / Alpha"],
)

port_df = get_portfolio()
weights = weights_dict(port_df)
if not weights:
    st.warning("Ajoutez d'abord des positions dans la page Portefeuille.")
    st.stop()

period = st.select_slider("Période", options=["6mo", "1y", "2y", "5y"], value="2y")
all_t = tuple(sorted(set(list(weights.keys()) + [BENCHMARK["ticker"]])))
with st.spinner("Chargement des historiques…"):
    prices = get_history(all_t, period=period)

if prices.empty:
    st.error("Données indisponibles pour le moment — réessayez dans quelques minutes.")
    st.stop()

port_ret = risk.portfolio_returns(prices, weights)
bench_ret = prices[BENCHMARK["ticker"]].pct_change().dropna() if BENCHMARK["ticker"] in prices else pd.Series(dtype=float)
common = port_ret.index.intersection(bench_ret.index)
port_ret_c, bench_ret_c = port_ret.loc[common], bench_ret.loc[common]

# ------------------------------------------------------------------ Synthèse
st.subheader("Synthèse des métriques")
summary = risk.risk_summary(port_ret_c, bench_ret_c, RISK_FREE_ANNUAL)
rows = []
for k, v in summary.items():
    is_ratio = k in ("Sharpe", "Sortino", "Beta vs MSCI World", "Information ratio")
    rows.append({"Métrique": k, "Valeur": fmt_num(v) if is_ratio else fmt_pct(v)})
c1, c2 = st.columns([1, 1])
with c1:
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
with c2:
    st.markdown("**Lecture VaR / ES (1 jour)**")
    v95, v99 = summary["VaR 95 % (1j, hist.)"], summary["VaR 99 % (1j, hist.)"]
    es95 = summary["ES 95 % (1j)"]
    if pd.notna(v95):
        st.markdown(
            f"- Dans 95 % des cas, la perte quotidienne ne devrait pas dépasser **{fmt_pct(v95)}** "
            f"(soit {v95 * 1_000_000:,.0f} € pour 1 M€ géré).\n"
            f"- Au seuil 99 % : **{fmt_pct(v99)}**.\n"
            f"- En cas de dépassement du seuil 95 %, la perte moyenne attendue (ES) est de **{fmt_pct(es95)}**."
        )
    vp95 = risk.var_parametric(port_ret_c, 0.95)
    st.markdown(f"- VaR paramétrique (normale) 95 % : **{fmt_pct(vp95)}** — à comparer à l'historique "
                "pour détecter les queues épaisses.")

# ------------------------------------------------------------------ Drawdown
st.subheader("Drawdown")
dd = risk.drawdown_series(port_ret_c)
dd_b = risk.drawdown_series(bench_ret_c)
fig = go.Figure()
fig.add_trace(go.Scatter(x=dd.index, y=dd * 100, name="AlphaCore", fill="tozeroy",
                         line=dict(color="#C9A227", width=1.5)))
fig.add_trace(go.Scatter(x=dd_b.index, y=dd_b * 100, name="MSCI World",
                         line=dict(color="#7A8CA6", width=1.2, dash="dot")))
fig.update_layout(height=340, template="plotly_dark", yaxis_title="Drawdown (%)",
                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                  margin=dict(l=10, r=10, t=20, b=10), hovermode="x unified",
                  legend=dict(orientation="h", y=1.1))
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------- Distribution
st.subheader("Distribution des rendements quotidiens")
col_h, col_c = st.columns(2)
with col_h:
    fig_h = px.histogram(port_ret_c * 100, nbins=60, color_discrete_sequence=["#C9A227"])
    if pd.notna(summary["VaR 95 % (1j, hist.)"]):
        fig_h.add_vline(x=-summary["VaR 95 % (1j, hist.)"] * 100, line_dash="dash",
                        line_color="#E4572E", annotation_text="VaR 95 %")
    fig_h.update_layout(height=340, template="plotly_dark", showlegend=False,
                        xaxis_title="Rendement (%)", yaxis_title="Fréquence",
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig_h, use_container_width=True)

with col_c:
    rets = prices[[t for t in weights if t in prices.columns]].pct_change().dropna(how="all")
    if rets.shape[1] >= 2:
        corr = rets.corr()
        fig_c = px.imshow(corr, color_continuous_scale="RdBu_r", zmin=-1, zmax=1, aspect="auto")
        fig_c.update_layout(height=340, template="plotly_dark",
                            paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=20, b=10),
                            title="Corrélations entre positions")
        st.plotly_chart(fig_c, use_container_width=True)

# ---------------------------------------------------------- Contribution au risque
st.subheader("Contribution au risque par position")
rets = prices[[t for t in weights if t in prices.columns]].pct_change().dropna(how="all")
if rets.shape[1] >= 2:
    w = pd.Series({t: weights[t] for t in rets.columns})
    w = w / w.sum()
    cov = rets.cov() * 252
    port_var = float(w @ cov @ w)
    mcr = cov @ w  # covariance marginale
    ctr = (w * mcr) / port_var * 100 if port_var > 0 else w * 0
    df_ctr = pd.DataFrame({"Ticker": ctr.index, "Poids (%)": (w * 100).round(1),
                           "Contribution au risque (%)": ctr.round(1)}).sort_values(
        "Contribution au risque (%)", ascending=False)
    fig_r = px.bar(df_ctr, x="Ticker", y=["Poids (%)", "Contribution au risque (%)"], barmode="group",
                   color_discrete_sequence=["#3E5C82", "#C9A227"])
    fig_r.update_layout(height=360, template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=20, b=10),
                        legend=dict(orientation="h", y=1.1), yaxis_title="%")
    st.plotly_chart(fig_r, use_container_width=True)
    st.caption("Une position dont la contribution au risque excède nettement son poids concentre "
               "le risque du portefeuille — candidat naturel à l'allègement en phase de stress.")

data_disclaimer()
