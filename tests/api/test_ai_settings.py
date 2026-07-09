import json

from apps.api.app.config import Settings
from apps.api.app.schemas.settings import (
    AIModelProviderUpdate,
    AIOrganizerSettingsUpdate,
    DeepSeekProviderUpdate,
)
from apps.api.app.services.ai_settings import (
    get_ai_organizer_settings,
    load_effective_settings,
    save_ai_organizer_settings,
)


def test_save_ai_organizer_settings_persists_deepseek(tmp_path) -> None:
    base = Settings(_env_file=None, storage_root=str(tmp_path), organizer_provider="local")

    response = save_ai_organizer_settings(
        AIOrganizerSettingsUpdate(
            organizer_provider="deepseek",
            minimax=AIModelProviderUpdate(),
            deepseek=DeepSeekProviderUpdate(
                api_key="deepseek-key",
                base_url="https://api.deepseek.com",
                model="deepseek-v4-flash",
                max_tokens=4096,
                thinking_enabled=False,
            ),
        ),
        base,
    )

    settings_file = tmp_path / "ai-organizer-settings.json"
    assert response.organizer_provider == "deepseek"
    assert response.providers.deepseek.api_key_configured is True
    saved_settings = json.loads(settings_file.read_text(encoding="utf-8"))
    assert saved_settings["deepseek_api_key"] == "deepseek-key"

    effective = load_effective_settings(base)
    assert effective.organizer_provider == "deepseek"
    assert effective.deepseek_api_key == "deepseek-key"
    assert effective.deepseek_model == "deepseek-v4-flash"


def test_ai_organizer_settings_response_does_not_expose_keys(tmp_path) -> None:
    base = Settings(
        _env_file=None,
        storage_root=str(tmp_path),
        organizer_provider="minimax",
        minimax_api_key="secret",
    )

    response = get_ai_organizer_settings(base)
    dumped = response.model_dump()

    assert response.providers.minimax.api_key_configured is True
    assert "secret" not in str(dumped)
