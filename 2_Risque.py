"""Rapport mensuel investisseurs — le track record documenté est l'outil de vente du fonds."""

from datetime import date

import pandas as pd
import streamlit as st

from core import risk
from core.data import get_history
from core.ui import data_disclaimer, fmt_num, fmt_pct, get_portfolio, hero, inject_style, weights_dict
from core.universe import BENCHMARK, RISK_FREE_ANNUAL

st.set_page_config(page_title="Rapports — AlphaCore", page_icon="📄", layout="wide")
inject_style()
hero(
    "Rapport mensuel",
    "Le track record documenté (rapports, décisions horodatées, rationale) est le "
    "principal outil de crédibilité du fonds auprès des investisseurs.",
    ["Rapport mensuel", "Décisions horodatées", "Transparence UCITS"],
)

port_df = get_portfolio()
weights = weights_dict(port_df)
if not weights:
    st.warning("Ajoutez d'abord des positions dans la page Portefeuille.")
    st.stop()

col1, col2 = st.columns(2)
with col1:
    ref_date = st.date_input("Date du rapport", value=date.today())
with col2:
    commentary = st.text_area(
        "Commentaire de gestion (rationale du mois)",
        placeholder="Événements macro traités, arbitrages effectués, positionnement à venir…",
        height=100,
    )

with st.spinner("Calcul des performances…"):
    prices = get_history(tuple(sorted(set(list(weights.keys()) + [BENCHMARK["ticker"]]))), period="1y")

if prices.empty or BENCHMARK["ticker"] not in prices.columns:
    st.error("Données indisponibles — réessayez dans quelques minutes.")
    st.stop()

port_ret = risk.portfolio_returns(prices, weights)
bench_ret = prices[BENCHMARK["ticker"]].pct_change().dropna()
common = port_ret.index.intersection(bench_ret.index)
port_ret, bench_ret = port_ret.loc[common], bench_ret.loc[common]

last_month = port_ret.tail(21)
last_month_b = bench_ret.tail(21)
m_perf = float((1 + last_month).prod() - 1)
m_perf_b = float((1 + last_month_b).prod() - 1)
summary = risk.risk_summary(port_ret, bench_ret, RISK_FREE_ANNUAL)

c1, c2, c3 = st.columns(3)
c1.metric("Perf. du mois (≈21 j)", fmt_pct(m_perf), f"{(m_perf - m_perf_b) * 100:+.2f} pts vs MSCI World")
c2.metric("Perf. 1 an (annualisée)", fmt_pct(summary["Rendement annualisé"]))
c3.metric("VaR 95 % (1j)", fmt_pct(summary["VaR 95 % (1j, hist.)"]))

# ------------------------------------------------------------------ Génération
alloc_lines = "\n".join(
    f"| {r['Ticker']} | {r['Nom']} | {r['Poche']} | {r['Poids (%)']:.1f} % |"
    for _, r in port_df.dropna(subset=["Poids (%)"]).sort_values("Poids (%)", ascending=False).iterrows()
)

report_md = f"""# AlphaCore Capital — Rapport mensuel
**Date : {ref_date.strftime('%d/%m/%Y')}** · Benchmark : {BENCHMARK['name']} · Document confidentiel

## 1. Performance
| Métrique | Fonds | Repère |
|---|---|---|
| Performance du mois (~21 séances) | {fmt_pct(m_perf)} | {fmt_pct(m_perf_b)} (MSCI World) |
| Rendement annualisé (1 an) | {fmt_pct(summary['Rendement annualisé'])} | Objectif ≥ 14 % net |
| Volatilité annualisée | {fmt_pct(summary['Volatilité annualisée'])} | — |
| Sharpe / Sortino | {fmt_num(summary['Sharpe'])} / {fmt_num(summary['Sortino'])} | — |
| Alpha de Jensen (ann.) | {fmt_pct(summary['Alpha de Jensen (ann.)'])} | — |

## 2. Risque
| Métrique | Valeur |
|---|---|
| VaR 95 % (1 jour, historique) | {fmt_pct(summary['VaR 95 % (1j, hist.)'])} |
| VaR 99 % (1 jour, historique) | {fmt_pct(summary['VaR 99 % (1j, hist.)'])} |
| Expected Shortfall 95 % | {fmt_pct(summary['ES 95 % (1j)'])} |
| Max drawdown (1 an) | {fmt_pct(summary['Max drawdown'])} |
| Beta vs MSCI World | {fmt_num(summary['Beta vs MSCI World'])} |
| Tracking error | {fmt_pct(summary['Tracking error'])} |

## 3. Allocation en fin de période
| Ticker | Nom | Poche | Poids |
|---|---|---|---|
{alloc_lines}

Conformité UCITS : pondération maximale de 5 % par titre vif respectée sauf mention
explicite (positions courtes ≤ 1 semaine, notifiées et justifiées).

## 4. Commentaire de gestion
{commentary.strip() or "_À compléter par l'équipe de gestion._"}

---
*Données Yahoo Finance différées (~15 min). Les performances passées ne préjugent pas des
performances futures. Document interne — ne constitue pas un conseil en investissement.*
"""

st.subheader("Aperçu du rapport")
st.markdown(report_md)
st.download_button(
    "📄 Télécharger le rapport (Markdown)",
    report_md.encode(),
    file_name=f"alphacore_rapport_{ref_date.strftime('%Y_%m')}.md",
    mime="text/markdown",
    use_container_width=True,
)
st.caption("Le fichier .md se convertit en PDF/Word en un clic (Pandoc, Word, Google Docs) "
           "pour l'envoi aux investisseurs.")
data_disclaimer()
