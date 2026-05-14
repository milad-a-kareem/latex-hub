# latex-hub

An online LaTeX editor and build service — collaborative, browser-based, with
server-side compilation via [Tectonic](https://tectonic-typesetting.github.io/).
Inspired by Overleaf.

## Stack

| Layer        | Tech                                                         |
| ------------ | ------------------------------------------------------------ |
| Frontend     | Vite + React 19 + TypeScript, Tailwind v4, shadcn/ui, Monaco |
| PDF viewer   | pdf.js (`pdfjs-dist`)                                        |
| Collab       | Yjs (`y-monaco`, `y-websocket` client; `pycrdt` server)      |
| Backend      | FastAPI (Python 3.13), `uv` + `ruff` + `mypy`                |
| LaTeX engine | Tectonic, invoked from the API container                     |
| Auth         | Firebase Auth (email/password)                               |
| Data         | Firestore (project + file metadata)                          |
| Blobs        | Firebase Storage (source tarballs, compiled PDFs)            |
| Hosting      | Frontend → Firebase Hosting; API → Google Cloud Run          |

## Layout

```
frontend/   Vite SPA
backend/    FastAPI app + Dockerfile for Cloud Run
infra/      Deploy manifests (Cloud Run service.yaml, firebase config)
```

See [CLAUDE.md](./CLAUDE.md) for development commands and architecture notes.

## Quick start

```sh
# Frontend
cd frontend && npm install && npm run dev

# Backend (in another shell)
cd backend && uv sync && uv run uvicorn app.main:app --reload
```

You will need a Firebase project; copy `frontend/.env.example` →
`frontend/.env.local` and `backend/.env.example` → `backend/.env`
and fill in the values.
