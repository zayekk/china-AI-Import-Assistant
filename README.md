# China AI Import Assistant

Plateforme IA qui aide les débutants à acheter des produits en Chine (Taobao, Pinduoduo, Alibaba, 1688) en détectant les pièges d'achat, en analysant les fournisseurs et en identifiant les produits gagnants pour la revente.

## ⚠️ Avertissement

Ce projet **ne garantit jamais un produit à 100%**. Les analyses IA sont des aides à la décision, pas des certitudes. Vérifiez toujours les informations directement auprès du vendeur avant achat.

## Fonctionnalités

- **Analyse produit** (texte / image / lien) : traduction, détection de variantes, détection de pièges (`case only`, `no battery included`, `without charger`, etc.)
- **Scraper modulaire** (Playwright + BeautifulSoup) : Taobao, Pinduoduo, Alibaba, 1688, extensible à de nouvelles plateformes
- **Analyse fournisseur** : score de fiabilité /100 basé sur l'ancienneté, les avis, le taux de litiges
- **Produits gagnants** : moteur de scoring pondéré (demande 30%, marge 25%, qualité 20%, fiabilité vendeur 15%, logistique 10%)

## Architecture

```
china-ai-import-assistant/
├── backend/          # API FastAPI (auth, analyse, scraping, produits, scores)
│   ├── app/
│   │   ├── api/      # Routers FastAPI
│   │   ├── core/     # Config, sécurité, DB, dependencies
│   │   ├── models/   # Modèles SQLAlchemy
│   │   ├── schemas/  # Schémas Pydantic
│   │   └── services/ # Logique métier
│   └── alembic/      # Migrations base de données
├── ai_engine/        # Intégration Mistral, prompts, OCR
│   ├── prompts/
│   └── services/
├── scraper/          # Scrapers modulaires par plateforme
│   └── spiders/
├── frontend/         # Dashboard React + Tailwind
│   └── src/
│       ├── components/
│       ├── pages/
│       └── services/
├── database/         # Scripts SQL d'init
├── tests/            # Tests backend + scraper
└── docker/           # Dockerfiles + config nginx
```

## Stack technique

| Couche       | Technologies                                  |
|--------------|------------------------------------------------|
| Backend      | Python, FastAPI, SQLAlchemy, PostgreSQL         |
| IA           | Mistral API (mode JSON structuré)               |
| Vision/OCR   | Tesseract OCR (chinois/anglais/français)        |
| Scraping     | Playwright, BeautifulSoup                       |
| Frontend     | React, Vite, Tailwind CSS, React Router         |
| Sécurité     | JWT (python-jose), bcrypt, validation Pydantic  |
| Déploiement  | Docker, docker-compose, Nginx                   |

## Installation (Linux)

### Prérequis

- Python 3.11+
- Node.js 20+
- PostgreSQL 16+ (ou via Docker)
- Tesseract OCR avec les packs de langues chinois/anglais/français

```bash
# Tesseract + langues (Ubuntu/Debian)
sudo apt update
sudo apt install -y tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng tesseract-ocr-fra
```

### 1. Cloner et configurer

```bash
cd china-ai-import-assistant
cp backend/.env.example backend/.env
# Éditez backend/.env : renseignez MISTRAL_API_KEY et SECRET_KEY (openssl rand -hex 32)
```

### 2. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m playwright install --with-deps chromium

# Démarrer PostgreSQL (via Docker, plus simple) :
docker run -d --name china_ai_db -p 5432:5432 \
  -e POSTGRES_USER=china_ai_user \
  -e POSTGRES_PASSWORD=china_ai_password \
  -e POSTGRES_DB=china_ai_db \
  postgres:16-alpine

# Lancer les migrations
alembic upgrade head

# Démarrer l'API (mode développement, crée les tables automatiquement)
uvicorn app.main:app --reload --port 8000
```

L'API est disponible sur `http://localhost:8000`, documentation interactive sur `http://localhost:8000/docs`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Le dashboard est disponible sur `http://localhost:5173`.

### 4. Lancer les tests

```bash
cd china-ai-import-assistant
pip install -r backend/requirements.txt  # si pas déjà fait
pytest tests/ -v
```

## Démarrage rapide avec Docker

```bash
cp backend/.env.example backend/.env
# Éditez backend/.env avec votre clé Mistral

docker compose up --build
```

- Frontend : `http://localhost:3000`
- Backend API : `http://localhost:8000`
- Documentation API : `http://localhost:8000/docs`

## Déploiement sur Vercel

Le projet inclut une configuration Vercel prête à l'emploi (`vercel.json`,
`vercel_app.py`, `requirements.txt` à la racine) : frontend et backend se déploient
depuis un seul projet Vercel, sans configuration manuelle dans le dashboard.

⚠️ Le scraping (Playwright) ne fonctionne pas sur l'environnement serverless de
Vercel (limitation de la plateforme, pas du code). L'analyse d'image / OCR
fonctionne pleinement : en l'absence du binaire Tesseract, elle bascule
automatiquement sur l'API OCR de Mistral. Détails, variables d'environnement
requises et alternative pour garder le scraping : voir
[docs/vercel_deployment.md](docs/vercel_deployment.md).

## Endpoints API principaux

| Méthode | Endpoint                  | Description                          |
|---------|----------------------------|---------------------------------------|
| POST    | `/api/v1/analyze-text`     | Analyse un texte produit brut         |
| POST    | `/api/v1/analyze-image`    | Analyse une capture d'écran (OCR+IA)  |
| POST    | `/api/v1/analyze-url`      | Scrape + analyse un lien produit      |
| POST    | `/api/v1/scrape`           | Lance le scraper sur une fiche produit|
| GET     | `/api/v1/products`         | Liste les produits (filtres, pagination)|
| GET     | `/api/v1/products/{id}`    | Détail d'un produit                   |
| GET     | `/api/v1/score/{id}`       | Score "produit gagnant" IA            |
| POST    | `/api/v1/auth/register`    | Inscription                           |
| POST    | `/api/v1/auth/login`       | Connexion (JWT)                       |

