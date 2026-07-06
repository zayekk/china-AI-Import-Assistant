# Déploiement sur Vercel

## Architecture du déploiement

Un seul projet Vercel héberge, via la fonctionnalité **Services** de Vercel (deux
"services" indépendants au sein d'un même déploiement) :
- le **service `frontend`** (React/Vite), racine `frontend/` : build statique.
- le **service `backend`** (FastAPI), racine `.` (le repo entier) : une fonction
  serverless Python unique dont le point d'entrée est `api/index.py` (qui réexpose
  l'application existante `backend/app/main.py`).

Le service backend a volontairement pour racine le **repo entier** (`"root": "."`)
et non `backend/` : le code du backend importe deux paquets Python situés à côté de
`backend/` (`ai_engine/` et `scraper/`), pas dedans. Si la racine du service backend
avait été limitée à `backend/`, ces paquets frères n'auraient pas été inclus dans le
build isolé de ce service, provoquant l'échec `could not import "api/index.py"`
rencontré lors de la première tentative de déploiement.

Frontend et API partagent le même domaine Vercel : `frontend/src/services/apiClient.js`
continue d'appeler l'URL relative `/api/v1/...` sans configuration supplémentaire
(pas de CORS à gérer entre les deux). Les rewrites de `vercel.json` garantissent que
le service backend reçoit le chemin de requête original tel quel (ex. `/api/v1/analyze-text`),
ce qui correspond exactement au préfixe `API_V1_PREFIX = "/api/v1"` déjà utilisé par
l'application FastAPI.

```
requête utilisateur
        │
        ▼
 ┌───────────────────────┐        /api/*        ┌─────────────────────────────┐
 │ service "frontend"     │ ◀──────────────────▶ │ service "backend"            │
 │ racine: frontend/       │  (tout le reste)     │ racine: . (repo entier)      │
 │ build statique (dist/)  │                      │ entrypoint: api.index:app    │
 └───────────────────────┘                      │ inclut backend/, ai_engine/, │
                                                  │ scraper/ (tous sous la racine)│
                                                  └──────────────┬──────────────┘
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

- **Modèle "Services" Vercel.** `vercel.json` déclare deux services (`frontend`,
  `backend`) plutôt qu'un unique `buildCommand`/`outputDirectory` global : c'est le
  mécanisme actuellement recommandé par Vercel pour combiner un frontend JS et un
  backend Python dans un même projet. Les champs de build (`installCommand`,
  `buildCommand`, `outputDirectory`) doivent être définis **à l'intérieur** de
  chaque service, plus au niveau racine du fichier.
- **Fallback SPA (`rewrites` à l'intérieur du service `frontend`).** Le rewrite
  racine `{"source": "/(.*)", "destination": {"service": "frontend"}}` route
  seulement le *trafic* vers le service frontend — une fois dedans, ce service gère
  sa propre table de routes et ne sert que les fichiers statiques réellement
  présents dans `dist/`. Sans règle supplémentaire, une URL comme `/products` ou
  `/scan-guide` (routes gérées côté client par React Router) renvoie donc un 404 au
  rechargement de page, faute de fichier `products` ou `scan-guide` sur le disque.
  La règle `"rewrites": [{"source": "/(.*)", "destination": "/index.html"}]`
  **à l'intérieur** de la config du service `frontend` corrige ça : Vercel sert
  d'abord tout fichier statique qui existe réellement (JS/CSS du bundle, favicon...),
  et ne retombe sur `index.html` que pour les chemins qui n'ont pas de fichier
  correspondant — exactement le comportement attendu d'une SPA avec routeur
  côté client.
- **`entrypoint: "api.index:app"`** pointe explicitement vers `api/index.py` (module
  `api.index`, variable `app`) pour éviter toute ambiguïté avec d'autres fichiers du
  repo qui pourraient aussi correspondre aux motifs de détection automatique
  d'entrypoint de Vercel (ex. `backend/app/main.py`).
- **`"root": "."` pour le service backend** (et non `"backend/"`) : voir la section
  "Architecture du déploiement" ci-dessus — c'est ce qui garantit que `ai_engine/`
  et `scraper/` (paquets frères de `backend/`, pas des sous-dossiers) sont bien
  inclus dans le build de ce service.
- La version de Python (3.12, celle utilisée en développement) est fixée via le
  fichier `.python-version` à la racine du repo — c'est le mécanisme actuellement
  supporté par Vercel. Ne pas la fixer via un champ `runtime` dans `vercel.json` :
  cela a provoqué l'erreur `Function Runtimes must have a valid version` lors d'une
  précédente tentative.
- `requirements.txt` à la racine du repo est dédié à la fonction serverless : il est
  volontairement plus restreint que `backend/requirements.txt` (pas d'`uvicorn`, pas
  d'`alembic`, pas d'outils de test).
- `.vercelignore` exclut les dossiers non nécessaires au déploiement (venv,
  node_modules, cache Graphify, tests, docs annexes...) ; il s'applique à
  l'ensemble du repo, donc aux deux services.
- Si la fonctionnalité "Services" n'est pas disponible sur ton compte/projet
  Vercel, l'alternative de repli est de créer **deux projets Vercel distincts** à
  partir du même repo : un projet "frontend only" (racine `frontend/`, build Vite
  standard) et un projet "backend only" (racine du repo, entrypoint `api/index.py`),
  puis relier les deux via la variable `VITE_API_BASE_URL` du frontend pointée vers
  l'URL du projet backend (voir la section sur les limites plus haut — cette
  variable existe déjà dans le code pour ce cas de figure).
