# Infra — content-autopilot

CLI Python qui prend des médias + une description, déduplique dans Postgres, génère le contenu avec Grok (LangGraph), publie sur X, et produit (ou uploade) une proposition TikTok.

Repo produit : `X-Tiktok-post-automation`. Le moteur DAG `agent-loop-autonomous-TDD-dag-runner/` est un plugin gitignoré ; il n’est **pas** l’app.

---

## 1. Vue d’ensemble

```
opérateur
    │  content-autopilot run --video … --description …
    ▼
CLI (Typer) ──► orchestration
                    │
                    ├─ fingerprints SHA-256 + taille (ordre --video)
                    ├─ Postgres post_runs (dedup + persist)
                    └─ LangGraph
                          Understand → Research → Analyze → Strategy
                          → Generate → Validate
                                │ pass                  │ fail
                                ▼                       ▼
                         Publish X                 TikTok proposal
                                │                       │
                                └──────────► TikTok ────┘
                                             persist metadata
```

Entry point installé : `content-autopilot` → `content_autopilot.cli:main`.

---

## 2. Arborescence

```
X-Tiktok-post-automation/
├── infra.md                          ← ce fichier
├── README.md
├── LICENSE
├── docker-compose.yml                Postgres 16 (seul datastore)
├── .env                              secrets locaux (gitignoré)
├── .env.example                      clés sans secrets
├── .github/workflows/ci.yml          pytest via uv si pyproject.toml
├── .cursor/                          skill / hooks copiés à l’init
├── src/.gitkeep
└── src/backend/                      package Python content-autopilot
    ├── pyproject.toml
    ├── uv.lock
    ├── src/content_autopilot/
    │   ├── __init__.py
    │   ├── cli.py                    Typer : commande `run`
    │   ├── orchestration.py          dedup → graphe → persist
    │   ├── settings.py               pydantic-settings + dotenv
    │   ├── media/
    │   │   ├── fingerprint.py        SHA-256:size + set hash
    │   │   └── run_inputs.py         validation chemins + fingerprints
    │   ├── db/
    │   │   ├── models.py             table post_runs
    │   │   ├── schema.py             create_all
    │   │   └── repository.py         find / save
    │   └── graph/
    │       ├── state.py              ContentAutopilotState
    │       ├── workflow.py           StateGraph + route validate
    │       ├── nodes.py              8 nœuds métier
    │       ├── clients.py            Grok, X, Apify, TikTok
    │       └── oauth1.py             signature OAuth 1.0a (X)
    └── tests/                        pytest (cwd src/backend)
```

Le plugin `agent-loop-autonomous-TDD-dag-runner/` n’est pas versionné dans le repo produit. Il orchestre `yarn task` (plan, TDD, commit, PR) et **réécrit** `.env` depuis `.env.example` + alias (voir §4.3). Il ne contient pas le code de posting.

---

## 3. Fichiers applicatifs

| Fichier | Rôle |
|---|---|
| `cli.py` | Groupe Typer `content-autopilot`. Commande `run`. Invocation vide → exit 0 (compat console script). |
| `orchestration.py` | Enchaîne collect médias → settings → dedup confirm → `graph.invoke` → persist. Exit 1 si média manquant ou validation KO. |
| `settings.py` | Charge `.env` (cwd, ou remontée jusqu’à la racine produit hors pytest). `DATABASE_URL` + `GROK_API_KEY` obligatoires. |
| `media/fingerprint.py` | Lecture par chunks 64 KiB. Empreinte `{sha256_hex}:{size}`. Set hash = SHA-256 des empreintes jointes par `\n` (**sensible à l’ordre**). |
| `media/run_inputs.py` | Vérifie fichiers lisibles, conserve l’ordre CLI, calcule fingerprints + set hash. |
| `db/models.py` | ORM `PostRun` / table `post_runs`. |
| `db/schema.py` | `Base.metadata.create_all` au premier `from_settings`. |
| `db/repository.py` | `find_existing_by_media_set`, `save_post_metadata`. URL SQLAlchemy via `resolve_database_url` + driver `postgresql+psycopg`. |
| `graph/state.py` | État LangGraph (description, médias, sorties Grok, validation, URLs). |
| `graph/workflow.py` | Graphe compilé. Après `validate` : `publish_x` si OK, sinon skip X → `tiktok_proposal`. |
| `graph/nodes.py` | Understand, Research, Analyze, Strategy, Generate, Validate, Publish X, TikTok. |
| `graph/clients.py` | HTTP réel (httpx). X OAuth 1.0a, Apify crawler, TikTok inbox upload, Grok chat. |
| `graph/oauth1.py` | HMAC-SHA1 pour l’API X. |

