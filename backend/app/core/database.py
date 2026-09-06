from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Convert sync URL to async — handle various postgres URL formats
_url = settings.DATABASE_URL
if _url.startswith("postgresql://"):
    _url = _url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif _url.startswith("postgres://"):
    _url = _url.replace("postgresql://", "postgresql+asyncpg://", 1)

# PgBouncer compatibility: OrthoFlow connects to Postgres through PgBouncer, which runs in
# transaction pooling mode. asyncpg's default server-side prepared statements are NOT
# compatible with transaction pooling (they cause ProtocolViolationError / "prepared
# statement does not exist" across pooled connections). The correct, documented fix is to
# disable prepared-statement caching on the asyncpg driver so every statement is sent
# inline. This applies uniformly to the app, seed scripts, and one-off tasks.
_is_pgbouncer = "pgbouncer" in _url or settings.DB_VIA_PGBOUNCER
_connect_args: dict = {}
if _url.startswith("postgresql+asyncpg://") and _is_pgbouncer:
    _connect_args = {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }

engine = create_async_engine(
    _url,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600,
    connect_args=_connect_args,
)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with SessionLocal() as session:
        yield session
