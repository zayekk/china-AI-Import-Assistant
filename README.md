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
`api/index.py`, `requirements.txt` à la racine) : frontend et backend se déploient
depuis un seul projet Vercel, sans configuration manuelle dans le dashboard.

⚠️ Le scraping (Playwright) et l'analyse d'image (Tesseract OCR) ne fonctionnent
pas sur l'environnement serverless de Vercel (limitation de la plateforme, pas du
code) — le reste de l'application (auth, analyse texte, estimation import, scan
guidé, produits/scores) fonctionne pleinement. Détails, variables d'environnement
requises et alternative pour garder 100 % des fonctionnalités : voir
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
  "recommendation": "CAUTION"
}
```

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
