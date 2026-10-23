from collections.abc import Callable, Sequence
from typing import Any, Generic, TypeVar
from uuid import UUID

from fastapi_filter.contrib.sqlalchemy import Filter
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import (
    ColumnElement,
    Delete,
    Select,
    Update,
    and_,
    asc,
    delete,
    desc,
    exists,
    func,
    insert,
    or_,
    select,
    update,
)
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

ModelT = TypeVar("ModelT", bound=DeclarativeBase)

FilterParams = dict[str, Any]
OrderParams = dict[str, str]

FILTER_OPERATORS: dict[str, Callable[[Any, Any], ColumnElement[bool]]] = {
    "eq": lambda column, operand: column == operand,
    "!eq": lambda column, operand: column != operand,
    "gt": lambda column, operand: column > operand,
    "ge": lambda column, operand: column >= operand,
    "lt": lambda column, operand: column < operand,
    "le": lambda column, operand: column <= operand,
    "in": lambda column, operand: column.in_(operand),
    "!in": lambda column, operand: ~column.in_(operand),
    "like": lambda column, operand: column.like(operand),
    "!like": lambda column, operand: ~column.like(operand),
    "between": lambda column, operand: column.between(operand[0], operand[1]),
    "!between": lambda column, operand: ~column.between(operand[0], operand[1]),
    "null": lambda column, _operand: column.is_(None),
    "!null": lambda column, _operand: column.is_not(None),
}


class SQLAlchemyRepository(Generic[ModelT]):
    """
    Base CRUD repository.

    Filter values are either a plain value (equality) or a tuple of an operator and its operands,
    e.g. ("ge", 10), ("in", [1, 2]), ("between", low, high), ("null",).
    The keys "and" / "or" take a list of nested filter dicts or SQL expressions.
    """

    model: type[ModelT]

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _get_column(self, field: str) -> Any:
        column = getattr(self.model, field, None)
        if column is None:
            raise ValueError(f"Model '{self.model.__name__}' has no field '{field}'")
        return column

    def _build_single_clause(self, field: str, value: Any) -> ColumnElement[bool]:
        if isinstance(value, tuple):
            operator, *operands = value
        else:
            operator, operands = "eq", [value]
        build_clause = FILTER_OPERATORS.get(operator.lower())
        if build_clause is None:
            raise ValueError(f"Unknown filter operator: {operator}")
        operand = operands[0] if len(operands) == 1 else operands
        return build_clause(self._get_column(field), operand)

    def _build_filter_group(self, filter_params: FilterParams) -> list[ColumnElement[bool]]:
        clauses: list[ColumnElement[bool]] = []
        for key, value in filter_params.items():
            group_operator = key.lower()
            if group_operator in ("and", "or"):
                if not isinstance(value, list):
                    raise ValueError(f"Expected a list for '{key}', got {type(value).__name__}")
                if not value:
                    continue
                nested_clauses = [
                    and_(*self._build_filter_group(item)) if isinstance(item, dict) else item for item in value
                ]
                clauses.append(or_(*nested_clauses) if group_operator == "or" else and_(*nested_clauses))
            else:
                clauses.append(self._build_single_clause(key, value))
        return clauses

    def _build_order_clause(self, order_params: OrderParams) -> list[Any]:
        order_clause = []
        for field, direction in order_params.items():
            column = self._get_column(field)
            is_descending = direction.lower() == "desc" or direction == "-"
            order_clause.append(desc(column) if is_descending else asc(column))
        return order_clause

    def _init_query(
        self,
        *fields: str,
        filter_params: FilterParams | None = None,
        order_params: OrderParams | None = None,
        operation: Select | Update | Delete | None = None,
    ) -> Any:
        columns = [self._get_column(field) for field in fields]
        query: Any = operation if operation is not None else select(*columns) if columns else select(self.model)
        where_clauses = self._build_filter_group(filter_params or {})
        if where_clauses:
            query = query.where(*where_clauses)
        order_clause = self._build_order_clause(order_params or {})
        if order_clause:
            query = query.order_by(*order_clause)
        return query

    async def count_all(self, *, filter_params: FilterParams | None = None) -> int:
        operation = select(func.count()).select_from(self.model)
        query = self._init_query(filter_params=filter_params, operation=operation)
        return int(await self.db.scalar(query) or 0)

    async def exists(self, *, filter_params: FilterParams | None = None) -> bool:
        where_clauses = self._build_filter_group(filter_params or {})
        return bool(await self.db.scalar(select(exists().select_from(self.model).where(*where_clauses))))

    async def get_one(
        self,
        *fields: str,
        filter_params: FilterParams | None = None,
        order_params: OrderParams | None = None,
    ) -> ModelT | RowMapping | None:
        query = self._init_query(*fields, filter_params=filter_params, order_params=order_params).limit(1)
        result = await self.db.execute(query)
        if fields:
            return result.mappings().one_or_none()
        return result.scalars().one_or_none()

    async def get_by_id(self, *fields: str, id: UUID) -> ModelT | RowMapping | None:  # noqa: A002
        return await self.get_one(*fields, filter_params={"id": id})

    async def get_all(
        self,
        *fields: str,
        filter_params: FilterParams | None = None,
        order_params: OrderParams | None = None,
        pagination: bool = False,
        extra_filter: Filter | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> Sequence[ModelT] | Sequence[RowMapping] | Page:
        query = self._init_query(*fields, filter_params=filter_params, order_params=order_params)
        if extra_filter is not None:
            query = extra_filter.filter(query)
            query = extra_filter.sort(query)
        if pagination:
            return await apaginate(self.db, query, additional_data=additional_data)
        result = await self.db.execute(query)
        if fields:
            return result.mappings().all()
        return result.scalars().all()

    async def add(self, entity: ModelT) -> ModelT:
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def create(self, *, values: dict[str, Any]) -> ModelT:
        query = insert(self.model).values(**values).returning(self.model)
        result = await self.db.execute(query.execution_options(populate_existing=True))
        return result.scalars().one()

    async def bulk_create(self, *, values: list[dict[str, Any]]) -> Sequence[ModelT]:
        query = insert(self.model).values(values).returning(self.model)
        result = await self.db.execute(query.execution_options(populate_existing=True))
        return result.scalars().all()

    async def update_all(
        self, *, values: dict[str, Any], filter_params: FilterParams | None = None
    ) -> Sequence[ModelT]:
        operation = update(self.model).values(**values).returning(self.model)
        query = self._init_query(filter_params=filter_params, operation=operation)
        result = await self.db.execute(query.execution_options(populate_existing=True))
        return result.scalars().all()

    async def update_by_id(self, *, id: UUID, values: dict[str, Any]) -> ModelT | None:  # noqa: A002
        updated_rows = await self.update_all(values=values, filter_params={"id": id})
        return updated_rows[0] if updated_rows else None

    async def delete(self, entity: ModelT) -> None:
        await self.db.delete(entity)
        await self.db.flush()

    async def delete_all(self, *, filter_params: FilterParams | None = None) -> Sequence[ModelT]:
        operation = delete(self.model).returning(self.model)
        query = self._init_query(filter_params=filter_params, operation=operation)
        result = await self.db.execute(query.execution_options(populate_existing=True))
        return result.scalars().all()

    async def delete_by_id(self, *, id: UUID) -> ModelT | None:  # noqa: A002
        deleted_rows = await self.delete_all(filter_params={"id": id})
        return deleted_rows[0] if deleted_rows else None
