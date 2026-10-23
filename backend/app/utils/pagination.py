from typing import Annotated

from fastapi import Query

SearchQuery = Annotated[str | None, Query(max_length=200)]
