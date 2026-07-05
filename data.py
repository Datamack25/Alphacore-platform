"""
Univers d'investissement AlphaCore Capital.

Aligné sur la stratégie du fonds :
- Core défensif (couverture du portefeuille)
- Satellite dynamique orienté "intrants de l'IA" :
  énergie, data centers, transformateurs électriques,
  semi-conducteurs, minéraux critiques.
Tickers au format Yahoo Finance (données gratuites, différées ~15 min).
"""

BENCHMARK = {"ticker": "URTH", "name": "MSCI World (iShares URTH)"}

RISK_FREE_ANNUAL = 0.025  # approximation taux sans risque EUR

UNIVERSE = {
    "Core défensif": {
        "IWDA.AS": "iShares Core MSCI World (Acc)",
        "AGGH.MI": "iShares Core Global Aggregate Bond EUR-H",
        "SGLD.MI": "Invesco Physical Gold",
        "XEON.MI": "Xtrackers EUR Overnight Rate (monétaire)",
        "BRK-B": "Berkshire Hathaway B",
    },
    "Énergie (conv. & renouvelable)": {
        "TTE.PA": "TotalEnergies",
        "SHEL.L": "Shell",
        "NEE": "NextEra Energy",
        "VST": "Vistra Corp",
        "CEG": "Constellation Energy",
        "ENGI.PA": "Engie",
    },
    "Data centers & infrastructure": {
        "EQIX": "Equinix",
        "DLR": "Digital Realty",
        "VRT": "Vertiv Holdings",
        "LR.PA": "Legrand",
    },
    "Transformateurs & équip. électrique": {
        "ETN": "Eaton Corp",
        "SU.PA": "Schneider Electric",
        "SIE.DE": "Siemens",
        "GEV": "GE Vernova",
        "HUBB": "Hubbell",
    },
    "Semi-conducteurs": {
        "NVDA": "NVIDIA",
        "ASML.AS": "ASML Holding",
        "TSM": "TSMC (ADR)",
        "AMAT": "Applied Materials",
        "STMPA.PA": "STMicroelectronics",
        "IFX.DE": "Infineon",
    },
    "Minéraux critiques & matériaux": {
        "MP": "MP Materials (terres rares)",
        "ALB": "Albemarle (lithium)",
        "RIO": "Rio Tinto (ADR)",
        "GLEN.L": "Glencore",
        "MT.AS": "ArcelorMittal (acier)",
        "FCX": "Freeport-McMoRan (cuivre)",
    },
}

# Portefeuille modèle de démarrage — respecte la règle UCITS (≤ 5 % par titre
# hors ETF core) et la logique Core (~60 %) / Satellite (~40 %).
DEFAULT_PORTFOLIO = [
    # ticker, poche, poids cible (%)
    ("IWDA.AS", "Core", 30.0),
    ("AGGH.MI", "Core", 15.0),
    ("SGLD.MI", "Core", 8.0),
    ("XEON.MI", "Core", 7.0),
    ("NVDA", "Satellite", 5.0),
    ("ASML.AS", "Satellite", 5.0),
    ("ETN", "Satellite", 4.0),
    ("SU.PA", "Satellite", 4.0),
    ("VST", "Satellite", 4.0),
    ("TTE.PA", "Satellite", 4.0),
    ("EQIX", "Satellite", 3.0),
    ("VRT", "Satellite", 3.0),
    ("MP", "Satellite", 2.0),
    ("FCX", "Satellite", 2.0),
    ("GEV", "Satellite", 2.0),
    ("ALB", "Satellite", 2.0),
]

MARKET_DASHBOARD = {
    "^GSPC": "S&P 500",
    "^NDX": "Nasdaq 100",
    "^FCHI": "CAC 40",
    "^STOXX50E": "Euro Stoxx 50",
    "^VIX": "VIX",
    "CL=F": "Pétrole WTI",
    "GC=F": "Or",
    "EURUSD=X": "EUR/USD",
    "^TNX": "US 10 ans (%)",
}


def all_tickers():
    out = {}
    for theme, members in UNIVERSE.items():
        for t, name in members.items():
            out[t] = {"name": name, "theme": theme}
    return out


def name_of(ticker: str) -> str:
    return all_tickers().get(ticker, {}).get("name", ticker)


def theme_of(ticker: str) -> str:
    return all_tickers().get(ticker, {}).get("theme", "Hors univers")