Tests (tous `uv run python -m pytest -q` dans `src/backend`) :

| Test | Couvre |
|---|---|
| `test_scaffold.py` | package, deps, console script |
| `test_postgres_compose.py` | Compose postgres |
| `test_media_fingerprint.py` | empreintes / ordre / chemins |
| `test_settings.py` | env, alias XAI / typos X, dotenv, psycopg URL |
| `test_post_schema.py` / `test_post_repository.py` | modèle + repo |
| `test_cli_media_args.py` | flags Typer |
| `test_langgraph_*.py` | nœuds et graphe |
| `test_cli_orchestration_run.py` | flux CLI + dedup |
| `test_live_clients.py` | X / Apify / TikTok avec httpx mocké |

---

## 4. Environnement

### 4.1 Fichiers

- **`.env`** — jamais commité. Secrets + URLs. Lu par `load_settings()` (produit) et `docker compose --env-file .env`.
- **`.env.example`** — versionné. Même clés, valeurs factices / vides. Source pour le sync orchestrateur.

Recherche du `.env` applicatif :

1. Hors pytest : `cwd/.env`, puis parents, puis parents de `settings.py` (jusqu’à la racine git produit).
2. Sous pytest : uniquement `cwd/.env` (pas de fuite des secrets du poste).

Les variables **déjà présentes** dans le process gagnent (`load_dotenv(..., override=False)`).

### 4.2 Clés

**Obligatoires (app crash au load sinon)**

| Variable | Usage |
|---|---|
| `DATABASE_URL` | Postgres **réseau Compose** (`@postgres:5432`). |
| `GROK_API_KEY` | xAI / Grok. Alias accepté : `XAI_API_KEY`. |

**Postgres Compose**

| Variable | Usage |
|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Image `postgres:16-alpine`. |
| `DATABASE_URL_HOST` | Même DSN, hôte `127.0.0.1` pour le CLI **sur la machine**. |

Le CLI n’utilise pas `DATABASE_URL` aveuglément : si le hostname docker (`postgres`) ne résout pas (`socket.getaddrinfo` échoue), il bascule sur `DATABASE_URL_HOST`. Dans Compose, `postgres` résout → URL docker.

`postgres://…` est réécrit en `postgresql+psycopg://…` pour SQLAlchemy.

**X (optionnel — sans les 4, pas de post live)**

| Variable | Usage |
|---|---|
| `X_API_KEY` / `X_API_SECRET` | Consumer OAuth 1.0a |
| `X_ACCESS_TOKEN` | Alias : `X_ACCES_TOKEN` |
| `X_ACCESS_TOKEN_SECRET` | Alias : `X_ACCES_SECRET`, `X_ACCESS_SECRET` |
| `X_API_BASE_URL` | défaut `https://api.twitter.com` |
| `X_UPLOAD_BASE_URL` | défaut `https://upload.twitter.com` |

**Autres optionnels**

| Variable | Usage |
|---|---|
| `APIFY_API_TOKEN` | Research web. Acteur défaut `apify~website-content-crawler` (`APIFY_ACTOR_ID`). |
| `APIFY_API_BASE_URL` | défaut `https://api.apify.com` |
| `TIKTOK_ACCESS_TOKEN` | Obligatoire pour upload live (inbox). |
| `TIKTOK_CLIENT_KEY` / `TIKTOK_CLIENT_SECRET` | Requis avec le token pour considérer les credentials TikTok complets. |
| `TIKTOK_API_BASE_URL` | défaut `https://open.tiktokapis.com` |
| `XAI_API_BASE_URL` | défaut `https://api.x.ai/v1` |
| `XAI_MODEL` | défaut `grok-4-latest` |
| `APP_PORT` | héritage init (pas utilisé par le CLI) |
| `CURSOR_API_KEY` | moteur DAG uniquement, pas l’app |

Aucun secret ne doit figurer dans `infra.md`, le DAG JSON, ou git.

### 4.3 Alignement automatique (agent-loop)

L’orchestrateur (`dag/src/init/env-sync.ts`) relit l’env **au start du loop et avant chaque nœud** :

