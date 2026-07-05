"""Gestion du portefeuille : positions, poches, contrôle UCITS."""

import pandas as pd
import plotly.express as px
import streamlit as st

from core.risk import ucits_check
from core.ui import data_disclaimer, get_portfolio, hero, inject_style, set_portfolio, weights_dict
from core.universe import UNIVERSE, all_tickers, name_of, theme_of

st.set_page_config(page_title="Portefeuille — AlphaCore", page_icon="📊", layout="wide")
inject_style()
hero(
    "Portefeuille",
    "Construction Core/Satellite. La poche core couvre le portefeuille ; "
    "la poche satellite capture la volatilité (event-driven, intrants de l'IA).",
    ["Règle UCITS ≤ 5 % / titre vif", "Horizon fonds 7-10 ans", "Tactique 1-4 mois"],
)

port = get_portfolio()

# ------------------------------------------------------------------ Édition
st.subheader("Positions")
st.caption(
    "Modifiez directement le tableau : tickers Yahoo Finance (ex. NVDA, SU.PA, ASML.AS), "
    "poche Core ou Satellite, poids cible en %. Ajoutez une ligne avec « + »."
)

edited = st.data_editor(
    port,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Ticker": st.column_config.TextColumn(required=True),
        "Poche": st.column_config.SelectboxColumn(options=["Core", "Satellite"], required=True),
        "Poids (%)": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, step=0.5, format="%.1f"),
    },
    key="portfolio_editor",
)

# compléter nom/thème pour les nouvelles lignes
if not edited.equals(port):
    edited = edited.dropna(subset=["Ticker"]).copy()
    edited["Ticker"] = edited["Ticker"].astype(str).str.upper().str.strip()
    edited["Nom"] = edited["Ticker"].map(name_of)
    edited["Thème"] = edited["Ticker"].map(theme_of)
    set_portfolio(edited)
    port = edited

weights = weights_dict(port)
total = sum(weights.values())

c1, c2, c3 = st.columns(3)
c1.metric("Poids total", f"{total:.1f} %", None if abs(total - 100) < 0.01 else f"{total - 100:+.1f} pts vs 100 %")
core_w = port.loc[port["Poche"] == "Core", "Poids (%)"].sum()
sat_w = port.loc[port["Poche"] == "Satellite", "Poids (%)"].sum()
c2.metric("Poche Core", f"{core_w:.1f} %")
c3.metric("Poche Satellite", f"{sat_w:.1f} %")

if abs(total - 100) > 0.01:
    st.warning(f"Le portefeuille totalise {total:.1f} %. Ajustez les poids pour atteindre 100 % "
               "(les calculs de risque renormalisent automatiquement).")

# ------------------------------------------------------------------ UCITS
st.subheader("Contrôle de conformité UCITS")
etf_core = {t for t in weights if t in UNIVERSE["Core défensif"]}
check = ucits_check(weights, etf_core=etf_core)
breaches = check[check["breach"]]
if breaches.empty:
    st.success("✅ Toutes les positions vives respectent la limite de 5 % par titre.")
else:
    st.error(
        f"⚠️ {len(breaches)} position(s) au-delà de 5 % : "
        + ", ".join(f"{r.Ticker} ({r._2:.1f} %)" if hasattr(r, "_2") else r.Ticker for r in breaches.itertuples())
        + ". Rappel de la règle du fonds : dépassement toléré uniquement pour des positions "
        "courtes ≤ 1 semaine, notifié et justifié au client."
    )
st.dataframe(check.drop(columns=["breach"]), use_container_width=True, hide_index=True)

# ------------------------------------------------------------------ Visualisation
st.subheader("Allocation")
col_a, col_b = st.columns(2)
viz = port.dropna(subset=["Poids (%)"]).copy()
with col_a:
    fig = px.sunburst(
        viz, path=["Poche", "Ticker"], values="Poids (%)",
        color="Poche", color_discrete_map={"Core": "#3E5C82", "Satellite": "#C9A227"},
        title="Core / Satellite",
    )
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)
with col_b:
    theme_alloc = viz.groupby("Thème")["Poids (%)"].sum().reset_index()
    fig2 = px.bar(
        theme_alloc.sort_values("Poids (%)"), x="Poids (%)", y="Thème", orientation="h",
        title="Exposition par thème", color_discrete_sequence=["#C9A227"],
    )
    fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                       plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=40, b=10))
    st.plotly_chart(fig2, use_container_width=True)

# ------------------------------------------------------------------ Sauvegarde
st.subheader("Sauvegarde / chargement")
col_s, col_l = st.columns(2)
with col_s:
    st.download_button(
        "💾 Télécharger le portefeuille (CSV)",
        port.to_csv(index=False).encode(),
        file_name="alphacore_portefeuille.csv",
        mime="text/csv",
        use_container_width=True,
    )
with col_l:
    up = st.file_uploader("Recharger un portefeuille CSV", type="csv", label_visibility="collapsed")
    if up is not None:
        try:
            df = pd.read_csv(up)
            needed = {"Ticker", "Poche", "Poids (%)"}
            if needed.issubset(df.columns):
                df["Nom"] = df["Ticker"].map(name_of)
                df["Thème"] = df["Ticker"].map(theme_of)
                set_portfolio(df[["Ticker", "Nom", "Thème", "Poche", "Poids (%)"]])
                st.success("Portefeuille chargé. Actualisez la page si besoin.")
            else:
                st.error(f"Colonnes requises : {', '.join(sorted(needed))}")
        except Exception as e:
            st.error(f"Fichier illisible : {e}")

st.caption(
    "La session Streamlit est éphémère : téléchargez le CSV pour conserver votre allocation, "
    "ou branchez Supabase (voir README) pour une persistance multi-utilisateurs."
)
data_disclaimer()
