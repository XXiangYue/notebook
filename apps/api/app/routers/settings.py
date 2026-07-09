from fastapi import APIRouter, HTTPException

from apps.api.app.schemas.settings import (
    AIOrganizerSettingsResponse,
    AIOrganizerSettingsUpdate,
)
from apps.api.app.services.ai_settings import (
    AIOrganizerSettingsError,
    get_ai_organizer_settings,
    save_ai_organizer_settings,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/ai-organizer", response_model=AIOrganizerSettingsResponse)
async def read_ai_organizer_settings() -> AIOrganizerSettingsResponse:
    try:
        return get_ai_organizer_settings()
    except AIOrganizerSettingsError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.patch("/ai-organizer", response_model=AIOrganizerSettingsResponse)
async def update_ai_organizer_settings(
    payload: AIOrganizerSettingsUpdate,
) -> AIOrganizerSettingsResponse:
    try:
        return save_ai_organizer_settings(payload)
    except AIOrganizerSettingsError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
