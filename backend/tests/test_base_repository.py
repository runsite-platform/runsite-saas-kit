import uuid

from fastapi_pagination import Params, set_params
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.repository import SQLAlchemyRepository


class RepositoryTestBase(DeclarativeBase):
    pass


class Gadget(RepositoryTestBase, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "repository_test_gadgets"

    name: Mapped[str] = mapped_column(String(64))


class GadgetRepository(SQLAlchemyRepository[Gadget]):
    model = Gadget


async def create_gadget_table(db: AsyncSession) -> None:
    connection = await db.connection()
    await connection.run_sync(RepositoryTestBase.metadata.create_all)


async def test_add_get_and_delete_round_trip(db_session: AsyncSession) -> None:
    await create_gadget_table(db_session)
    repository = GadgetRepository(db_session)

    gadget = await repository.add(Gadget(name="Widget"))
    assert isinstance(gadget.id, uuid.UUID)

    loaded_gadget = await repository.get_by_id(id=gadget.id)
    assert loaded_gadget is gadget
    assert loaded_gadget.created_at is not None

    await repository.delete(gadget)
    db_session.expunge_all()
    assert await repository.get_by_id(id=gadget.id) is None


async def test_get_unknown_id_returns_none(db_session: AsyncSession) -> None:
    await create_gadget_table(db_session)
    assert await GadgetRepository(db_session).get_by_id(id=uuid.uuid4()) is None


async def test_crud_with_filters_and_ordering(db_session: AsyncSession) -> None:
    await create_gadget_table(db_session)
    repository = GadgetRepository(db_session)
    await repository.bulk_create(values=[{"name": "Alpha"}, {"name": "Beta"}, {"name": "Gamma"}])

    assert await repository.count_all() == 3
    assert await repository.exists(filter_params={"name": "Beta"})
    assert not await repository.exists(filter_params={"name": "Omega"})

    selected = await repository.get_all(
        filter_params={"name": ("in", ["Alpha", "Gamma"])}, order_params={"name": "desc"}
    )
    assert [gadget.name for gadget in selected] == ["Gamma", "Alpha"]

    names = await repository.get_all("name", filter_params={"or": [{"name": "Alpha"}, {"name": "Beta"}]})
    assert sorted(row["name"] for row in names) == ["Alpha", "Beta"]

    with set_params(Params(page=2, size=2)):
        second_page = await repository.get_all(order_params={"name": "asc"}, pagination=True)
    assert second_page.total == 3
    assert [gadget.name for gadget in second_page.items] == ["Gamma"]

    created = await repository.create(values={"name": "Delta"})
    updated = await repository.update_by_id(id=created.id, values={"name": "Epsilon"})
    assert updated is not None and updated.name == "Epsilon"

    deleted = await repository.delete_all(filter_params={"name": ("like", "%a")})
    assert sorted(gadget.name for gadget in deleted) == ["Alpha", "Beta", "Gamma"]
    assert await repository.delete_by_id(id=created.id) is not None
    assert await repository.count_all() == 0
