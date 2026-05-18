"""FastAPI application factory and process lifecycle."""

from __future__ import annotations

import contextlib

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.gzip import GZipMiddleware

from app import __version__
import app.core.settings as settings_mod
from app.api import automate_router, info_router, task_router
from app.core.access_log_middleware import install_http_access_log
from app.core.http_cache import NesqlQuestsCacheMiddleware
from app.core.logging import logger
from app.core.scheduler import start_scheduler, stop_scheduler
from app.core.tasks import migrate_legacy_files
from app.core.quest_cache import init_quest_cache_state
from app.core.nesql_shared import setup_nesql_state, teardown_nesql_state
from app.core.triggers import trigger_manager
from app.db.base import Base
from app.db.session import engine
from app.modules.autocraft import router as autocraft_router
from app.modules.craft import router as craft_router
from app.modules.events import router as events_router
from app.modules.monitor import router as monitor_router
from app.modules.nesql import router as nesql_router
from app.modules.quests import router as quests_router
from app.modules.robots import router as robots_router
from app.modules.worldmap import router as worldmap_router
from app.schemas import StandardResponseModel


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    init_quest_cache_state(app)
    setup_nesql_state(app)
    app.state.redis = None
    if settings_mod.settings.optional_redis_url:
        import redis.asyncio as redis_asyncio

        app.state.redis = redis_asyncio.from_url(
            settings_mod.settings.optional_redis_url,
            decode_responses=True,
        )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        await migrate_legacy_files()
    except Exception:
        logger.exception("legacy task migration failed; continuing")
    start_scheduler()
    logger.info("remote-gtnh-control backend v%s started", __version__)
    try:
        yield
    finally:
        redis_client = getattr(app.state, "redis", None)
        if redis_client is not None:
            try:
                await redis_client.close()
            except Exception:
                logger.exception("redis close failed")
            app.state.redis = None
        teardown_nesql_state(app)
        stop_scheduler()
        trigger_manager.stop_all()


def create_app() -> FastAPI:
    app = FastAPI(
        title="GTNH Cyber Supervisor",
        description="Backend for RemoteOC-GTNH-AE2 fork (remote-gtnh-control).",
        version=__version__,
        lifespan=lifespan,
    )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_, exc: HTTPException):
        return JSONResponse(
            status_code=500 if exc.status_code == 500 else 200,
            content=StandardResponseModel(
                code=exc.status_code, message=exc.detail, data=None
            ).model_dump(),
        )

    install_http_access_log(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(NesqlQuestsCacheMiddleware)

    app.include_router(task_router, prefix="/api/task", tags=["task"])
    app.include_router(automate_router, prefix="/api/automate", tags=["automate"])
    app.include_router(info_router, prefix="/api/info", tags=["info"])
    app.include_router(robots_router, prefix="/api/robots", tags=["robots"])
    app.include_router(autocraft_router, prefix="/api/autocraft", tags=["autocraft"])
    app.include_router(craft_router, prefix="/api", tags=["craft"])
    app.include_router(worldmap_router, prefix="/api/map", tags=["map"])
    app.include_router(quests_router, prefix="/api/quests", tags=["quests"])
    app.include_router(nesql_router, prefix="/api/nesql", tags=["nesql"])
    app.include_router(monitor_router, prefix="/api/monitor", tags=["monitor"])
    app.include_router(events_router, prefix="/api", tags=["events"])

    @app.get("/health", include_in_schema=False)
    async def health() -> dict:
        return {"code": 200, "message": "ok", "data": {"version": __version__}}

    return app


app = create_app()
