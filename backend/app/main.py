from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .core.router import router as core_router
from .courses.router import router as courses_router
from .exams.router import router as exams_router
from .ingest.router import router as ingest_router
from .questions.router import router as questions_router

app = FastAPI(title="LearnIO", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)
for router in (core_router, courses_router, questions_router, exams_router, ingest_router):
    app.include_router(router)
