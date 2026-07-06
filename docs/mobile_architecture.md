# Architecture technique — Extension mobile Android (bouton flottant overlay)

## Statut du document

Documentation d'architecture uniquement. **Aucun code Android/Kotlin/APK n'est livré dans ce lot.**
Objectif : décrire comment un futur module Android (bouton flottant overlay au-dessus de
Pinduoduo / Taobao / Alibaba / 1688) s'intégrerait au backend FastAPI existant, sans modification
du code backend/frontend actuel.

---

## 1. Schéma de flux (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Device Android                                                         │
│                                                                           │
│   ┌────────────────────┐         ┌──────────────────────────────────┐  │
│   │ App Pinduoduo /     │         │ App Android "China AI Import      │  │
│   │ Taobao / Alibaba /  │◄────────┤ Assistant" (Foreground Service)   │  │
│   │ 1688 (au premier    │  overlay│                                    │  │
│   │ plan, écran visible)│         │  ┌──────────────────────────────┐ │  │
│   └─────────┬───────────┘         │  │ Bouton flottant (overlay)    │ │  │
│             │                     │  │ SYSTEM_ALERT_WINDOW           │ │  │
│             │  1. Utilisateur     │  │ (WindowManager, TYPE_APPLICATION│ │  │
│             │     tape sur le     │  │  _OVERLAY)                    │ │  │
│             │     bouton flottant │  └──────────┬───────────────────┘ │  │
│             │◄────────────────────┼─────────────┘                     │  │
│             │                     │                                    │  │
│             ▼                     ▼                                    │  │
│   ┌─────────────────────────────────────────────────────────────────┐ │  │
│   │ 2. Capture d'écran explicite (MediaProjection API)               │ │  │
│   │    - Action utilisateur obligatoire à CHAQUE capture             │ │  │
│   │    - Pas de capture automatique / silencieuse / en arrière-plan  │ │  │
│   └───────────────────────────────┬─────────────────────────────────┘ │  │
│                                    ▼                                    │  │
│   ┌─────────────────────────────────────────────────────────────────┐ │  │
│   │ 3. File d'attente locale de captures (cache app temporaire)      │ │  │
│   │    - L'utilisateur répète l'étape 1-2 pour accumuler             │ │  │
│   │      entre 5 et 12 captures (cohérent avec le module web         │ │  │
│   │      "scan multi-captures" côté backend)                         │ │  │
│   │    - Miniatures affichées dans la bulle (feedback visuel)        │ │  │
│   └───────────────────────────────┬─────────────────────────────────┘ │  │
│                                    │ 4. Upload batch déclenché          │  │
│                                    │    (bouton "Analyser" dans la bulle)│ │
└────────────────────────────────────┼───────────────────────────────────┘  │
                                     ▼                                       │
                    ┌────────────────────────────────────┐                  │
                    │  Réseau (HTTPS)                     │                  │
                    │  POST /api/v1/analyze-images         │                  │
                    │  Content-Type: multipart/form-data   │                  │
                    │  Authorization: Bearer <JWT access>  │                  │
                    │  files: 5 à 12 UploadFile             │                  │
                    └────────────────┬─────────────────────┘                  │
                                     ▼                                        │
                    ┌────────────────────────────────────────────┐           │
                    │  Backend FastAPI existant                   │           │
                    │  (voir section 4 — compatibilité déjà       │           │
                    │  assurée, aucune modification nécessaire)   │           │
                    │                                              │           │
                    │  - Vérifie le JWT (get_optional_user /       │           │
                    │    get_current_user)                         │           │
                    │  - OCR multi-images + analyse IA             │           │
                    │  - Retourne AIAnalysisResult (JSON)           │           │
                    └────────────────┬─────────────────────────────┘           │
                                     │ 5. Réponse JSON structurée               │
                                     ▼                                          │
   ┌─────────────────────────────────────────────────────────────────────┐    │
   │ 6. Purge du cache local des captures (upload réussi)                 │    │
   └───────────────────────────────┬─────────────────────────────────────┘    │
                                    ▼                                          │
   ┌─────────────────────────────────────────────────────────────────────┐    │
   │ 7. Affichage compact dans la bulle flottante (overlay), au-dessus    │    │
   │    de l'app source (Pinduoduo/Taobao/1688 reste visible en dessous)  │◄───┘
   │                                                                      │
   │    ┌────────────────────────────────────┐                          │
   │    │  📦 product_name (tronqué, 1 ligne)  │                          │
   │    │  🟢 BUY   |  score: 82/100           │  ← badge recommendation  │
   │    │  confiance: 74/100                   │     coloré (BUY=vert,   │
   │    │                                       │     CAUTION=orange,     │
   │    └────────────────────────────────────┘     AVOID=rouge)          │
   └───────────────────────────────────────────────────────────────────────┘
