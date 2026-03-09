---
phase: 02-entity-management
plan: 01
subsystem: database
tags: [sqlalchemy, alembic, activity-log, asyncpg, postgresql]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "Base ORM model, AsyncSession, initial Alembic migration 0001"
provides:
  - "activity_service.log() callable by all Phase 2 services"
  - "COLOR_MAP with all six activity type colors"
  - "ActivityLog.color column in ORM and DB"
  - "ScholarshipApplication.rejection_reason column in ORM and DB"
  - "ScholarshipApplication.submitted_by_user_id FK column in ORM and DB"
  - "Alembic migration 0002 chained to 0001"
affects:
  - 02-entity-management (plans 02-05 all depend on activity_service)
  - 03-fund-flow
  - 04-demo-readiness

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Late import pattern for activity service (avoids circular dependency: models→database→services)"
    - "Raw op.execute() only in Alembic migrations (asyncpg type event compatibility)"
    - "IF NOT EXISTS in all DDL for idempotent migration applies"
    - "activity_service.log() before db.commit() for atomic logging+action"

key-files:
  created:
    - alembic/versions/0002_phase2_additions.py
    - app/services/activity_service.py (replaced stub)
  modified:
    - app/models/activity_log.py
    - app/models/application.py

key-decisions:
  - "Late import of ActivityLog inside log() function body to prevent circular imports (models→db→services)"
  - "COLOR_MAP fallback to 'gray' for unknown activity types via .get(type, 'gray')"
  - "activity_service.log() is async def for consistency with all other service methods even though no awaits"
  - "submitted_by_user_id uses index=True on column declaration (sufficient — no separate Index() needed)"

patterns-established:
  - "Activity logging pattern: await activity_service.log(db, type, text, actor_id) THEN await db.commit()"
  - "All Alembic DDL via raw op.execute() with IF NOT EXISTS — never op.add_column with sa.Enum"

requirements-completed:
  - ACTV-01
  - APIC-01
  - APIC-02

# Metrics
duration: 2min
completed: 2026-03-09
---

# Phase 2 Plan 01: Activity Logging Service and Phase 2 Database Migration Summary

**`activity_service.log()` with full COLOR_MAP, Alembic migration 0002 adding three columns (color on activity_logs, rejection_reason + submitted_by_user_id on scholarship_applications)**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-09T16:33:01Z
- **Completed:** 2026-03-09T16:34:51Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Implemented `activity_service.log()` with `COLOR_MAP` covering all six activity types (verify, blacklist, program, allocation, donation, invoice)
- Created Alembic migration `0002_phase2_additions.py` that adds three columns using raw `op.execute()` with `IF NOT EXISTS` guards, chained to `down_revision="0001"`
- Updated `ActivityLog` ORM model with `color = Column(String(50), nullable=True)`
- Updated `ScholarshipApplication` ORM model with `rejection_reason` and `submitted_by_user_id` FK columns (indexed)

## Task Commits

Each task was committed atomically:

1. **Task 1: Update ORM models with missing columns** - `c1ce160` (feat)
2. **Task 2: Create Alembic migration 0002_phase2_additions** - `b491e26` (feat)
3. **Task 3: Implement activity_service.log()** - `edb146d` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `app/models/activity_log.py` - Added `color = Column(String(50), nullable=True)` after `actor_id`
- `app/models/application.py` - Added `rejection_reason = Column(Text, nullable=True)` and `submitted_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)`
- `alembic/versions/0002_phase2_additions.py` - Migration adding three columns with IF NOT EXISTS, chained to 0001
- `app/services/activity_service.py` - Replaced 1-line stub with full implementation: `log()` async function + `COLOR_MAP`

## COLOR_MAP Reference (for Wave 2 plans)

```python
COLOR_MAP = {
    "verify": "blue",
    "blacklist": "red",
    "program": "blue",
    "allocation": "purple",
    "donation": "green",
    "invoice": "amber",
}
# Unknown types fall back to "gray"
```

## Decisions Made

- **Late import pattern**: `from app.models.activity_log import ActivityLog` placed inside the `log()` function body to avoid circular imports (`models → database → services` circular chain)
- **No flush before return**: The ORM entry is added to the session via `db.add(entry)` — no `await db.flush()` needed; SQLAlchemy flushes automatically when the caller calls `db.commit()`
- **`async def` consistency**: Even though `log()` has no `await` expressions, it is declared `async def` so all Phase 2 services can `await activity_service.log(...)` uniformly

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `activity_service.log()` is ready for import by plans 02–05
- Migration `0002` is ready to apply — run `alembic upgrade head` when DB is available
- All Wave 2 services can `from app.services import activity_service` without errors
- No blockers for plans 02-02 through 02-05

---
*Phase: 02-entity-management*
*Completed: 2026-03-09*
