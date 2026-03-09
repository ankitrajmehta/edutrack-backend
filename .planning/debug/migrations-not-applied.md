---
status: diagnosed
trigger: "POST /api/v1/auth/register returns 500 — UndefinedTableError: relation \"users\" does not exist"
created: 2026-03-09T13:30:00Z
updated: 2026-03-09T13:35:00Z
---

## Current Focus

hypothesis: Migration file 0001_initial_schema.py is a placeholder stub with no actual op.create_table() calls — upgrade() is a no-op (just `pass`)
test: Read alembic/versions/0001_initial_schema.py upgrade() body
expecting: If confirmed, running `alembic upgrade head` would stamp the DB as migrated but create zero tables
next_action: DIAGNOSED — root cause confirmed

## Symptoms

expected: POST /api/v1/auth/register hits the database and returns 201 with a token. The `users` table must exist in PostgreSQL.
actual: 500 Internal Server Error — asyncpg.exceptions.UndefinedTableError: relation "users" does not exist
errors: |
  asyncpg.exceptions.UndefinedTableError: relation "users" does not exist
  [SQL: SELECT users.id ... FROM users WHERE users.email = $1::VARCHAR]
reproduction: POST /api/auth/register (UAT Test 5)
started: Discovered during UAT of Phase 01-foundation

## Eliminated

- hypothesis: Wrong DATABASE_URL in alembic.ini causing migrations to target the wrong DB
  evidence: alembic.ini has `sqlalchemy.url = postgresql+asyncpg://edutrack:edutrack@localhost:5432/edutrack` which matches app/core/config.py DEFAULT (DATABASE_URL = same string). env.py overrides alembic.ini's url with settings.DATABASE_URL at runtime, so they're consistent.
  timestamp: 2026-03-09T13:33:00Z

- hypothesis: Async migration pattern in env.py is broken (wrong async setup)
  evidence: env.py correctly uses async_engine_from_config + connection.run_sync(do_run_migrations). Pattern is valid for asyncpg. No issue here.
  timestamp: 2026-03-09T13:33:00Z

- hypothesis: App runs migrations automatically on startup
  evidence: app/main.py has NO lifespan event, no startup handler, no call to alembic or create_all. Migrations are 100% manual.
  timestamp: 2026-03-09T13:34:00Z

## Evidence

- timestamp: 2026-03-09T13:31:00Z
  checked: alembic/versions/0001_initial_schema.py — upgrade() function body
  found: |
    upgrade() contains only `pass`. The docstring says:
    "This migration was created without a live database connection.
    After starting the database, run: alembic revision --autogenerate -m 'initial_schema'
    to regenerate with proper table definitions."
    There are NO op.create_table() calls whatsoever.
    downgrade() is also just `pass`.
  implication: Running `alembic upgrade head` would mark revision "0001" as applied in alembic_version table but create ZERO tables. The database remains empty.

- timestamp: 2026-03-09T13:32:00Z
  checked: alembic/env.py — full file
  found: Correctly structured async migration pattern. Imports settings and Base.metadata. Uses async_engine_from_config. The URL is overridden with settings.DATABASE_URL at runtime (line 19). Pattern is sound.
  implication: env.py is not the problem.

- timestamp: 2026-03-09T13:32:00Z
  checked: alembic.ini — sqlalchemy.url
  found: `sqlalchemy.url = postgresql+asyncpg://edutrack:edutrack@localhost:5432/edutrack` (line 89). This is a hardcoded fallback; env.py overrides it with settings.DATABASE_URL which defaults to the same value. In Docker, DATABASE_URL env var would override via .env / environment block.
  implication: URL configuration is consistent and not the root cause.

- timestamp: 2026-03-09T13:33:00Z
  checked: app/main.py — startup lifecycle, lifespan events
  found: No @app.on_event("startup"), no lifespan context manager, no call to Base.metadata.create_all(), no alembic runner. The app never triggers migrations automatically.
  implication: Migrations MUST be run manually (`alembic upgrade head`) before the app can use the database. They were never run.

- timestamp: 2026-03-09T13:34:00Z
  checked: app/core/config.py
  found: DATABASE_URL default matches alembic.ini. No issues with config.
  implication: Not a contributing factor.

## Resolution

root_cause: |
  The migration file `alembic/versions/0001_initial_schema.py` is a placeholder stub.
  Its upgrade() function contains only `pass` — there are ZERO op.create_table() calls.
  The file's own docstring admits this explicitly:
    "This migration was created without a live database connection.
     After starting the database, run: alembic revision --autogenerate -m 'initial_schema'
     to regenerate with proper table definitions."
  
  Additionally, app/main.py has no startup lifecycle hook to run migrations automatically.
  
  Combined effect: Even if `alembic upgrade head` were run, it would create no tables.
  The users table (and all 11 other tables) simply do not exist in the database.

fix: NOT APPLIED (diagnose-only mode)
verification: NOT APPLIED
files_changed: []

## Suggested Fix Direction

1. PRIMARY FIX — Write the real migration: Replace the `pass` in upgrade() with actual
   op.create_table() calls for all 12 tables (users, refresh_tokens, ngos, programs,
   students, donors, donations, invoices, schools, scholarship_applications,
   activity_logs, file_records). OR run `alembic revision --autogenerate -m "initial_schema"`
   against a live (but empty) DB to auto-generate from SQLAlchemy models, then delete the
   placeholder 0001 file (or fold the generated content into it).

2. THEN run `alembic upgrade head` to apply the migration.

3. OPTIONAL — Add a startup lifespan hook in app/main.py to auto-run migrations,
   or document the manual step clearly in docker-compose / README.
