# AlphaCore Capital — Plateforme de gestion

Plateforme Streamlit implémentant la stratégie du fonds :
gestion **Core/Satellite** event-driven, thématique **« intrants de l'IA »**
(énergie, data centers, transformateurs, semi-conducteurs, minéraux critiques),
discipline **UCITS ≤ 5 % par titre**, suivi quantitatif **Python**
(VaR, Expected Shortfall, drawdown, alpha de Jensen), rapports mensuels investisseurs.

**Données : Yahoo Finance via `yfinance` — gratuites, différées d'environ 15 minutes.**

## Pages

| Page | Contenu |
|---|---|
| 🏠 Accueil | Panorama des marchés, backtest du portefeuille modèle vs MSCI World |
| 📊 Portefeuille | Édition des positions, contrôle UCITS 5 %, allocation Core/Satellite et par thème |
| 🛡️ Risque | VaR 95/99 (historique & paramétrique), ES, drawdown, corrélations, contribution au risque |
| 🔍 Screener | Univers thématique classé par score alpha (momentum 12-1, force relative, tendance) |
| ⚡ Signaux | Timing d'entrée/sortie : SMA, RSI, MACD, stops ATR + bougies intraday 15 min |
| 📄 Rapports | Génération du rapport mensuel investisseurs (Markdown → PDF/Word) |

## Lancer en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Déployer (GitHub + Streamlit Community Cloud — gratuit)

1. Créer un dépôt GitHub (ex. `alphacore-platform`) et pousser **tout le contenu de ce dossier
   à la racine du dépôt** (`app.py` doit être à la racine — cause classique d'échec de déploiement) :

   ```bash
   git init
   git add .
   git commit -m "AlphaCore platform v1"
   git branch -M main
   git remote add origin https://github.com/<votre-compte>/alphacore-platform.git
   git push -u origin main
   ```

2. Sur [share.streamlit.io](https://share.streamlit.io) : **New app** → sélectionner le dépôt,
   branche `main`, fichier principal `app.py` → **Deploy**.

3. L'app est en ligne sur `https://<nom>.streamlit.app`. Chaque `git push` redéploie automatiquement.

### Pourquoi Streamlit plutôt qu'une alternative ?

- **Streamlit Community Cloud** : gratuit, redéploiement auto depuis GitHub, parfait pour la finance
  quantitative en Python — c'est le choix retenu ici.
- Alternatives sérieuses : **Hugging Face Spaces** (gratuit, accepte Streamlit/Gradio, plus de RAM),
  **Render** (gratuit avec mise en veille). Dash/Panel sont plus verbeux pour le même résultat.

## Structure

```
alphacore/
├── app.py                  # Tableau de bord principal
├── pages/                  # Pages Streamlit (multi-page natif)
├── core/
│   ├── universe.py         # Univers thématique + portefeuille modèle
│   ├── data.py             # Couche yfinance (cache 10-15 min)
│   ├── risk.py             # VaR, ES, drawdown, ratios, contrôle UCITS
│   ├── signals.py          # Score alpha + signaux techniques entrée/sortie
│   └── ui.py               # Style, formats, état du portefeuille
├── .streamlit/config.toml  # Thème
└── requirements.txt
```

## Persistance (optionnel)

La session Streamlit est éphémère. Deux options :
1. **CSV** : bouton de sauvegarde/chargement intégré dans la page Portefeuille (zéro configuration).
2. **Supabase** (gratuit) : créer une table `portfolios(user text, data jsonb)`, ajouter
   `supabase` à `requirements.txt`, stocker l'URL et la clé dans **Settings → Secrets** de
   Streamlit Cloud, puis remplacer `get_portfolio`/`set_portfolio` dans `core/ui.py`.

## Limites connues

- Yahoo Finance limite le débit : les données sont mises en cache 10–15 min ; en cas d'erreur,
  attendre quelques minutes.
- Les tickers doivent être au **format Yahoo** (`SU.PA`, `ASML.AS`, `GLEN.L`, `NVDA`…).
- Backtest à poids constants (rebalancement quotidien) : indicatif, hors frais et slippage.

---
*Plateforme pédagogique. Ne constitue pas un conseil en investissement.*
