# app/db/base.py
#
# SQLAlchemy setup. Three things happen here:
# 1. engine — the actual DB connection using DATABASE_URL
# 2. SessionLocal — a factory that creates DB sessions
# 3. Base — all ORM models inherit from this, linking them to the engine
#
# The get_db() dependency is injected into every endpoint that needs DB access.
# FastAPI calls it before the endpoint runs and closes the session after.

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# pool_pre_ping=True checks connection health before using it from the pool
# Prevents "server closed the connection unexpectedly" errors
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    FastAPI dependency for DB sessions.
    Usage in endpoints: db: Session = Depends(get_db)
    
    The try/finally ensures the session is ALWAYS closed,
    even if an exception occurs inside the endpoint.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
