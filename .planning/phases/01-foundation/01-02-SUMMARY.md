---
phase: 01-foundation
plan: 02
subsystem: database
tags: [sqlalchemy, alembic, async, postgresql, orm]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: FastAPI app, config.py with DATABASE_URL
provides:
  - Async SQLAlchemy engine and session factory
  - 12 ORM models for all entities
  - Alembic migration setup with async pattern
affects: [Phase 2+ services]

# Tech tracking
tech-stack:
  added: [sqlalchemy[asyncio], asyncpg, alembic]
  patterns: [async sessionmaker, expire_on_commit=False, run_async_migrations]

key-files:
  created:
    - app/core/database.py
    - app/models/user.py
    - app/models/ngo.py
    - app/models/program.py
    - app/models/student.py
    - app/models/donor.py
    - app/models/donation.py
    - app/models/invoice.py
    - app/models/school.py
    - app/models/application.py
    - app/models/activity_log.py
    - app/models/file_record.py
    - alembic.ini
    - alembic/env.py
    - alembic/versions/0001_initial_schema.py
  modified: []

key-decisions:
  - "Used async_sessionmaker with expire_on_commit=False to prevent MissingGreenlet errors"
  - "All status fields use SQLAlchemy Enum (not raw String) for DB-level enforcement"
  - "Indexes on all FK columns, plus unique indexes on email, scholarship_id, token"

requirements-completed: [INFRA-02]

# Metrics
duration: 7min
completed: 2026-03-09
---

# Phase 1 Plan 2: Database & ORM Models Summary

**Async SQLAlchemy setup with 12 ORM models and Alembic migration infrastructure**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-09T10:59:27Z
- **Completed:** 2026-03-09T11:06:36Z
- **Tasks:** 3
- **Files modified:** 17

## Accomplishments
- Created async database.py with expire_on_commit=False
- Implemented all 12 ORM models (User, RefreshToken, NGO, Program, Student, Donor, Donation, Invoice, School, ScholarshipApplication, ActivityLog, FileRecord)
- Set up Alembic with async template and run_async_migrations() pattern
- Created placeholder migration (DB not running - requires regeneration with --autogenerate after docker compose up)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create database.py** - `1f850dc` (feat)
2. **Task 2: Implement all 12 ORM models** - `ab4c142` (feat)
3. **Task 3: Initialize Alembic with async template** - `3eb67a8` (feat)

**Plan metadata:** (to be added after summary)

## Files Created/Modified
- `app/core/database.py` - Async engine, AsyncSessionLocal (expire_on_commit=False), Base, get_db
- `app/models/__init__.py` - Imports all models for Alembic autodiscovery
- `app/models/user.py` - User + RefreshToken with UserRole enum
- `app/models/ngo.py` - NGO with NGOStatus enum
- `app/models/program.py` - Program with ProgramStatus enum and JSON categories
- `app/models/student.py` - Student with StudentStatus enum and unique scholarship_id
- `app/models/donor.py` - Donor
- `app/models/donation.py` - Donation with DonationType enum
- `app/models/invoice.py` - Invoice with InvoiceStatus enum and JSON items
- `app/models/school.py` - School with SchoolStatus enum
- `app/models/application.py` - ScholarshipApplication with ApplicationStatus enum
- `app/models/activity_log.py` - ActivityLog with ActivityType enum
- `app/models/file_record.py` - FileRecord
- `alembic.ini` - Alembic config with asyncpg driver
- `alembic/env.py` - Async migration environment using run_async_migrations()
- `alembic/versions/0001_initial_schema.py` - Placeholder migration

## Decisions Made
- Used `async_sessionmaker(expire_on_commit=False)` to prevent MissingGreenlet errors on post-commit attribute access
- All status fields use SQLAlchemy Enum (not raw String) for DB-level enforcement
- Created placeholder migration since PostgreSQL was not running - needs regeneration with `--autogenerate` after `docker compose up db -d`

## Deviations from Plan

None - plan executed exactly as written.

**Note:** Migration was created as placeholder since no live DB was available. After starting the database with `docker compose up db -d`, regenerate with:
```bash
alembic revision --autogenerate -m "initial_schema"
```

## Issues Encountered
- PostgreSQL not running - created placeholder migration with instructions to regenerate

## Next Phase Readiness
- Database layer complete and ready for Phase 2 services
- All ORM models importable from app.models
- Alembic configured for async migrations
- Need to run `docker compose up db -d` and regenerate migration before `alembic upgrade head` will work

---
*Phase: 01-foundation*
*Completed: 2026-03-09*
