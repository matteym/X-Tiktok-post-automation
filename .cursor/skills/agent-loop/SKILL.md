---
name: agent-loop
description: >-
  Master operational protocol for the Cursor SDK DAG (dag/run-dag-loop.ts,
  dag/metadata/task.json or --dagfile). Apply on every Agent.send turn, DAG node,
  agent-loop step, or autonomous change. Local Agent.create only. Orchestrator
  owns tests, guard, commit verify, archive, and next.
---

# Agent-loop protocol

Runtime: one local agent handle (Cursor `@cursor/sdk` or Claude Code SDK) plus one send per node and fix round. No pstack. MCP is optional read-only context.

Operator manual: `dag/README.md`. Default: clone this engine inside a product git repo, then from `dag/`, `yarn run init --remote=https://github.com/OWNER/REPO.git` then `yarn task "intent"`. Expert/CI: `yarn task --dagfile=<your.json>`.

## Split of duties

| Actor | Owns | Never |
|---|---|---|
| Agent (`send`) | READ PLAN INSPECT IMPLEMENT, COMMIT NOW with exact DAG `commit` | `git push`, `--no-verify`, `terraform apply` / `destroy`, edit `.env`, write `metadata/state.json`, edit `metadata/task.json` / `*.done.json` |
| Orchestrator (`dag/run-dag-loop.ts`) | TEST, GUARD, keep `.github/workflows/ci.yml` (written at init; skip missing languages), COMMIT NOW send, verify/fallback commit, archive to sibling `*.done.json`, history line, NEXT, 5 fix rounds, revert; `git push` at init; after each node fetch+rebase onto origin then `git push` + `gh pr create` (reuse if the PR exists) unless `--no-push`. Never `--force`; never drop remote commits. | cloud Agent VM, live OAuth, EAS, `terraform apply` |

Ticket prompt in the loaded DAG JSON wins on **scope**. This file wins on **git, secrets, apply**.

## SECTION 1 — Source of truth

