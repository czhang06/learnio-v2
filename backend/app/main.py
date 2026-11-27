import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .core.router import router as core_router
from .courses.router import router as courses_router
from .exams.router import router as exams_router
from .ingest import worker
from .ingest.router import router as ingest_router
from .questions.router import router as questions_router


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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)
for router in (core_router, courses_router, questions_router, exams_router, ingest_router):
    app.include_router(router)
