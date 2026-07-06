# Déploiement sur Vercel

## Architecture du déploiement

Un seul projet Vercel héberge :
- le **frontend** (React/Vite) : build statique servi depuis `frontend/dist`.
- le **backend** (FastAPI) : une fonction serverless Python unique (`api/index.py`)
  qui réexpose l'application existante (`backend/app/main.py`) sous `/api/*`.

Frontend et API partagent donc le même domaine Vercel : `frontend/src/services/apiClient.js`
continue d'appeler l'URL relative `/api/v1/...` sans configuration supplémentaire
(pas de CORS à gérer entre les deux).

```
requête utilisateur
        │
        ▼
 ┌─────────────────────┐        /api/*        ┌───────────────────────┐
 │ frontend/dist (SPA)  │ ───────────────────▶ │ api/index.py (FastAPI) │
 │ servi statiquement   │                      │ fonction serverless    │
 └─────────────────────┘                      └───────────┬───────────┘
                                                            │
                                                            ▼
                                              PostgreSQL externe (obligatoire,
                                              voir "Base de données" ci-dessous)
```

## ⚠️ Limites réelles de cet environnement (à lire avant de déployer)

Vercel exécute le backend comme une **fonction serverless** : pas de processus
persistant, pas de paquets système installables, temps d'exécution limité. Deux
fonctionnalités du projet ne peuvent donc **pas** fonctionner telles quelles :

| Fonctionnalité | Endpoint(s) | Pourquoi ça ne marche pas sur Vercel | Comportement observé |
|---|---|---|---|
| Scraping produit (Taobao/Pinduoduo/1688) | `POST /api/v1/scrape`, `POST /api/v1/analyze-url` | Nécessite un vrai navigateur Chromium (Playwright) : Vercel ne permet pas d'installer/lancer un navigateur headless | Erreur `502` propre (déjà gérée par le code existant, `SpiderError`) |
| Analyse d'image / multi-captures (OCR) | `POST /api/v1/analyze-image`, `POST /api/v1/analyze-images` | Nécessite le binaire système `tesseract-ocr`, absent de l'environnement Vercel et non installable | Erreur `422` propre (déjà gérée, `OCRError`) |

Ces deux limitations ne cassent pas le reste de l'application (chaque endpoint gère
son échec proprement), mais ce sont de vraies fonctionnalités en moins. À noter
aussi : Vercel limite la taille du corps d'une requête (~4,5 Mo sur le plan Hobby),
ce qui pourrait de toute façon bloquer l'upload de plusieurs captures d'écran avant
même le problème OCR.

**Pour conserver 100 % des fonctionnalités (scraping + OCR inclus)**, héberge le
backend sur une plateforme qui exécute un vrai conteneur Docker en continu (Render,
Railway, Fly.io, un VPS...) en réutilisant `docker-compose.yml` /
`docker/Dockerfile.backend` déjà présents dans ce repo, puis déploie uniquement le
frontend sur Vercel en définissant `VITE_API_BASE_URL` (voir plus bas) à l'URL de ce
backend. Le code du frontend supporte déjà les deux topologies sans modification.

## Ce qui fonctionne pleinement sur Vercel

- Authentification (inscription, connexion, refresh, profil)
- Analyse de texte produit (IA Mistral) — `/api/v1/analyze-text`
- Estimation du coût d'import — `/api/v1/import-estimate`
- Étapes du scan guidé — `/api/v1/scan-guide/steps`
- Liste/détail produits, scores — `/api/v1/products`, `/api/v1/score/{id}`
- Historique des analyses — `/api/v1/analyses`

## Base de données

Vercel n'héberge pas de PostgreSQL persistant utilisable directement par la fonction
serverless : il faut une base **externe**. Options simples : Neon, Supabase, ou
l'intégration native "Vercel Postgres" (elle-même basée sur Neon).

**Étape manuelle obligatoire avant la première utilisation** : exécuter les
migrations Alembic contre cette base externe, depuis ta machine (Vercel ne lance pas
les migrations automatiquement) :

```bash
cd backend
source venv/bin/activate
DATABASE_URL="postgresql+psycopg2://..." alembic upgrade head
```

À refaire à chaque nouvelle migration ajoutée au projet.

## Variables d'environnement à définir sur Vercel

Dans les réglages du projet Vercel (Settings → Environment Variables) :

| Variable | Valeur | Obligatoire |
|---|---|---|
| `DATABASE_URL` | URL de connexion vers ta base PostgreSQL externe | Oui |
| `SECRET_KEY` | Clé aléatoire forte (`openssl rand -hex 32`) | Oui |
| `MISTRAL_API_KEY` | Ta clé API Mistral | Oui (sinon `/analyze-text` tombe en mode dégradé) |
| `APP_ENV` | `production` | Recommandé |
| `DEBUG` | `False` | Recommandé |
| `CORS_ORIGINS` | Laisser la valeur par défaut : le domaine Vercel courant (`VERCEL_URL`, fourni automatiquement par Vercel) est ajouté automatiquement | Non |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` | Non nécessaire : réduits automatiquement en environnement serverless (détection de la variable `VERCEL` fournie par la plateforme) | Non |
| `VITE_API_BASE_URL` | Uniquement si le backend est hébergé **ailleurs** que sur Vercel (voir plus haut) | Non |

Les variables liées au scraping/OCR (`OCR_LANG`, `TESSERACT_CMD`, `SCRAPER_*`)
peuvent rester à leur valeur par défaut : elles n'ont simplement aucun effet tant
que ces fonctionnalités ne sont pas disponibles sur Vercel.

## Notes techniques

- `vercel.json` fixe `functions."api/index.py".runtime` à `python3.12` (version
  utilisée en développement). Si Vercel refuse cette syntaxe au moment de ton
  déploiement (le format exact peut évoluer côté Vercel), consulte leur
  documentation à jour et adapte ce champ — le reste de la configuration n'en
  dépend pas.
- `requirements.txt` à la racine du repo est dédié à la fonction serverless : il est
  volontairement plus restreint que `backend/requirements.txt` (pas d'`uvicorn`, pas
  d'`alembic`, pas d'outils de test).
- `.vercelignore` exclut les dossiers non nécessaires au déploiement (venv,
  node_modules, cache Graphify, tests, docs annexes...).
