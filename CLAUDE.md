# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

An Overleaf-style web app: collaborative LaTeX editing in the browser with
server-side compilation to PDF. Monorepo with two deployable units:

- `frontend/` — Vite + React 19 + TypeScript SPA, deployed to **Firebase Hosting**.
- `backend/` — FastAPI app (Python 3.13), deployed to **Google Cloud Run**.

Both share one Firebase project for **Auth (email/password)**, **Firestore**
(project + file metadata), and **Storage** (compiled PDF artifacts).

## Common commands

### Frontend (`cd frontend`, npm)

```sh
npm install
npm run dev              # vite, default port 5173, proxies /api and /ws to backend
npm run build            # tsc -b && vite build  → frontend/dist
npm run lint             # eslint (flat config in eslint.config.js)
npm run lint:fix
npm run format           # prettier (with prettier-plugin-tailwindcss)
npm run typecheck        # tsc -b --noEmit
npm run test             # vitest (jsdom)
npm run test -- src/foo  # run a single test file or pattern
```

### Backend (`cd backend`, uv)

```sh
uv sync                                      # creates .venv from pyproject + lock
uv run uvicorn app.main:app --reload --port 8080
uv run ruff check .         # lint
uv run ruff format .        # format
uv run mypy app             # type check (strict)
uv run pytest               # tests
uv run pytest tests/test_health.py::test_healthz   # single test
```

### Deploy

```sh
# Frontend → Firebase Hosting (also wires Hosting → Cloud Run rewrites)
firebase deploy --only hosting,firestore,storage

# Backend → Cloud Run (builds via Cloud Build, deploys image)
PROJECT_ID=<gcp-project> infra/cloudrun/deploy.sh
```

`firebase.json` rewrites `/api/**` and `/ws/**` from the Hosting domain to the
Cloud Run service `latex-hub-api` in `us-central1`. Update the region/service
ID there if you change them.

## Architecture

```
Browser  ─────────────────────┐
  React + Monaco              │  HTTPS (REST)     ┌──────────────────────┐
  Yjs client                  ├──────────────────►│  FastAPI on Cloud Run│
  Firebase Auth (web SDK)     │  WSS  (Yjs sync)  │   app/main.py         │
                              │                    │   app/routers/*       │
                              │  ID tokens         │   app/ws/collab.py    │
                              ▼                    └────────┬─────────────┘
                       Firebase Hosting                     │
                       (static + rewrites)                  │ Admin SDK
                                                            ▼
                                            Firestore  +  Cloud Storage
                                            (projects)    (compiled PDFs)

                                            tectonic binary in container
                                            invoked per compile request
```

### Frontend layout

- `src/lib/firebase.ts` — single `initializeApp` for Auth/Firestore/Storage.
  All env comes from `VITE_FIREBASE_*` (see `.env.example`).
- `src/lib/api.ts` — `api<T>(path)` helper that auto-attaches the Firebase ID
  token as `Authorization: Bearer <jwt>`; `wsUrl(path)` for WebSockets.
- `src/features/auth/` — `AuthProvider` exposes `useAuth()`; `LoginPage` does
  email/password sign in + signup.
- `src/features/projects/` — list/create projects via REST.
- `src/features/editor/` — the editing surface:
  - `useYjsDoc(projectId, filePath)` opens a `WebsocketProvider` to
    `/ws/collab` with the user's ID token and exposes a `Y.Text`.
  - `LatexEditor` binds Monaco to that `Y.Text` via `y-monaco`'s
    `MonacoBinding`. **All edits flow through Yjs**, never directly to
    Firestore — Firestore stores snapshots, Yjs owns realtime state.
  - `PdfPreview` renders compiled PDFs with `pdfjs-dist` directly to a
    `<canvas>` (no react-pdf wrapper).
- `src/routes/router.tsx` — react-router with a `Protected` guard that
  redirects to `/login` when `useAuth()` reports no user.

### Backend layout

- `app/main.py` — `create_app()` wires CORS (from `CORS_ALLOW_ORIGINS`), the
  REST routers, the WS router, and a `/healthz` probe used by Cloud Run.
- `app/config.py` — `pydantic-settings` reads `.env`. `get_settings()` is
  `lru_cache`-d; reach for it via `Depends(get_settings)` or call directly.
- `app/firebase.py` — lazy `firebase_admin.initialize_app` (uses
  `GOOGLE_APPLICATION_CREDENTIALS` locally, ADC on Cloud Run). Exposes
  `db()`, `bucket()`, and `verify_id_token()`.
- `app/auth.py` — `CurrentUserDep` is the standard dependency for any
  authenticated route. It pulls `Authorization: Bearer …` and verifies the
  Firebase ID token.
- `app/routers/projects.py` — project CRUD + file PUT. Owned-by-uid check is
  enforced in `app/services/projects.py`, not in Firestore rules (see below).
- `app/routers/compile.py` — pulls files from Firestore, runs Tectonic via
  `app/services/tectonic.py`, uploads the PDF to Storage, returns a 30-min
  signed URL. **Compile failures return HTTP 200 with `pdfUrl=""` and `log`
  populated** — this is intentional so the client can show the build log
  without a network error path.
- `app/services/tectonic.py` — `compile_latex(workdir, files, entry)` writes
  sources to a fresh `uuid4()` subdir, runs `tectonic --keep-logs --outdir`,
  and tears the dir down in `finally`. Concurrent requests are safe because
  each gets its own dir.
