"""Tests for runtime database URL selection."""

from __future__ import annotations

from app.config import Settings, clear_base_settings_cache


def test_sqlite_database_url_wins_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./data/durgasai.db")
    monkeypatch.setenv(
        "POSTGRESQL_URL",
        "postgresql+asyncpg://user:pass@54.146.221.133:5432/postgres",
    )
    clear_base_settings_cache()
    settings = Settings()
    assert "sqlite" in settings.effective_database_url.lower()


def test_postgresql_preferred_when_database_url_is_not_sqlite(monkeypatch):
    pg = "postgresql+asyncpg://user:pass@db.example.com:5432/app"
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", pg)
    monkeypatch.setenv("POSTGRESQL_URL", pg)
    clear_base_settings_cache()
    settings = Settings()
    assert settings.effective_database_url == pg
