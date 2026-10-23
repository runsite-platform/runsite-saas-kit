from collections.abc import AsyncIterator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "all_column_names": lambda constraint, _table: "_".join(column.name for column in constraint.columns.values()),
    "ix": "ix__%(table_name)s__%(all_column_names)s",
    "uq": "uq__%(table_name)s__%(all_column_names)s",
    "ck": "ck__%(table_name)s__%(constraint_name)s",
    "fk": "fk__%(table_name)s__%(all_column_names)s__%(referred_table_name)s",
    "pk": "pk__%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class DatabaseManager:
    engine: AsyncEngine | None = None
    session_maker: async_sessionmaker[AsyncSession] | None = None

    @classmethod
    def setup(cls, database_url: str, *, echo: bool = False) -> None:
        cls.engine = create_async_engine(
            database_url,
            echo=echo,
            pool_pre_ping=True,
            connect_args={"server_settings": {"timezone": "UTC"}},
        )
        cls.session_maker = async_sessionmaker(bind=cls.engine, class_=AsyncSession, expire_on_commit=False)

    @classmethod
    async def stop(cls) -> None:
        if cls.engine is not None:
            await cls.engine.dispose()
        cls.engine = None
        cls.session_maker = None


async def get_db_session() -> AsyncIterator[AsyncSession]:
    if DatabaseManager.session_maker is None:
        raise RuntimeError("Database is not initialized. Call DatabaseManager.setup() first.")
    session = DatabaseManager.session_maker()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
