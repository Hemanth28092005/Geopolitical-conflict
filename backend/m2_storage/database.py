from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from backend.core.config import get_settings

settings = get_settings()

# Sync engine (for migrations and scripts)
engine = create_engine(settings.database_url, echo=False)

# Async engine (for FastAPI endpoints)
async_engine = create_async_engine(settings.async_database_url, echo=False)

# Session factories
SyncSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False
)

# Base class all models inherit from
class Base(DeclarativeBase):
    pass

# Dependency for FastAPI routes
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()