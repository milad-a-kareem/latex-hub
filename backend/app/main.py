from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import compile as compile_router
from .routers import projects as projects_router
from .ws import collab as collab_ws


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with collab_ws.websocket_server:
        yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="latex-hub", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(projects_router.router)
    app.include_router(compile_router.router)
    app.include_router(collab_ws.router)
    return app


app = create_app()
