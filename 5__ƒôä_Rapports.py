"""Screener alpha : univers « intrants de l'IA » classé par score composite."""

import pandas as pd
import plotly.express as px
import streamlit as st

from core.data import get_history
from core.signals import alpha_score
from core.ui import data_disclaimer, fmt_pct, hero, inject_style
from core.universe import BENCHMARK, UNIVERSE

st.set_page_config(page_title="Screener — AlphaCore", page_icon="🔍", layout="wide")
inject_style()
hero(
    "Screener alpha",
    "Philosophie du fonds : investir dans les intrants de l'IA plutôt que les produits finis, "
    "pour limiter l'exposition aux bulles technologiques. Le score priorise les idées ; "
    "la décision finale reste fondamentale.",
    ["Momentum 12-1", "Force relative vs MSCI World", "Tendance", "Pénalité de volatilité"],
)

themes = st.multiselect(
    "Thèmes analysés",
    options=list(UNIVERSE.keys()),
    default=[t for t in UNIVERSE.keys() if t != "Core défensif"],
)
if not themes:
    st.info("Sélectionnez au moins un thème.")
    st.stop()

tickers, meta = [], {}
for th in themes:
    for t, name in UNIVERSE[th].items():
        tickers.append(t)
        meta[t] = {"Nom": name, "Thème": th}

with st.spinner(f"Analyse de {len(tickers)} valeurs sur 2 ans…"):
    prices = get_history(tuple(sorted(set(tickers + [BENCHMARK["ticker"]]))), period="2y")

if prices.empty or BENCHMARK["ticker"] not in prices.columns:
    st.error("Données indisponibles — réessayez dans quelques minutes.")
    st.stop()

bench = prices[BENCHMARK["ticker"]]
rows = []
for t in tickers:
    if t not in prices.columns:
        continue
    s = prices[t].dropna()
    sc = alpha_score(s, bench)
    rows.append({
        "Ticker": t,
        "Nom": meta[t]["Nom"],
        "Thème": meta[t]["Thème"],
        "Score alpha": sc["score"],
        "Momentum 12-1": sc["m12"],
        "Momentum 3 m": sc["m3"],
        "Force rel. 3 m": sc["rs"],
        "Volatilité ann.": sc["vol"],
    })

df = pd.DataFrame(rows).sort_values("Score alpha", ascending=False).reset_index(drop=True)
df.index += 1

st.subheader("Classement")
styled = df.copy()
for col in ["Momentum 12-1", "Momentum 3 m", "Force rel. 3 m", "Volatilité ann."]:
    styled[col] = styled[col].apply(lambda x: fmt_pct(x, 1))
st.dataframe(
    styled,
    use_container_width=True,
    column_config={"Score alpha": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f")},
)

# ------------------------------------------------------------------ Carte risque/momentum
st.subheader("Carte momentum / volatilité")
plot_df = df.dropna(subset=["Momentum 3 m", "Volatilité ann.", "Score alpha"])
if not plot_df.empty:
    fig = px.scatter(
        plot_df, x="Volatilité ann.", y="Momentum 3 m", color="Thème", text="Ticker",
        size="Score alpha", size_max=28, hover_data=["Nom"],
    )
    fig.update_traces(textposition="top center", textfont_size=10)
    fig.update_layout(height=480, template="plotly_dark",
                      xaxis_tickformat=".0%", yaxis_tickformat=".0%",
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Idéal satellite : momentum élevé, volatilité raisonnable (quadrant haut-gauche). "
               "Les bulles les plus grandes portent le meilleur score composite.")

st.info(
    "Workflow du fonds : ① screener quantitatif pour prioriser → ② analyse fondamentale "
    "titre par titre (risques taux, juridiques…) → ③ page Signaux pour le timing d'entrée → "
    "④ dimensionnement UCITS ≤ 5 % dans le Portefeuille."
)
data_disclaimer()
