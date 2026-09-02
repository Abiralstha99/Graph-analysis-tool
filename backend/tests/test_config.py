from backend.config import Settings


def test_from_environment_reads_gemini_api_key(monkeypatch):
    """A changed GEMINI_API_KEY must be reflected in newly loaded settings."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

    settings = Settings.from_environment()

    assert settings.gemini_api_key == "test-gemini-key"
