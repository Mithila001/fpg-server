import multiprocessing as mp
import os
from time import perf_counter

# Set start method to spawn to prevent thread inheritance issues on Linux (Ubuntu)
try:
    mp.set_start_method("spawn", force=True)
except RuntimeError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response, StreamingResponse


app = FastAPI(title="House Plan Generator API")


# CORS: read allowed origins from CORS_ORIGINS env var (comma-separated).
# Default permits the local Vite dev server used during development / presentation.
_raw_origins = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
ALLOWED_ORIGINS: list[str] = [
    o.strip() for o in _raw_origins.split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_api_requests(request, call_next):
    start = perf_counter()
    # If this is an SSE client, avoid consuming or re-injecting the body
    accept_header = request.headers.get("accept", "")
    if "text/event-stream" in accept_header:
        return await call_next(request)

    request_body = await request.body()

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": request_body, "more_body": False}

    request._receive = (
        receive  # Re-inject consumed request body for downstream handlers.
    )

    try:
        response = await call_next(request)
        # Detect streaming SSE responses by media_type or StreamingResponse
        media_type = getattr(response, "media_type", "")
        if media_type == "text/event-stream" or isinstance(response, StreamingResponse):
            return response

        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk

        response_headers = dict(response.headers)
        response_headers.pop("content-length", None)
        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=response_headers,
            media_type=response.media_type,
            background=response.background,
        )
    except Exception as exc:
        duration_ms = (perf_counter() - start) * 1000
        print(f"duration: {duration_ms}, Exception: {exc}")
        raise


from app.routes.generation import router as generation_router  # noqa: E402

app.include_router(generation_router)
