from backend.config import Settings


def test_from_environment_reads_gemini_api_key(monkeypatch):
    """A changed GEMINI_API_KEY must be reflected in newly loaded settings."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

    settings = Settings.from_environment()

    assert settings.gemini_api_key == "test-gemini-key"


def test_from_environment_reads_db_password_when_db_pass_is_unset(monkeypatch):
    monkeypatch.delenv("DB_PASS", raising=False)
    monkeypatch.setenv("DB_PASSWORD", "alias-password")
    monkeypatch.setenv("DB_PORT", "23429")

    settings = Settings.from_environment()

    assert settings.db_pass == "alias-password"
    assert settings.db_port == 23429


def test_from_environment_prefers_db_pass_over_db_password(monkeypatch):
    monkeypatch.setenv("DB_PASS", "primary-password")
    monkeypatch.setenv("DB_PASSWORD", "alias-password")

    settings = Settings.from_environment()

    assert settings.db_pass == "primary-password"
