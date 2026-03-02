from __future__ import annotations

from bt_common.config import get_emos_fallback_settings, get_settings


def test_settings_and_fallback_round_trip(monkeypatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://supabase.local")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role")
    monkeypatch.setenv("EMOS_BASE_URL", "https://emos.local")
    monkeypatch.setenv("EMOS_API_KEY", "emos-key")
    monkeypatch.setenv("MATRIX_HOMESERVER_URL", "https://matrix.local")
    monkeypatch.setenv("MATRIX_AS_TOKEN", "as-token")
    monkeypatch.setenv("MATRIX_HS_TOKEN", "hs-token")

    get_settings.cache_clear()
    get_emos_fallback_settings.cache_clear()

    settings = get_settings()
    fallback = get_emos_fallback_settings()

    assert settings.EMOS_BASE_URL == "https://emos.local"
    assert fallback.EMOS_BASE_URL == "https://emos.local"
    assert fallback.EMOS_API_KEY == "emos-key"
