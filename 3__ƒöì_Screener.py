"""Éléments d'interface partagés : style, formats, état du portefeuille."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.universe import DEFAULT_PORTFOLIO, name_of, theme_of

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

h1, h2, h3 { font-family: 'Fraunces', serif !important; letter-spacing: -0.01em; }

.ac-hero {
    padding: 1.4rem 1.6rem;
    border: 1px solid rgba(201,162,39,.35);
    border-left: 4px solid #C9A227;
    border-radius: 10px;
    background: linear-gradient(135deg, rgba(201,162,39,.07), rgba(20,30,50,.25));
    margin-bottom: 1.2rem;
}
.ac-hero h1 { margin: 0 0 .3rem 0; font-size: 1.7rem; }
.ac-hero p { margin: 0; opacity: .85; font-size: .95rem; }

.ac-badge {
    display: inline-block; padding: .15rem .6rem; border-radius: 999px;
    font-size: .75rem; font-weight: 600; letter-spacing: .04em;
    background: rgba(201,162,39,.15); color: #C9A227;
    border: 1px solid rgba(201,162,39,.4); margin-right: .4rem;
}
[data-testid="stMetric"] {
    background: rgba(255,255,255,.03);
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 10px; padding: .8rem 1rem;
}
.ac-note { font-size: .8rem; opacity: .65; }
</style>
"""


def inject_style():
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str, badges: list[str] | None = None):
    b = "".join(f'<span class="ac-badge">{x}</span>' for x in (badges or []))
    st.markdown(
        f'<div class="ac-hero"><h1>{title}</h1><p>{subtitle}</p>'
        f'<div style="margin-top:.6rem">{b}</div></div>',
        unsafe_allow_html=True,
    )


def data_disclaimer():
    st.markdown(
        '<p class="ac-note">Données Yahoo Finance — gratuites, différées d\'environ 15 minutes '
        "selon les places. Plateforme pédagogique : ne constitue pas un conseil en investissement.</p>",
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------- État portefeuille
def get_portfolio() -> pd.DataFrame:
    """Portefeuille en session (éditable), initialisé sur le modèle du fonds."""
    if "portfolio" not in st.session_state:
        st.session_state.portfolio = pd.DataFrame(
            [
                {
                    "Ticker": t,
                    "Nom": name_of(t),
                    "Thème": theme_of(t),
                    "Poche": pocket,
                    "Poids (%)": w,
                }
                for t, pocket, w in DEFAULT_PORTFOLIO
            ]
        )
    return st.session_state.portfolio


def set_portfolio(df: pd.DataFrame):
    st.session_state.portfolio = df.reset_index(drop=True)


def weights_dict(df: pd.DataFrame) -> dict[str, float]:
    d = {}
    for _, row in df.iterrows():
        t = str(row["Ticker"]).strip()
        try:
            w = float(row["Poids (%)"])
        except (TypeError, ValueError):
            continue
        if t and w > 0:
            d[t] = d.get(t, 0) + w
    return d


def fmt_pct(x, digits=2):
    return "—" if x is None or pd.isna(x) else f"{x * 100:.{digits}f} %"


def fmt_num(x, digits=2):
    return "—" if x is None or pd.isna(x) else f"{x:.{digits}f}"
