from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.database import get_session
from apps.api.app.schemas.search import SearchRequest, SearchResponse
from apps.api.app.services.search import search_chunks

router = APIRouter(prefix="/search", tags=["search"])
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.post("", response_model=SearchResponse)
async def search_knowledge(
    payload: SearchRequest,
    session: SessionDependency,
) -> SearchResponse:
    items, total = await search_chunks(session, payload)
    return SearchResponse(
        query=payload.query,
        total=total,
        limit=payload.limit,
        items=items,
    )
