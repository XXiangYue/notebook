from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.database import get_session
from apps.api.app.schemas.knowledge import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
)
from apps.api.app.services.knowledge import (
    CategoryNameConflictError,
    CategoryNotFoundError,
    SystemCategoryProtectedError,
    create_category,
    delete_category,
    list_categories,
    update_category,
)

router = APIRouter(prefix="/categories", tags=["categories"])
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=list[CategoryResponse])
async def get_categories(session: SessionDependency) -> list[CategoryResponse]:
    categories = await list_categories(session)
    return [CategoryResponse.model_validate(category) for category in categories]


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def post_category(
    payload: CategoryCreate,
    session: SessionDependency,
) -> CategoryResponse:
    try:
        category = await create_category(session, payload)
    except CategoryNameConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category name already exists",
        ) from error
    return CategoryResponse.model_validate(category)


@router.patch("/{category_id}", response_model=CategoryResponse)
async def patch_category(
    category_id: UUID,
    payload: CategoryUpdate,
    session: SessionDependency,
) -> CategoryResponse:
    try:
        category = await update_category(session, category_id, payload)
    except CategoryNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        ) from error
    except SystemCategoryProtectedError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System categories cannot be modified",
        ) from error
    except CategoryNameConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category name already exists",
        ) from error
    return CategoryResponse.model_validate(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category_route(
    category_id: UUID,
    session: SessionDependency,
) -> None:
    try:
        await delete_category(session, category_id)
    except CategoryNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        ) from error
    except SystemCategoryProtectedError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System categories cannot be deleted",
        ) from error
