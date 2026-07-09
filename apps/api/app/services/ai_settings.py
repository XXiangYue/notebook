import json
import os
from pathlib import Path
from typing import Any

from apps.api.app.config import Settings
from apps.api.app.schemas.settings import (
    AIModelProviderResponse,
    AIOrganizerProviderResponses,
    AIOrganizerSettingsResponse,
    AIOrganizerSettingsUpdate,
    DeepSeekProviderResponse,
    LocalProviderResponse,
)

ORGANIZER_PROVIDERS = {"local", "minimax", "deepseek"}
ORGANIZER_SETTING_FIELDS = {
    "organizer_provider",
    "minimax_api_key",
    "minimax_base_url",
    "minimax_model",
    "minimax_max_tokens",
    "deepseek_api_key",
    "deepseek_base_url",
    "deepseek_model",
    "deepseek_max_tokens",
    "deepseek_timeout_seconds",
    "deepseek_thinking_enabled",
}


class AIOrganizerSettingsError(ValueError):
    pass


def load_effective_settings(base: Settings | None = None) -> Settings:
    settings = base or Settings()
    overrides = _read_runtime_overrides(settings)
    if not overrides:
        return settings
    return settings.model_copy(update=overrides)


def get_ai_organizer_settings(
    base: Settings | None = None,
) -> AIOrganizerSettingsResponse:
    settings = load_effective_settings(base)
    return _settings_response(settings)


def save_ai_organizer_settings(
    payload: AIOrganizerSettingsUpdate,
    base: Settings | None = None,
) -> AIOrganizerSettingsResponse:
    base_settings = base or Settings()
    current = load_effective_settings(base_settings)
    values = {
        "organizer_provider": payload.organizer_provider,
        "minimax_api_key": payload.minimax.api_key or current.minimax_api_key,
        "minimax_base_url": payload.minimax.base_url or current.minimax_base_url,
        "minimax_model": payload.minimax.model or current.minimax_model,
        "minimax_max_tokens": payload.minimax.max_tokens
        if payload.minimax.max_tokens is not None
        else current.minimax_max_tokens,
        "deepseek_api_key": payload.deepseek.api_key or current.deepseek_api_key,
        "deepseek_base_url": payload.deepseek.base_url or current.deepseek_base_url,
        "deepseek_model": payload.deepseek.model or current.deepseek_model,
        "deepseek_max_tokens": payload.deepseek.max_tokens
        if payload.deepseek.max_tokens is not None
        else current.deepseek_max_tokens,
        "deepseek_timeout_seconds": current.deepseek_timeout_seconds,
        "deepseek_thinking_enabled": payload.deepseek.thinking_enabled
        if payload.deepseek.thinking_enabled is not None
        else current.deepseek_thinking_enabled,
    }

    _validate_settings(values)
    _write_runtime_overrides(base_settings, values)
    return _settings_response(base_settings.model_copy(update=values))


def _runtime_settings_path(settings: Settings) -> Path:
    if settings.ai_organizer_settings_path:
        return Path(settings.ai_organizer_settings_path).expanduser()
    return Path(settings.storage_root).expanduser() / "ai-organizer-settings.json"


def _read_runtime_overrides(settings: Settings) -> dict[str, Any]:
    path = _runtime_settings_path(settings)
    if not path.exists():
        return {}

    try:
        raw_data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AIOrganizerSettingsError(
            f"Unable to read AI organizer settings: {error}"
        ) from error

    if not isinstance(raw_data, dict):
        raise AIOrganizerSettingsError("AI organizer settings file must contain a JSON object")

    overrides = {
        key: value
        for key, value in raw_data.items()
        if key in ORGANIZER_SETTING_FIELDS and value is not None
    }
    _validate_settings(overrides, require_keys=False)
    return overrides


def _write_runtime_overrides(settings: Settings, values: dict[str, Any]) -> None:
    path = _runtime_settings_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    data = {key: values[key] for key in sorted(ORGANIZER_SETTING_FIELDS) if key in values}

    try:
        temp_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.chmod(temp_path, 0o600)
        temp_path.replace(path)
    except OSError as error:
        raise AIOrganizerSettingsError(
            f"Unable to save AI organizer settings: {error}"
        ) from error


def _validate_settings(values: dict[str, Any], require_keys: bool = True) -> None:
    provider = values.get("organizer_provider")
    if provider is not None and provider not in ORGANIZER_PROVIDERS:
        raise AIOrganizerSettingsError(f"Unsupported organizer provider: {provider}")

    if require_keys and provider == "minimax" and not values.get("minimax_api_key"):
        raise AIOrganizerSettingsError("MINIMAX_API_KEY is required for MiniMax")
    if require_keys and provider == "deepseek" and not values.get("deepseek_api_key"):
        raise AIOrganizerSettingsError("DEEPSEEK_API_KEY is required for DeepSeek")


def _settings_response(settings: Settings) -> AIOrganizerSettingsResponse:
    provider = settings.organizer_provider
    if provider not in ORGANIZER_PROVIDERS:
        provider = "local"

    return AIOrganizerSettingsResponse(
        organizer_provider=provider,
        providers=AIOrganizerProviderResponses(
            local=LocalProviderResponse(
                label="Local",
                description="离线 deterministic 整理适配器，用于开发和无密钥场景。",
            ),
            minimax=AIModelProviderResponse(
                label="MiniMax",
                base_url=settings.minimax_base_url,
                model=settings.minimax_model,
                max_tokens=settings.minimax_max_tokens,
                api_key_configured=bool(settings.minimax_api_key),
            ),
            deepseek=DeepSeekProviderResponse(
                label="DeepSeek V4 Flash",
                base_url=settings.deepseek_base_url,
                model=settings.deepseek_model,
                max_tokens=settings.deepseek_max_tokens,
                api_key_configured=bool(settings.deepseek_api_key),
                thinking_enabled=settings.deepseek_thinking_enabled,
            ),
        ),
    )
