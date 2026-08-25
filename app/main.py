from __future__ import annotations

import multiprocessing as mp
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, cast

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException

from app.core_config import load_server_config
from app.jobs import GenerationJobManager
from app.routes.buildable_space import (
    buildable_space_context_middleware,
    router as buildable_space_router,
)
from app.routes.errors import (
    api_http_exception_handler,
    api_unexpected_exception_handler,
    api_validation_exception_handler,
)
from app.routes.generation import router as generation_router
from app.util.jsonl_logging import ApiLoggingMiddleware

try:
    mp.set_start_method("spawn", force=True)
except RuntimeError:
    pass

BOOT_CONFIG = load_server_config()


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    application.state.server_config = BOOT_CONFIG
    manager = GenerationJobManager(BOOT_CONFIG)
    application.state.job_manager = manager
    await manager.start()
    try:
        yield
    finally:
        await manager.shutdown()


app = FastAPI(
    title="Floor Plan Generator API",
    version="1.0.0",
    description=(
        "Independent buildable-space calculation and asynchronous floor-plan "
        "generation. All dimensions are integer project units; 10 units = 1 meter."
    ),
    lifespan=lifespan,
)
app.add_middleware(cast(Any, ApiLoggingMiddleware), config=BOOT_CONFIG)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(BOOT_CONFIG.server.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Last-Event-ID", "Authorization"],
    expose_headers=["X-Flow-ID", "X-Generation-Job-ID"],
)
app.middleware("http")(buildable_space_context_middleware)
app.add_exception_handler(
    RequestValidationError, cast(Any, api_validation_exception_handler)
)
app.add_exception_handler(HTTPException, cast(Any, api_http_exception_handler))
app.add_exception_handler(Exception, cast(Any, api_unexpected_exception_handler))
app.include_router(buildable_space_router)
app.include_router(generation_router)
