from typing import Literal

from pydantic import BaseModel, Field, field_validator

OrganizerProvider = Literal["local", "minimax", "deepseek"]


class AIModelProviderResponse(BaseModel):
    label: str
    base_url: str
    model: str
    max_tokens: int
    api_key_configured: bool


class DeepSeekProviderResponse(AIModelProviderResponse):
    thinking_enabled: bool


class LocalProviderResponse(BaseModel):
    label: str
    description: str


class AIOrganizerProviderResponses(BaseModel):
    local: LocalProviderResponse
    minimax: AIModelProviderResponse
    deepseek: DeepSeekProviderResponse


class AIOrganizerSettingsResponse(BaseModel):
    organizer_provider: OrganizerProvider
    providers: AIOrganizerProviderResponses


class AIModelProviderUpdate(BaseModel):
    api_key: str | None = Field(default=None, max_length=4096)
    base_url: str | None = Field(default=None, max_length=500)
    model: str | None = Field(default=None, max_length=200)
    max_tokens: int | None = Field(default=None, ge=1, le=200_000)

    @field_validator("api_key", "base_url", "model")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class DeepSeekProviderUpdate(AIModelProviderUpdate):
    thinking_enabled: bool | None = None


class AIOrganizerSettingsUpdate(BaseModel):
    organizer_provider: OrganizerProvider
    minimax: AIModelProviderUpdate = Field(default_factory=AIModelProviderUpdate)
    deepseek: DeepSeekProviderUpdate = Field(default_factory=DeepSeekProviderUpdate)
