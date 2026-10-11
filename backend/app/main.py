from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routes import router

app = FastAPI(title="LearnIO", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