- `app/ws/collab.py` — Yjs sync. Each `room` query param (`projectId:filePath`)
  maps to a `YRoom` held in memory by `pycrdt-websocket`'s `WebsocketServer`.
  **State is in-memory only right now**; on container scale-down or scale-out
  it is lost. For durability, hook `room.ydoc.observe` to debounce-write
  snapshots into Firestore — that's the intended next step.

### Why Firestore/Storage rules are deny-all

Both `infra/firestore.rules` and `infra/storage.rules` deny **all** client
access. Clients never talk to Firestore/Storage directly — they go through
the FastAPI backend, which uses the Admin SDK (bypasses rules) and enforces
ownership in code. If you find yourself wanting to read Firestore from the
React app, add an API endpoint instead. Keep the deny-all rules intact.

### Cloud Run notes that matter

- The Dockerfile is multi-stage: it pulls the pinned Tectonic release into a
  scratch stage, `uv sync`s deps into a venv stage, then assembles a small
  python:3.13-slim runtime. Bump `TECTONIC_VERSION` in `backend/Dockerfile`
  to upgrade the LaTeX engine.
- `sessionAffinity: true` and `cpu-throttling: false` are set on the service
  because the Yjs WebSocket connection must stick to one instance for the
  lifetime of the editing session.
- `minScale: 0` keeps cost low but means the first compile after idle pays a
  cold start (Tectonic also downloads packages on demand on first use,
  cached in the container's `/root/.cache`).

## Conventions

- TypeScript: `strict` + `noUnusedLocals` + `verbatimModuleSyntax`. Use
  `import type { … }` for type-only imports.
- Python: `ruff` is the only linter+formatter; `mypy --strict` must pass.
  Prefer `Annotated[T, Depends(...)]` for FastAPI deps.
- Path alias `@/` → `frontend/src/` (see `tsconfig.app.json` and
  `vite.config.ts`). Don't import with deep relative paths from `src/`.
- shadcn/ui components live in `frontend/src/components/ui/` and are added
  via `npx shadcn@latest add <name>` — they're checked in and editable.
- Tailwind v4: config lives in `src/index.css` via `@theme` + CSS variables.
  There is no `tailwind.config.js`.

## CI/CD

GitHub Actions workflows live in `.github/workflows/`:

- `ci.yml` — runs on PRs and pushes to `main`. Two jobs: frontend
  (`npm run lint`, `typecheck`, `test`, `build`) and backend (`ruff check`,
  `ruff format --check`, `mypy`, `pytest`).
- `deploy.yml` — runs on pushes to `main` (and `workflow_dispatch`). Three
  **parallel** jobs:
  1. `backend` — `gcloud builds submit` builds the image, then
     `gcloud run deploy` rolls it out. Cloud Run runtime SA is the **same SA**
     that authenticates the workflow (read from `client_email` in the key).
  2. `rules` — `firebase deploy --only firestore,storage` ships the rules and
     the Firestore index defined in `infra/firestore.indexes.json`.
  3. `frontend` — Resolves the Firebase Web SDK config at deploy time via
     `firebase apps:sdkconfig WEB --json`, builds with those values, then
     `firebase deploy --only hosting`.

### Required GitHub configuration (one secret, one variable)

**Secret:**
- `GCP_SA_KEY` — JSON service-account key. Reused for *everything*: the
  GitHub Actions deployer, the Cloud Run runtime identity, and the
  Firebase Admin SDK on Cloud Run.

  Grant this SA the following roles on the project:
  | Role                              | Why                                   |
  | --------------------------------- | ------------------------------------- |
  | `roles/run.admin`                 | Deploy Cloud Run revisions            |
  | `roles/iam.serviceAccountUser`    | Act-as itself as the runtime SA       |
  | `roles/cloudbuild.builds.editor`  | Build the container image             |
  | `roles/artifactregistry.writer`   | Push the image                        |
  | `roles/storage.admin`             | Cloud Build staging + signed URLs     |
  | `roles/firebasehosting.admin`     | Deploy Hosting                        |
  | `roles/firebaserules.admin`       | Deploy Firestore/Storage rules        |
  | `roles/datastore.indexAdmin`      | Deploy Firestore indexes              |
  | `roles/datastore.user`            | Runtime reads/writes to Firestore     |

**Variable:**
- `GCP_PROJECT_ID` — Firebase/GCP project ID.

**Optional variables:**
- `GCP_REGION` (defaults to `us-central1`).
- `FIREBASE_WEB_APP_ID` — only needed if the project has more than one
  registered Web app; otherwise `apps:sdkconfig WEB` picks the lone one.

The frontend's `VITE_FIREBASE_*` values are **not** GitHub secrets/vars —
they're fetched from Firebase at deploy time. The Firebase web config is
public anyway (it ends up in the JS bundle); fetching it just avoids the
config drift you get from manually mirroring it into GitHub Variables.

### Workload Identity Federation (alternative, zero secrets)

`google-github-actions/auth@v2` also supports keyless OIDC via Workload
Identity Federation. If you'd rather not store a JSON key, swap
`credentials_json` for `workload_identity_provider` + `service_account` and
add the SA's `iam.workloadIdentityUser` binding on the WIF pool. The rest of
the workflow is unchanged.

## Open follow-ups

These are known gaps, not bugs:

1. Yjs room state is not persisted. Snapshot to Firestore on debounce inside
   `app/ws/collab.py`.
2. There's no file tree UI yet — the editor hard-codes `main.tex`. The
   backend already stores `files: { path: content }` per project, so a tree
   view + the existing `PUT /api/projects/{id}/files/{path}` is enough.