1. Load this skill and `.cursor/rules/agent-loop.mdc`. Other project skills if they match the ticket.
2. Read the current node in the DAG JSON (`--dagfile` or `dag/metadata/task.json`). The orchestrator appends a deterministic repo briefing (inventoried packages, this node's tests, exact commit subject, forbidden paths). Do not treat the briefing as extra scope.
3. Copy APIs from existing code in this repo. Do not invent syntax.
4. Do not use MCP to mutate cloud state.

## SECTION 2 — Readiness

1. Read `package.json` / `pyproject.toml` / `tsconfig.json` of packages you will touch. Do not add a lint script unless the ticket says so.
2. `tests` on this DAG node are the gate. Do not invent a second test runner.
3. Match existing test commands and layout. `optionalCwd` is only for a **new** product path not yet in inventory (plan time). After GREEN the folder must exist and node tests must EXIT 0. Missing cwd does not skip tests.
4. No new `fallback-secret`. No hardcoded `http://localhost` / `http://127.0.0.1` in application source (use env vars). Allowlisted: e2e tests, conftest, compose, prometheus yml, schema.sql, `.cursor/`, `dag/`, markdown.

## SECTION 3 — Loop

Do not run extra SDK roundtrips for lint/commit. Orchestrator owns TEST, GUARD, COMMIT NOW.

`run.wait()` is `"finished" | "error" | "cancelled"`. Only `"finished"` continues. There is no `"success"`.

No tests: one send, then GUARD + COMMIT NOW (`allowEmptyCommit` if needed). With tests, TDD:

1. **RED** — failing tests only. Orchestrator runs `tests` from the DAG. Up to 2 more red sends if still green. Do not commit.
2. **GREEN** — minimal production code. Do not commit.
3. **GUARD + TEST** — `node .cursor/hooks/guard-anti-patterns.mjs` then DAG tests. Up to 5 fix sends. Do not commit.
4. **COMMIT NOW** — exact `commit` string, no `--no-verify`, no push. Orchestrator verifies `git log -1 --format=%s`, else fallback. Init already wrote `.github/workflows/ci.yml`; after node tests pass the orchestrator keeps that file current (do not invent a second workflow). Then move the task to sibling `*.done.json` and `chore(config): archive dag node <id>`. History line in `dag/history/nodes.jsonl` (gitignored). Run log in `dag/logs/run-YYYYMMDD-HHmmss.log` (gitignored).

CLI (from `dag/`): `yarn run init --remote=https://github.com/OWNER/REPO.git` (or `--repo=`), `yarn task "intent"`, `yarn test`. Nested plugin: init writes one level up (`../`) on the parent git repo and gitignores this engine folder. The CLI parks the nested engine `.git` as `.git.engine` so git from `dag/` is the product. Task flags only: `--dagfile=<path>`, `--push=false` / `--no-push`, `--provider=cursor|claude`. No `DAG_*` environment variables.

## SECTION 4 — Failure

Up to 5 fix sends. Then `dag/logs/failures.log`, `git reset --hard HEAD` (tracked only, no `git clean -fd`), history `status=failed`, exit non-zero. Node is not archived.

## SECTION 5 — Zero bypass

- `--no-verify`, `--no-gpg-sign`, `git push`, `git commit` except COMMIT NOW with the exact subject
- `eslint-disable`, `@ts-ignore`, `@ts-nocheck`, new `: any` / `as any`
- `it.skip`, `describe.skip`, `xtest`, `xit`, deleting tests to go green
- weakening `.cursor/hooks/` or this skill
- Countly, `sentry.io` as DSN host, Datadog
- `terraform apply`, `terraform destroy`
- logging password, token, authorization, refresh token, DSN, API keys
- new `fallback-secret`; hardcoded localhost URLs in app source

## SECTION 6 — Done

1. Node tests EXIT 0, or empty tests plus `allowEmptyCommit`.
2. Guard EXIT 0.
3. Git commit subject matches the DAG `commit`.
4. Task removed from DAG JSON, appended to sibling `*.done.json`. Id in `dag/metadata/state.json` (gitignored). Agent never writes those files.
5. No secret in the commit. Diff stays in ticket scope.

## SECTION TASK

Human gives only the intent: from `dag/`, `yarn task "add JWT login on the API"`. Greenfield bootstrap is `yarn run init --remote=https://github.com/OWNER/REPO.git` (never `yarn init`): when this engine is nested in a product git repo, writes Compose, empty `src/`, `.cursor`, `.github/workflows/ci.yml` on the parent, gitignores this plugin folder, commits, and pushes `agent/init` on the **product** remote. `yarn task` does not replace init. Then one PLAN send (max 10 feature nodes; a full app or a module like auth may be several sequential tasks, including several in the same package). A new package (example `Client/`) may be a DAG node with `optionalCwd` and the test command for that language (`yarn test`, `uv`+pytest, `go test ./...`, `cargo test`) even if it is not in inventory yet; the agent must create the marker file and tests must pass. Inventoried packages keep their listed test command. FastAPI/gin/axum must not be planned as `yarn test`. The runner still owns TDD, guard, COMMIT NOW, and archive. Do not skip tests because the intent was a phrase or because the folder was missing at plan time. Skip the planner with `yarn task --dagfile=<your.json>`.

## ONBOARDING

Clone this engine inside the product git clone (or copy `dag/` and `.cursor/` to the product root). `git config user.name` / `user.email` on the **product**. From `dag/`: `yarn && yarn run init --remote=https://github.com/OWNER/REPO.git` (never `yarn init`) writes compose, `.env` (gitignored), app tree, `.cursor`, `.github/workflows/ci.yml` on the product root, gitignores the nested engine folder, commits, and pushes `agent/init`. Then `yarn task "…"`. Expert: `yarn task --dagfile=<your.json>`. Do not paste secrets into the DAG JSON.
