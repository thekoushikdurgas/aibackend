# Database Migration Notes

This backend supports both SQLite and PostgreSQL.

## Runtime database selection

- `database_url` is the default.
- In production, `postgresql_url` is preferred when:
  - `environment=production`
  - `database_prefer_postgresql_in_production=true`
  - `postgresql_url` is set

The final runtime URL is exposed through `settings.effective_database_url`.

## Recommended production setup

1. Set `ENVIRONMENT=production`
2. Set `POSTGRESQL_URL=postgresql+asyncpg://...`
3. Keep `DATABASE_URL` as local fallback only
4. Run schema migrations before startup

## SQLite to PostgreSQL switch checklist

1. Export data from SQLite (`data/durgasai.db`)
2. Create PostgreSQL database
3. Apply schema in PostgreSQL
4. Migrate data (conversation, metrics, and related entities)
5. Set `POSTGRESQL_URL` (and related pool settings) in **`.env`** or your process environment
6. Restart backend and verify `system.health`