1. Copie alias → nom canonique **seulement si le canonique est vide** (`XAI_API_KEY` → `GROK_API_KEY`, typos X → `X_ACCESS_*`).
2. Ajoute les clés manquantes depuis `.env.example` (sans écraser).
3. Dérive `*_HOST` depuis les URLs docker (`@postgres` → `@127.0.0.1`) si `DATABASE_URL_HOST` est vide.

Ça n’écrase jamais une valeur non vide.

---

## 5. Database

### 5.1 Runtime

```yaml
# docker-compose.yml
postgres:
  image: postgres:16-alpine
  ports: ["5433:5432"]  # host 5433; container still 5432 (avoids local postgres.exe)
  env: POSTGRES_USER / PASSWORD / DB
  volume: pgdata
  healthcheck: pg_isready
```

Démarrage (racine produit) :

```bash
docker compose --env-file .env up -d
```

Le DAG relance Compose si `docker-compose.yml` ou `.env.example` change (`docker compose up --build -d`).

Tests : `DATABASE_URL` absent → SQLite mémoire (`conftest.py`). Pas de Postgres requis pour pytest.

### 5.2 Schéma `post_runs`

Créé automatiquement (`create_all`) au premier `PostRunRepository.from_settings`.

| Colonne | Type | Contenu |
|---|---|---|
| `id` | int PK | run |
| `media_set_hash` | varchar(128) | SHA-256 de la liste ordonnée d’empreintes |
| `media_fingerprints` | JSON list | `["<sha256>:<bytes>", …]` ordre `--video` |
| `filenames` | JSON list | noms de fichiers (pas les chemins) |
| `description` | text | `--description` |
| `github_url` | varchar 2048 nullable | `--github` |
| `tiktok_url` | varchar 2048 nullable | `--tiktok` (URL d’entrée, pas le post TikTok) |
| `x_post_url` | varchar 2048 nullable | URL du tweet, ou null si skip / pas de credentials |
| `tiktok_proposal` | text nullable | JSON structuré (caption, hashtags, mode, media_order, publish_id) |
| `created_at` | timestamptz UTC | horodatage du persist |

**Dedup** : `find_existing_by_media_set(hash, fingerprints)`. Même set **dans le même ordre**. Fichiers identiques dans un autre ordre = autre hash → pas un doublon.

Si un match existe : warning + prompt `[y/N]` (défaut **non**). Refus → exit 0, pas de graphe, pas de nouvelle ligne. Confirm → graphe + **nouvelle** ligne `post_runs`.

Validation KO → **aucune** ligne écrite (évite de marquer un set comme « déjà posté » alors que X n’a pas été appelé).

---

## 6. Métadonnées runtime (hors Postgres)

| Donnée | Où | Vie |
|---|---|---|
| Empreinte fichier | calculée, pas un fichier | `{sha256}:{size}` |
| `media_set_hash` | calculée + colonne SQL | identifiant du set |
| État LangGraph | mémoire d’un `invoke` | voir `ContentAutopilotState` |
| DAG `task.json` / `*.done.json` / `state.json` | `dag/metadata/` (gitignoré) | file d’exécution agent-loop |
| `dag/history/nodes.jsonl` | gitignoré | un JSON par nœud DAG |
| `dag/logs/run-*.log` | gitignoré | journal orchestrateur |

L’app de posting **ne lit pas** les metadata DAG. Ce sont deux couches : produit (`post_runs`) vs runner (`task.json`).

État graphe (champs principaux) :

- entrée : `description`, `filenames`, `media_paths`, `media_fingerprints`, `github_url`, `tiktok_url`
- understand : `media_count`, `media_types`, `understanding_summary`
- research : `x_context`, `web_research`, `research_summary`
- analyze / strategy / generate : insights, angle, tone, hashtags, `x_post_text`, `tiktok_proposal`
- validate : `validation_passed`, `validation_errors`
- publish : `x_post_url`, `tiktok_proposal_structured`

---

## 7. Pipeline commande → post

### 7.1 Commande

Depuis `src/backend` (uv) ou avec le script installé :

```bash
cd src/backend
uv run content-autopilot run \
  --video ./clip.mp4 \
  --video ./cover.jpg \
  --description "Launch recap" \
  --github https://github.com/org/repo \
  --tiktok https://www.tiktok.com/@x/video/1
```

| Flag | Requis | Comportement |
|---|---|---|
| `--video` | oui, ≥ 1, répétable | photos/vidéos, **ordre conservé** pour X |
| `--description` | oui | brief humain → Grok |
| `--github` | non | hint research (Apify si token) |
| `--tiktok` | non | hint research, pas la destination de publish |