## Format de sortie IA (contrat strict)

```json
{
  "product_name": "Coque de protection Cooltech CP25",
  "included": ["protection silicone"],
  "not_included": ["batterie externe", "chargeur"],
  "warnings": ["Le titre suggère un produit complet alors qu'il s'agit d'un accessoire seul"],
  "quality_score": 65,
  "supplier_score": 50,
  "profit_score": 40,
  "final_score": 52,
  "recommendation": "CAUTION",
  "critical_alerts": ["Titre annonçant un pack complet alors que la fiche précise \"coque seule\""],
  "ai_recommendation_summary": "Achat envisageable avec précautions : seule la coque est incluse, pas la batterie ni le chargeur.",
  "commercial_estimate": {
    "possible": true,
    "reason_if_not_possible": null,
    "purchase_price_cny": 58.0,
    "estimated_transport_cny": 12.0,
    "estimated_customs_cny": 3.0,
    "misc_fees_cny": 2.0,
    "suggested_resale_price_fcfa": 12000.0,
    "landed_cost_fcfa": 7500.0,
    "estimated_profit_fcfa": 4500,
    "margin_percentage": 37.5,
    "roi_percentage": 60.0,
    "commercial_potential": "high",
    "purchase_price_eur": null,
    "estimated_transport_eur": null,
    "estimated_customs_eur": null,
    "suggested_resale_price_eur": null,
    "landed_cost_eur": null,
    "estimated_profit_eur": null
  },
  "decision_badge": "verify",
  "risk_level": "medium",
  "supplier_reliability": "medium",
  "margin_potential": "high",
  "language": "fr",
  "commercial_potential_rating": 4,
  "commercial_potential_explanation": "Bon potentiel : produit standard, marge correcte, forte demande.",
  "import_decision": "import",
  "import_decision_explanation": "Import viable, marge suffisante malgré une concurrence moyenne.",
  "market_comparisons": [],
  "demand_level": "high",
  "demand_explanation": "Accessoire très demandé, sans pic saisonnier particulier.",
  "quick_report": [
    "🟡 À étudier",
    "💰 Marge correcte",
    "⚠ Vérifier le contenu exact du pack"
  ],
  "decision_reasons": ["marge correcte", "demande forte", "contenu du pack à vérifier"],
  "winning_product_score": 7,
  "winning_product_explanation": "Bonne demande et marge correcte compensent une concurrence moyenne.",
  "competition_level": "medium",
  "competition_explanation": "Marché courant avec plusieurs vendeurs similaires.",
  "data_confidence": {"price": 90, "specifications": 70, "photos": 40, "reviews": 20, "ocr": 95},
  "average_market_price": "≈ 55-65 ¥",
  "market_positioning": "mid_range",
  "market_positioning_explanation": "Positionnement standard, ni premium ni entrée de gamme.",
  "resale_ease_rating": 4,
  "resale_ease_explanation": "Produit facile à revendre, forte rotation."
}
```

Tous les champs ci-dessus (hors ceux listés dans le paragraphe suivant) sont générés par l'IA
dans le **même appel Mistral** (aucune requête supplémentaire), **dans la langue choisie par
l'utilisateur** (`language`, transmise via l'en-tête HTTP `X-Language` — sélecteur FR/EN dans la
barre latérale du frontend).

**Toujours calculés côté serveur**, jamais par l'IA, pour garantir cohérence et déterminisme —
voir `ai_engine/services/product_analysis_service.py` : `decision_badge`, `risk_level`,
`supplier_reliability`, `margin_potential`, `import_decision`, et dans `commercial_estimate` tout
ce qui n'est pas un montant "input" — `landed_cost_fcfa`, `estimated_profit_fcfa`,
`margin_percentage`, `roi_percentage`, `commercial_potential`, `landed_cost_eur`,
`estimated_profit_eur`.

**Pipeline financier (v1.2)** : l'IA fournit le prix fournisseur et les coûts annexes en **yuan**
(devise réelle des plateformes chinoises) et le prix de revente conseillé directement en
**FCFA** (revente locale en Afrique de l'Ouest/Centrale) ; le serveur calcule le coût rendu, le
bénéfice, la marge % et le ROI via `settings.IMPORT_CNY_XOF_RATE` (1 ¥ = 100 FCFA par défaut —
taux **volontairement heuristique**, pas le taux de change réel ; configurable, avec repli
automatique sur le pipeline euro → FCFA au taux fixe réel EUR/XOF si l'IA n'a trouvé aucun prix
en yuan).

## Ajouter une nouvelle plateforme au scraper

1. Créer `scraper/spiders/ma_plateforme_spider.py` héritant de `BaseSpider`
2. Implémenter `matches()` et `extract_product()`
3. L'enregistrer dans `scraper/spider_registry.py` (`SPIDER_REGISTRY`)

Aucune autre modification n'est nécessaire : les endpoints `/scrape` et `/analyze-url` détecteront automatiquement la nouvelle plateforme.

## Roadmap SaaS

- [ ] Système de quotas par plan (Free / Pro)
- [ ] Webhooks et notifications d'alertes prix
- [ ] Multi-tenant avec isolation des données
- [ ] Cache Redis sur les résultats d'analyse IA
- [ ] File d'attente (Celery/RQ) pour le scraping asynchrone à grande échelle
- [ ] Extension navigateur pour analyse en un clic

## Licence

Projet propriétaire — usage interne / commercial selon accord du porteur de projet.
