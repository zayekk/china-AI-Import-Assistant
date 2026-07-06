# Déploiement sur Vercel

## Architecture du déploiement

Un seul projet Vercel héberge, via la fonctionnalité **Services** de Vercel (deux
"services" indépendants au sein d'un même déploiement) :
- le **service `frontend`** (React/Vite), racine `frontend/` : build statique.
- le **service `backend`** (FastAPI), racine `.` (le repo entier) : une fonction
  serverless Python unique dont le point d'entrée est `vercel_app.py`, à la racine
  du repo (qui réexpose l'application existante `backend/app/main.py`).

Le service backend a volontairement pour racine le **repo entier** (`"root": "."`)
et non `backend/` : le code du backend importe deux paquets Python situés à côté de
`backend/` (`ai_engine/` et `scraper/`), pas dedans. Si la racine du service backend
avait été limitée à `backend/`, ces paquets frères n'auraient pas été inclus dans le
build isolé de ce service, provoquant l'échec `could not import "api/index.py"`
rencontré lors de la première tentative de déploiement.

Le point d'entrée s'appelle `vercel_app.py` et vit à la racine du repo — pas dans un
dossier `api/`, `app/` ou `src/`. Ces trois noms sont réservés par Vercel pour son
ancien mécanisme de détection automatique de fonctions par système de fichiers, qui
entrait en conflit avec la configuration `services` (message observé :
`"The api/ directory will not be built because experimentalServices is
configured"`). En sortant le point d'entrée de `api/`, cette ambiguïté disparaît
complètement : il n'existe plus qu'une seule source de vérité, la configuration
`services` de `vercel.json`.

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
 │ build statique (dist/)  │                      │ entrypoint: vercel_app:app   │
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
persistant, pas de paquets système installables, temps d'exécution limité. Une
seule fonctionnalité du projet ne peut donc **pas** fonctionner telle quelle :

| Fonctionnalité | Endpoint(s) | Pourquoi ça ne marche pas sur Vercel | Comportement observé |
|---|---|---|---|
| Scraping produit (Taobao/Pinduoduo/1688) | `POST /api/v1/scrape`, `POST /api/v1/analyze-url` | Nécessite un vrai navigateur Chromium (Playwright) : Vercel ne permet pas d'installer/lancer un navigateur headless | Erreur `502` propre (déjà gérée par le code existant, `SpiderError`) |

Cette limitation ne casse pas le reste de l'application (l'endpoint gère son échec
proprement), mais c'est une vraie fonctionnalité en moins.

**L'analyse d'image / multi-captures (OCR) fonctionne bien sur Vercel**, malgré
l'absence du binaire système `tesseract-ocr` : `ai_engine/services/ocr_service.py`
utilise Tesseract en priorité (chemin local, inchangé), et **bascule
automatiquement sur l'API OCR dédiée de Mistral** (`mistral-ocr-latest`, réutilise
`MISTRAL_API_KEY`) dès qu'il détecte que le binaire est absent
(`pytesseract.TesseractNotFoundError`). Aucune configuration supplémentaire n'est
nécessaire. À noter tout de même : Vercel limite la taille du corps d'une requête
(~4,5 Mo sur le plan Hobby), ce qui peut limiter le nombre/la taille des captures
envoyées en une seule fois pour le scan multi-captures.

**Pour conserver le scraping (Playwright)**, héberge le backend sur une plateforme
qui exécute un vrai conteneur Docker en continu (Render, Railway, Fly.io, un
VPS...) en réutilisant `docker-compose.yml` / `docker/Dockerfile.backend` déjà
présents dans ce repo, puis déploie uniquement le frontend sur Vercel en
définissant `VITE_API_BASE_URL` (voir plus bas) à l'URL de ce backend. Le code du
frontend supporte déjà les deux topologies sans modification.

## Ce qui fonctionne pleinement sur Vercel

- Authentification (inscription, connexion, refresh, profil)
- Analyse de texte produit (IA Mistral) — `/api/v1/analyze-text`
- Analyse d'image et multi-captures (OCR, via repli automatique Mistral) —
  `/api/v1/analyze-image`, `/api/v1/analyze-images`
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
| `MISTRAL_API_KEY` | Ta clé API Mistral | Oui (sinon `/analyze-text` tombe en mode dégradé, et le repli OCR décrit plus haut échoue aussi) |
| `APP_ENV` | `production` | Recommandé |
| `DEBUG` | `False` | Recommandé |
| `CORS_ORIGINS` | Laisser la valeur par défaut : le domaine Vercel courant (`VERCEL_URL`, fourni automatiquement par Vercel) est ajouté automatiquement | Non |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` | Non nécessaire : réduits automatiquement en environnement serverless (détection de la variable `VERCEL` fournie par la plateforme) | Non |
| `MISTRAL_OCR_API_URL`, `MISTRAL_OCR_MODEL` | Non nécessaire : valeurs par défaut déjà correctes (réutilisent `MISTRAL_API_KEY`) | Non |
| `VITE_API_BASE_URL` | Uniquement si le backend est hébergé **ailleurs** que sur Vercel (voir plus haut) | Non |

Les variables liées au scraping (`SCRAPER_*`) peuvent rester à leur valeur par
défaut : elles n'ont simplement aucun effet tant que cette fonctionnalité n'est
pas disponible sur Vercel. `OCR_LANG` et `TESSERACT_CMD` restent utiles pour le
chemin Tesseract local (Docker/dev), même si Vercel utilise le repli Mistral.

## Notes techniques

- **Repli OCR automatique (Tesseract → API Mistral).**
  `ai_engine/services/ocr_service.py::extract_text_from_image_bytes()` essaie
  toujours Tesseract en premier (comportement local inchangé). Il ne bascule sur
  `MistralClient.ocr_extract_text()` (`ai_engine/services/mistral_client.py`,
  endpoint `POST /v1/ocr`, modèle `mistral-ocr-latest`) que sur l'exception précise
  `pytesseract.TesseractNotFoundError` (binaire absent) — jamais sur une image
  simplement illisible, pour ne rien changer au comportement historique en local.
  Aucune nouvelle dépendance : l'appel réutilise `httpx` (déjà utilisé pour les
  appels Mistral) et `MISTRAL_API_KEY` (déjà configurée).

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
- **`entrypoint: "vercel_app:app"`** pointe explicitement vers `vercel_app.py`
  (module `vercel_app`, variable `app`) à la racine du repo, pour éviter toute
  ambiguïté avec d'autres fichiers qui pourraient aussi correspondre aux motifs de
  détection automatique d'entrypoint de Vercel (ex. `backend/app/main.py`). Ce
  fichier n'est volontairement placé ni dans `api/`, ni dans `app/`, ni dans `src/`
  — voir la section "Architecture du déploiement" ci-dessus pour le pourquoi
  (conflit avec `services`/`experimentalServices`).
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
  standard) et un projet "backend only" (racine du repo, entrypoint `vercel_app.py`),
  puis relier les deux via la variable `VITE_API_BASE_URL` du frontend pointée vers
  l'URL du projet backend (voir la section sur les limites plus haut — cette
  variable existe déjà dans le code pour ce cas de figure).
