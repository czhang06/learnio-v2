import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .core.router import router as core_router
from .courses.router import router as courses_router
from .exams.router import router as exams_router
from .ingest import worker
from .ingest.router import router as ingest_router
from .questions.router import router as questions_router
from .users.router import router as users_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Run the ingestion worker alongside the API unless it is disabled."""
    if not settings.run_worker:
        yield
        return
    stop = asyncio.Event()
    task = asyncio.create_task(worker.run_forever(stop))
    try:
        yield
    finally:
        stop.set()
        await task


app = FastAPI(title="LearnIO", version="2.0.0", lifespan=lifespan)


@app.middleware("http")
async def unexpected_errors_as_json(request: Request, call_next):
    """Answer an unhandled error with a JSON 500 from inside the CORS layer.

    Starlette's own 500 page is sent from outside CORSMiddleware, without the
    Access-Control-Allow-Origin header, so a browser reports it as a network
    failure ("Could not reach the API") and the frontend never sees the status.
    """
    try:
        return await call_next(request)
    except Exception:
        logging.getLogger("app").exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse({"detail": "Something went wrong on the server. Please try again."}, status_code=500)


# Added after the error middleware, so CORS wraps it and headers reach 500s too.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)
for router in (core_router, courses_router, questions_router, exams_router, ingest_router, users_router):
    app.include_router(router)
