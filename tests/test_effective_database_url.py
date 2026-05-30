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


def test_compose_only_env_vars_do_not_fail_settings(monkeypatch):
    """Docker Compose port/UI vars in .env must not trip extra=forbid on Settings."""
    monkeypatch.setenv("KAFKA_EXTERNAL_PORT", "9092")
    monkeypatch.setenv("KAFKA_UI_PORT", "8080")
    monkeypatch.setenv("MINIO_API_PORT", "9000")
    monkeypatch.setenv("GRAFANA_USER", "admin")
    monkeypatch.setenv("PGADMIN_EMAIL", "admin@durgasos.local")
    clear_base_settings_cache()
    settings = Settings()
    assert settings.kafka_external_port == 9092
    assert settings.kafka_ui_port == 8080
    assert settings.minio_api_port == 9000
    assert settings.grafana_user == "admin"
    assert settings.pgadmin_email == "admin@durgasos.local"


def test_postgresql_preferred_when_database_url_is_not_sqlite(monkeypatch):
    pg = "postgresql+asyncpg://user:pass@db.example.com:5432/app"
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", pg)
    monkeypatch.setenv("POSTGRESQL_URL", pg)
    clear_base_settings_cache()
    settings = Settings()
    assert settings.effective_database_url == pg
