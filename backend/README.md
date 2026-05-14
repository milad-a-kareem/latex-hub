# latex-hub backend

FastAPI service exposing:

- `GET/POST /api/projects` — project CRUD (Firestore)
- `GET/PUT /api/projects/{id}/files/...` — file ops (Firestore + Storage)
- `POST /api/projects/{id}/compile` — invoke Tectonic, upload PDF, return signed URL
- `WS  /ws/collab` — Yjs sync server (pycrdt-websocket)

## Dev

```sh
uv sync
uv run uvicorn app.main:app --reload --port 8080
```

Tectonic must be on `PATH`. The Docker image installs it; for local dev see
<https://tectonic-typesetting.github.io/en-US/install.html>.
