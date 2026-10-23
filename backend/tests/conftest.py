import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from typing import Any

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://saaskit:saaskit@localhost:5432/saaskit_test"
)

# DATABASE_URL is forced (not setdefault) so an app built from get_settings() can never reach a non-test database.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("JWT_SECRET", "test-secret-" + "x" * 48)
os.environ.setdefault("APP_URL", "http://testserver")

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

import app.models  # noqa: E402, F401
from app.config.db import Base, get_db_session  # noqa: E402
from app.config.settings import Settings, get_settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.utils import security  # noqa: E402
from app.utils.dependencies import get_email_sender, get_object_storage  # noqa: E402
from app.utils.rate_limit import auth_rate_limiter  # noqa: E402
from tests.fakes import InMemoryEmailSender, InMemoryObjectStorage  # noqa: E402

TEST_SETTINGS_DEFAULTS: dict[str, Any] = {
    "DATABASE_URL": TEST_DATABASE_URL,
    "JWT_SECRET": "test-secret-" + "x" * 48,
    "APP_URL": "http://testserver",
    "EMAIL_API_KEY": "",
    "S3_BUCKET": "",
    "BILLING_PROVIDER": "",
    "GOOGLE_CLIENT_ID": "",
    "SUPERADMIN_EMAIL": "",
}

# Every optional field is passed explicitly so exported shell variables (DEBUG, S3_*, ...) never leak into tests.
SETTINGS_FIELD_DEFAULTS: dict[str, Any] = {
    field_name: field_info.get_default(call_default_factory=True)
    for field_name, field_info in Settings.model_fields.items()
    if not field_info.is_required()
}


def make_settings(**overrides: Any) -> Settings:
    return Settings(_env_file=None, **{**SETTINGS_FIELD_DEFAULTS, **TEST_SETTINGS_DEFAULTS, **overrides})


async def _recreate_schema() -> None:
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
    finally:
        await engine.dispose()


async def _drop_schema() -> None:
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
    finally:
        await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def database_schema() -> Iterator[None]:
    asyncio.run(_recreate_schema())
    yield
    asyncio.run(_drop_schema())


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
        await engine.dispose()


@pytest.fixture
def app(settings: Settings, db_session: AsyncSession) -> FastAPI:
    application = create_app(settings)

    async def override_db_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    application.dependency_overrides[get_db_session] = override_db_session
    application.dependency_overrides[get_settings] = lambda: settings
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def fast_password_hashing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security, "BCRYPT_ROUNDS", 4)


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> Iterator[None]:
    auth_rate_limiter.reset()
    yield
    auth_rate_limiter.reset()


@pytest.fixture
def email_outbox(app: FastAPI) -> InMemoryEmailSender:
    sender = InMemoryEmailSender()
    app.dependency_overrides[get_email_sender] = lambda: sender
    return sender


@pytest.fixture
def object_storage(app: FastAPI) -> InMemoryObjectStorage:
    storage = InMemoryObjectStorage()
    app.dependency_overrides[get_object_storage] = lambda: storage
    return storage
