from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  # ensure models register with SQLAlchemy metadata
from app.api.routes import router
from app.core.config import settings
from app.db.session import Base, engine

app = FastAPI(title=settings.project_name, version=settings.version)

# Create tables that might be missing (no migrations yet for SQLite workflow).
Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
