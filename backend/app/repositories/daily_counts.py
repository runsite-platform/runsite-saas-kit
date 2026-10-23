from collections.abc import Sequence
from datetime import date, datetime

from sqlalchemy import ColumnElement, Date, cast, func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute


async def count_rows_per_day(
    db: AsyncSession,
    created_at_column: InstrumentedAttribute[datetime],
    *,
    starts_at: datetime,
    ends_at: datetime,
    filters: Sequence[ColumnElement[bool]] = (),
) -> dict[date, int]:
    utc_day_expression = cast(func.timezone(literal_column("'UTC'"), created_at_column), Date)
    statement = (
        select(utc_day_expression, func.count())
        .where(created_at_column >= starts_at, created_at_column < ends_at, *filters)
        .group_by(utc_day_expression)
    )
    result = await db.execute(statement)
    return {row_day: row_count for row_day, row_count in result.all()}