Typer refuse un chemin inexistant / illisible avant `execute_run`.

### 7.2 Étapes (code)

1. **Collect** — `collect_run_media` : existence, 1 octet lisible, fingerprints, set hash.
2. **Echo** — description, fingerprints, set hash.
3. **Settings** — dotenv + validation pydantic.
4. **Schema** — `create_all` si tables absentes.
5. **Dedup** — match hash + liste d’empreintes → confirm ou abort.
6. **Graphe** — `build_content_autopilot_graph(settings).invoke(state)`.
7. **Validate fail** — message, exit 1, **pas** de persist.
8. **Echo** — URL X, résumé TikTok.
9. **Persist** — `save_post_metadata`.
10. **Exit 0**.

### 7.3 Nœuds LangGraph

```
START
  → understand     Grok : brief + types médias + hints URLs
  → research       timeline X (si creds) + Apify (si token + URLs) + Grok
  → analyze        Grok : insights
  → strategy       Grok : angle / tone / hashtags
  → generate       Grok : texte X + script/caption TikTok
  → validate       règles locales, pas d’API
        │
        ├─ validation_passed  → publish_x
        │                         upload médias ordre CLI
        │                         POST /2/tweets  (OAuth 1.0a)
        │                         x_post_url ou null si pas de creds
        │                              ↓
        └─ fail ──────────────────────→ tiktok_proposal
                                          mode proposal, ou live inbox
                                          si token TikTok + validation OK
                                          ↓
                                        END
```

**Validate** (coupe le publish X) :

- texte X vide → policy
- texte X > 280 caractères → length
- `len(media_paths) != media_count` → media

**Publish X**

- skip si `validation_passed` est faux ou credentials incomplets → `x_post_url = null`
- photos : `POST upload.twitter.com/1.1/media/upload.json`
- vidéos : INIT / APPEND (4 MiB) / FINALIZE
- tweet : `POST api.twitter.com/2/tweets` + `media_ids`
- URL renvoyée : `https://x.com/i/web/status/{id}`

**TikTok**

- sans les 3 clés, ou validation KO : `publish_mode=proposal` (JSON caption / hashtags / `media_order`)
- avec credentials et validation OK : `POST …/v2/post/publish/inbox/video/init/` puis PUT `upload_url` (premier fichier vidéo du set)

**Grok** : `POST {XAI_API_BASE_URL}/chat/completions`, Bearer `GROK_API_KEY`.

**Apify** : `POST /v2/acts/{actor}/run-sync-get-dataset-items?token=…` avec `startUrls`.

---

## 8. Services externes

| Service | Quand | Auth |
|---|---|---|
| Postgres | toujours (CLI réel) | DSN |
| xAI Grok | chaque nœud LLM | `GROK_API_KEY` |
| X | research + publish | OAuth 1.0a 4 clés |
| Apify | research si token **et** `--github` / `--tiktok` | token query |
| TikTok Open API | live seulement si 3 clés + vidéo | Bearer access token |

Pas de Redis / Mongo / Neo4j / MySQL dans ce produit. Compose n’a que Postgres.

---

## 9. Lancer en local

Prérequis : Docker, Python 3.12+, [uv](https://docs.astral.sh/uv/), clés dans `.env`.

```bash
# 1. Postgres
docker compose --env-file .env up -d

# 2. Dépendances
cd src/backend
uv sync

# 3. Tests (SQLite, pas besoin de Postgres)
uv run python -m pytest -q

# 4. Run réel (Postgres hôte + APIs)
uv run content-autopilot run \
  --video /chemin/clip.mp4 \
  --description "…"
```

CI (`.github/workflows/ci.yml`) : job `test`, étape Python = `uv run python -m pytest -q` pour chaque `pyproject.toml` (hors `dag/`).

---

## 10. Limites actuelles

- Le CLI affiche les 8 étapes **avant** `invoke` (ordre visuel, pas un vrai stream nœud par nœud).
- TikTok live = inbox upload, pas un Direct Post public ; il faut un `TIKTOK_ACCESS_TOKEN` OAuth, pas seulement client key/secret.
- X/Apify/TikTok dépendent des quotas et de la validité des tokens ; les tests HTTP sont mockés.
- `create_all` n’est pas un outil de migration versionné (Alembic absent).
- Le plugin agent-loop n’est pas déployé avec l’app ; c’est l’usine à commits/PR.
