from app.core.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.database_url, echo=False, future=True, connect_args=connect_args
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    """Provide a SQLAlchemy session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
