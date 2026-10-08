"""
Shared GraphQL arguments.

Strawberry ignores docstrings, so the GraphiQL docs only show what is passed as
`description`. Reusing these keeps the common arguments documented the same way everywhere.
"""

from typing import Annotated, Optional
import strawberry

from app.graphql.context import MAX_LIMIT

Limit = Annotated[int, strawberry.argument(
    description=f"Maximum number of results (at most {MAX_LIMIT})."
)]
Offset = Annotated[int, strawberry.argument(
    description="Number of results to skip, for paging through long lists."
)]
UserId = Annotated[Optional[str], strawberry.argument(
    description="Only include data of this Discord user ID."
)]
ChannelId = Annotated[Optional[str], strawberry.argument(
    description="Only include data of this Discord channel ID."
)]
Days = Annotated[Optional[int], strawberry.argument(
    description="Only include the last N days. Ignored when startDate is set."
)]
StartDate = Annotated[Optional[str], strawberry.argument(
    description='Only include data from this day on (UTC), e.g. "2026-01-31".'
)]
EndDate = Annotated[Optional[str], strawberry.argument(
    description='Only include data up to and including this day (UTC), e.g. "2026-01-31".'
)]
