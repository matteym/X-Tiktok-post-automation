# X / TikTok / YouTube post automation

CLI that takes a video (or photos) + a short description, generates captions with **Grok**, then:

1. **Dedups** the media set in Postgres (skip or confirm if already posted)
2. Runs a **LangGraph** pipeline (understand → research → strategy → generate → validate)
3. **Publishes to X** (when credentials + API credits work)
4. Builds a **TikTok proposal** (live upload only if TikTok tokens are set)
5. **Uploads to YouTube** (unless you pass `--no-youtube`)

Package: `content-autopilot` in `src/backend`.

---

## Who this is for

You have media ready on disk and want one command to draft + publish across platforms, with AI captions and a local history of what you already posted.

---

## Prerequisites

| Tool | Why |
| --- | --- |
| [Docker](https://docs.docker.com/get-docker/) | Local Postgres |
| [uv](https://docs.astral.sh/uv/) | Python deps + CLI |
| Python **3.12+** | Via uv |
| [xAI API key](https://console.x.ai/) | Grok (`GROK_API_KEY`) — **required** |
| Optional: X, YouTube, TikTok, Apify | Only if you want that platform live |

---

## 5-minute setup

```bash
git clone https://github.com/matteym/X-Tiktok-post-automation.git
cd X-Tiktok-post-automation

cp .env.example .env
# Edit .env — at minimum set GROK_API_KEY and Postgres password (see below)

docker compose --env-file .env up -d
# Wait until postgres is healthy: docker compose ps
```

### Minimal `.env`

```env
POSTGRES_USER=app
POSTGRES_PASSWORD=changeme
POSTGRES_DB=app
DATABASE_URL=postgres://app:changeme@postgres:5432/app
DATABASE_URL_HOST=postgres://app:changeme@127.0.0.1:5433/app
GROK_API_KEY=xai-...
```

Notes:

- Host port is **5433** (avoids clashing with a local Postgres on 5432).
- If the password contains `%`, encode it as `%25` **only** in `DATABASE_URL` / `DATABASE_URL_HOST` (keep `POSTGRES_PASSWORD` literal).
- Always run commands from the **repo root** so `.env` is found.

---

## One command to run

```bash
uv run --project src/backend content-autopilot run \
  --video "/path/to/clip.mp4" \
  --description "What this post is about in plain language." \
  --github "https://github.com/you/repo" \
  --twitter "https://x.com/you" \
  --tiktok "https://www.tiktok.com/@you" \
  --youtube "https://www.youtube.com/@you"
```

Repeat `--video` for several files; **order is kept** (covers, clips, etc.).

### Useful flags

| Flag | Effect |
| --- | --- |
| `--video PATH` | Media file (repeatable) |
| `--description TEXT` | Source brief for Grok |
| `--github` / `--twitter` / `--tiktok` / `--youtube` | Profile/repo URLs woven into captions |
| `--title TEXT` | Optional YouTube title |
| `--no-youtube` | Skip YouTube upload; still run the rest |

---

## Modes of use (pick what you need)

### 1. Full autopilot (default)

Grok + X + TikTok proposal + YouTube.

Fill in the optional keys for each platform you want **live**. Missing keys = that step is skipped or proposal-only.

### 2. Generate + X, skip YouTube

```bash
uv run --project src/backend content-autopilot run \
  --video "/path/to/clip.mp4" \
  --description "..." \
  --no-youtube
```

### 3. YouTube only-ish

Leave X / TikTok keys empty in `.env`, keep YouTube secrets set. First upload opens a browser for Google OAuth. Use `--no-youtube` if you only want captions + TikTok proposal.

### 4. Proposal mode (no X credits / no TikTok token)

Leave X / TikTok tokens empty or without credits: you still get AI captions + a TikTok **proposal** text, and YouTube if configured.

---

## Where to get each `.env` value

Copy `.env.example` → `.env`, then fill only what you use.

### Always required

| Variable | How to get it |
| --- | --- |
| `GROK_API_KEY` | Create an account at [console.x.ai](https://console.x.ai/) → API keys → create a key (`xai-…`). `XAI_API_KEY` works as an alias. |
| `POSTGRES_*` + `DATABASE_URL*` | Local only — defaults in `.env.example` are fine. Host URL must use port **5433**. |

Optional: `XAI_MODEL` (default `grok-4-latest`).

### X (Twitter) — optional, for live tweets

1. Go to [developer.x.com](https://developer.x.com) / [console.x.com](https://console.x.com) → create an app.
2. Set app permissions to **Read and write**, save, then **regenerate** Access Token & Secret.
3. Copy into `.env`:
   - `X_API_KEY` / `X_API_SECRET` → Consumer Key & Secret  
   - `X_ACCESS_TOKEN` / `X_ACCESS_TOKEN_SECRET` → Access Token & Secret  
4. Buy **API credits** (pay-per-use). Without credits → `402 Payment Required` on tweet create.

Video uploads wait for X processing (~30–60s) before the tweet is created.

### YouTube — optional, for live uploads

1. Open [Google Cloud Console](https://console.cloud.google.com/) → create/select a project.
2. Enable **YouTube Data API v3**.
3. APIs & Services → Credentials → **Create OAuth client ID** (type Desktop / Web with `http://localhost` redirect is fine for local CLI).
4. Download the JSON → save it at the repo root as `client.yt.json` (or another path).
5. In `.env`:
   - `YOUTUBE_CLIENT_SECRETS_FILE=client.yt.json`  
   - `YOUTUBE_TOKEN_FILE=youtube_token.json` (created automatically after the first browser login)

First `content-autopilot run` that uploads to YouTube opens a browser; approve access once.

### TikTok — optional

From the [TikTok for Developers](https://developers.tiktok.com/) portal: `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, and a user `TIKTOK_ACCESS_TOKEN`. All three required for live upload; otherwise you only get a **proposal**.

### Apify — optional research

Token from [apify.com](https://apify.com/) → `APIFY_API_TOKEN`. Used to scrape `--github` / profile URLs for extra context.

---

## What you’ll see

```
description: ...
media_fingerprints: ...
media_set_hash: ...
Starting content-autopilot pipeline...
-> Understand
-> Research
-> Analyze
-> Strategy
-> Generate
-> Validate
-> Publish
-> TikTok
-> YouTube
X post URL: https://x.com/i/web/status/...   # or none
TikTok proposal (...): ...
YouTube watch URL: https://www.youtube.com/watch?v=...
```

If the same media was already posted:

```
Warning: This media set was already posted
Proceed with posting this media set again? [y/N]
```

Default is **no** (safe).

---

## Common problems

| Symptom | Fix |
| --- | --- |
| Postgres password auth failed | Match `POSTGRES_*` with URLs; encode `%` as `%25` in URLs; use port **5433**; `docker compose down -v && docker compose up -d` if the volume was created with an old password |
| `Model not found: grok-2-...` | Use a current model (`XAI_MODEL=grok-4-latest`) |
| X `402 Payment Required` | Buy API credits in the X developer console |
| X `400` / invalid media IDs | Wait for video processing (fixed in current client via STATUS polling); retry |
| X `401` on upload | Regenerate OAuth 1.0a tokens after enabling Read and write |
| `X post URL: none` | X step soft-skipped after an HTTP error — check credits, Read and write tokens, and regenerate access tokens |
| YouTube OAuth loop | Re-download OAuth client JSON, check redirect URI / Desktop app type, delete `youtube_token.json` and retry |
| Root CI / pytest | Real tests live under `src/backend` |

Deep internals (schema, graph, env sync): see [`infra.md`](./infra.md).

---

## Dev / tests

```bash
uv run --project src/backend python -m pytest -q
```

---

## License

See [`LICENSE`](./LICENSE).