```

**Points clés du flux :**
- Le bouton flottant et la bulle de résultat sont deux états du **même overlay**
  (`WindowManager` + `TYPE_APPLICATION_OVERLAY`), affiché par-dessus l'app source sans jamais
  la fermer ni l'interrompre.
- Chaque capture d'écran est une **action utilisateur explicite** (tap sur le bouton flottant) —
  jamais de capture automatique en tâche de fond.
- Le nombre de captures (5 à 12) reprend exactement les bornes du module "scan multi-captures"
  déjà en cours de développement côté web/backend, pour rester cohérent avec le contrat de
  `POST /api/v1/analyze-images`.
- Le token JWT utilisé pour l'upload est celui obtenu **au login dans l'app mobile elle-même**
  (flux d'authentification mobile indépendant, hors scope de ce document — voir section 6).

---

## 2. Stack technique recommandée (indicative, non développée dans ce lot)

| Composant | Choix recommandé | Justification |
|---|---|---|
| Langage | **Kotlin** | Standard actuel pour app Android native, bon support coroutines pour l'async (upload réseau, capture). |
| Persistance du bouton flottant | **Foreground Service** | Nécessaire pour garder l'overlay actif même quand l'app Android n'est pas au premier plan (l'utilisateur navigue dans Pinduoduo/Taobao). Notification persistante obligatoire (conformité Android 8+). |
| Capture d'écran | **MediaProjection API** | Seule API Android permettant une capture d'écran déclenchée par une action utilisateur explicite, sans droits d'accessibilité invasifs. Nécessite une autorisation système à chaque session de capture (dialogue "Cast/enregistrer l'écran"). |
| Ce qu'on évite explicitement | **Pas d'Accessibility Service** pour la capture | Un service d'accessibilité tournant en arrière-plan pour lire l'écran serait à la fois invasif (accès à tout le contenu affiché, pas seulement aux captures voulues) et à haut risque de rejet Play Store. `MediaProjection` + tap utilisateur est le choix conforme. |
| Client HTTP | **OkHttp / Retrofit** | Standard de facto pour consommer une API REST JSON + multipart/form-data depuis Android. Retrofit gère nativement `MultipartBody.Part` pour l'upload batch de fichiers vers `POST /api/v1/analyze-images`. |
| Stockage du token JWT | **Android Keystore** (via `EncryptedSharedPreferences` ou équivalent) | Stockage chiffré matériel du token d'accès (et du refresh token), cohérent avec le modèle JWT stateless déjà utilisé côté backend (pas de session serveur à synchroniser). |
| Cache des captures en attente | **Cache app local temporaire** (`context.cacheDir`, jamais stockage externe/partagé) | Les captures accumulées (5-12 images) sont stockées temporairement le temps de constituer le lot, puis **purgées immédiatement après upload réussi**. Aucune capture ne doit persister au-delà du cycle d'analyse. |

Cette stack reste **indicative** : elle sert de base de discussion pour un futur lot de
développement Android, pas une décision figée à ce stade.

---

## 3. Permissions Android à anticiper

| Permission / composant | Usage | Point de vigilance |
|---|---|---|
| `SYSTEM_ALERT_WINDOW` | Afficher le bouton flottant et la bulle de résultat par-dessus les autres apps (Pinduoduo/Taobao/Alibaba/1688). | Permission "spéciale" sur Android — l'utilisateur doit l'accorder manuellement via les réglages système (`Settings.ACTION_MANAGE_OVERLAY_PERMISSION`), pas via une simple demande runtime classique. |
| `MediaProjection` (autorisation à la volée, pas une permission manifest classique) | Capture d'écran déclenchée à chaque tap sur le bouton flottant. | Le dialogue système de consentement doit apparaître **à chaque nouvelle session de capture** selon la politique Android — ne pas tenter de le contourner ou de le mettre en cache au-delà de ce que l'OS autorise. |
| Stockage / cache applicatif | Cache privé de l'app (`context.cacheDir`) pour les captures en attente d'upload. | **Pas** de permission de stockage externe (`WRITE_EXTERNAL_STORAGE`) nécessaire si le cache reste dans le bac à sable de l'app — à privilégier pour limiter la surface de permissions. |
| `INTERNET` | Appels réseau vers l'API FastAPI existante (`POST /api/v1/analyze-images`, login, etc.). | Permission standard, faible risque de friction Play Store. |
| Foreground Service (déclaration manifest + type de service) | Maintenir le bouton flottant actif en tâche de fond. | Depuis Android 14, les Foreground Services doivent déclarer un type explicite (ex. `specialUse` ou équivalent) — à valider lors de l'implémentation réelle, hors scope ici. |

### Point de conformité Play Store — à respecter strictement

> **Aucune capture d'écran automatique ou silencieuse n'est acceptable.**
> Chaque capture doit être déclenchée par un **tap utilisateur explicite** sur le bouton flottant.
> Pas de capture périodique, pas de capture déclenchée par un événement d'accessibilité, pas de
> capture en arrière-plan sans interaction directe. C'est une exigence à la fois réglementaire
> (Play Store policy sur les permissions sensibles / `MediaProjection`) et de confiance utilisateur
> (l'app tourne au-dessus de comptes marchands potentiellement sensibles — Pinduoduo, Taobao,
> Alibaba, 1688).

---

## 4. Compatibilité backend déjà assurée

Le backend actuel n'a **besoin d'aucune modification** pour servir un client mobile Android. Détail
point par point, avec référence aux fichiers concernés :

### 4.1 Authentification JWT stateless

- `backend/app/core/deps.py` définit `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)`
  et les dépendances `get_current_user()` (L17-48), `get_optional_user()` (L51-61) et
  `get_current_admin()` (L64-71).
- L'authentification repose uniquement sur la lecture et la validation d'un **header
  `Authorization: Bearer <token>`** (`decode_token()` dans `backend/app/core/security.py`), sans
  aucune session serveur, cookie, ni état conservé côté backend entre deux requêtes.
- Conséquence directe pour le mobile : un client Android qui a obtenu un access token JWT (via un
  flux de login mobile, hors scope de ce document) peut appeler n'importe quel endpoint protégé en
  ajoutant simplement ce header — exactement comme le fait le frontend web. Aucune notion de
  navigateur, cookie de session ou `CSRF token` n'entre en jeu : ce modèle est nativement
  compatible avec un client HTTP mobile standard (OkHttp/Retrofit).
- `get_optional_user()` (utilisé par `analyze_image()`, `analyze_text()`, `analyze_url()` dans
  `backend/app/api/analysis.py`) permet même un usage anonyme si nécessaire, ce qui laisse ouverte
  l'option d'un mode "essai sans compte" côté mobile si le produit le souhaite plus tard.

### 4.2 Endpoints multipart/form-data déjà utilisables depuis un client HTTP mobile standard

- `POST /api/v1/analyze-image` (`backend/app/api/analysis.py`, fonction `analyze_image()`,
  L92-131) accepte déjà un upload `UploadFile` en `multipart/form-data` (`file: UploadFile =
  File(...)`), avec validation du `content_type` (JPEG/PNG/WEBP) et de la taille
  (`settings.MAX_UPLOAD_SIZE_MB`, définie dans `backend/app/core/config.py`, L59).
- Le futur endpoint `POST /api/v1/analyze-images` (module "analyse multi-captures", en cours de
  développement en parallèle) suivra la même convention `multipart/form-data` avec un champ
  `files: list[UploadFile]` (5 à 12 images) — strictement le même protocole HTTP que
  `analyze-image`, juste avec plusieurs parties de fichier au lieu d'une seule.
- `multipart/form-data` est un standard HTTP universel, nativement supporté par Retrofit
  (`@Multipart`, `MultipartBody.Part.createFormData(...)`) et OkHttp côté Android. Aucune
  adaptation serveur n'est nécessaire pour qu'un client mobile envoie ses fichiers de la même façon
  qu'un navigateur web.

### 4.3 CORS configurable indépendamment du frontend web

- `backend/app/core/config.py` (L31-35) définit `CORS_ORIGINS: List[str]` comme une liste
  d'origines autorisées (actuellement des origines localhost pour le dev web).
- CORS est une politique **appliquée par les navigateurs**, pas par les clients HTTP natifs : un
  client Android (OkHttp/Retrofit) n'est pas soumis aux vérifications CORS du navigateur. Aucune
  configuration CORS supplémentaire n'est donc requise pour que l'app mobile fonctionne — CORS
  reste pertinent uniquement pour le frontend web, et les deux peuvent évoluer indépendamment
  (ajouter/retirer des origines web n'affecte jamais le client mobile).

### 4.4 Contrat de réponse JSON strict et stable

- `backend/app/schemas/analysis.py` définit `AIAnalysisResult` (L40-60) comme le contrat de sortie
  strict retourné par tous les endpoints d'analyse (`analyze-text`, `analyze-image`, `analyze-url`,
  et à terme `analyze-images`) : `product_name`, `included`, `not_included`, `warnings`,
  `quality_score`, `supplier_score`, `profit_score`, `final_score`, `recommendation` (`Literal["BUY",
  "AVOID", "CAUTION"]`), ainsi que les champs de transparence IA (`detected_data`,
  `ai_estimations`, `missing_information`, `confidence_score`, `confidence_level`,
  `confidence_reasons`, `confidence_risks`).
- Ce contrat est un schéma Pydantic (`response_model=AIAnalysisResult` sur chaque route), donc
  **auto-documenté en OpenAPI/Swagger** (`/docs` généré par FastAPI) et **type-safe** côté serveur.
  Un client Android peut générer son propre modèle Kotlin (data class) directement depuis ce schéma
  JSON, sans ambiguïté de format, et sans dépendre du rendu HTML du frontend web.
- Comme le contrat est strict (types, bornes `ge=0, le=100` sur les scores, `Literal` sur
  `recommendation`), le client mobile peut parser la réponse de façon fiable pour l'affichage
  compact dans la bulle flottante (badge coloré selon `recommendation`, score numérique, etc.)
  sans logique de tolérance particulière.

**En résumé** : aucun des trois piliers (auth, upload, contrat de sortie) ne nécessite de
changement backend pour être consommé par un client Android natif — l'architecture actuelle a été
conçue de façon découplée du frontend web (JWT stateless + REST + JSON strict), ce qui la rend
"mobile-ready" par construction.

---

## 5. Suggestion d'amélioration backend légère pour la bulle mobile (RECOMMANDATION — non implémentée dans ce lot)

**Idée** : ajouter un champ optionnel `mobile_summary: str` dans le contrat `AIAnalysisResult`
(`backend/app/schemas/analysis.py`), calculé **côté serveur par du code applicatif classique**
(pas par l'IA — donc pas de coût ni de variabilité de génération supplémentaire), à partir des
champs déjà existants dans la réponse. Exemple de logique :

```python
mobile_summary = f"{recommendation} — {final_score}/100 — {warnings[0] if warnings else 'aucun risque majeur détecté'}"
```

Ce qui donnerait par exemple : `"BUY — 82/100 — Batterie non incluse"`.

### Pourquoi ce serait utile

- Une bulle flottante overlay sur mobile a un **espace d'affichage très limité** (quelques
  centimètres carrés au-dessus d'une app tierce) — un résumé tenant sur **une seule ligne** est
  beaucoup plus adapté qu'un ensemble de champs à recomposer.
- Cela **évite au client mobile de reconstruire lui-même** cette logique de résumé (format,
  priorisation du premier warning, gestion du cas "pas de warning") — la règle métier resterait
  centralisée côté backend, cohérente avec le reste du contrat, et réutilisable telle quelle par
  tout futur client (mobile, extension navigateur, etc.) sans dupliquer la logique.
- Comme il s'agirait d'un champ **optionnel** en plus des champs existants, cela ne casserait rien
  côté frontend web actuel (`AnalysisOut`/`AIAnalysisResult` restent rétro-compatibles).

### Ce que cette section n'est PAS

Cette proposition est une **recommandation pour un futur lot de développement**. Elle n'est **pas
implémentée dans ce lot** : aucun champ n'a été ajouté à `backend/app/schemas/analysis.py`, ni à
aucun autre fichier du backend. Le fichier `analysis.py` (schémas) est actuellement modifié en
parallèle par un autre agent dans le cadre du module "analyse multi-captures" — cette suggestion
lui est simplement transmise comme piste, à évaluer et implémenter (ou non) dans son propre lot.

---

## 6. Hors scope maintenant

Les éléments suivants sont explicitement **hors scope de ce document et de ce lot** — ils
concernent un futur chantier de développement Android complet, non entamé ici :

- **Le projet Android complet (APK)** : structure du projet Kotlin, écrans, cycle de vie de l'app,
  build Gradle, signature de l'APK.
- **Le flux d'authentification mobile détaillé** (écran de login natif, gestion du refresh token,
  déconnexion) — seule l'hypothèse "le token JWT est déjà obtenu au login dans l'app" est posée
  ici, pas son implémentation.
- **Tests sur device réel** (différentes versions d'Android, différents fabricants, comportement du
  `Foreground Service` et de `MediaProjection` selon les restrictions constructeur type
  MIUI/EMUI/OneUI).
- **Gestion offline / retry des uploads** (file d'attente persistante en cas de perte réseau
  pendant l'upload batch, reprise après coupure, gestion des uploads partiels).
- **Gestion des quotas / rate-limiting côté mobile** (limitation du nombre d'analyses par
  utilisateur/jour, comportement UI en cas de 429, etc.).
- **Publication Play Store** (fiche store, politique de confidentialité spécifique à l'usage de
  `SYSTEM_ALERT_WINDOW` et `MediaProjection`, revue de conformité Google, gestion des versions).
- **Implémentation du champ `mobile_summary`** décrit en section 5 (recommandation uniquement, à
  planifier dans un futur lot backend).
