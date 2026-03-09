---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: planning
last_updated: "2026-03-09T18:23:33Z"
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 10
  completed_plans: 11
  percent: 100
---

# Project State: EduTrack Backend

**Initialized:** 2026-03-09
**Status:** Ready to plan

---

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-03-09)

**Core value:** Every education fund allocation is transparently tracked and verifiably delivered, giving donors, NGOs, and the public an auditable record from donation to student wallet.

**Current focus:** Phase 3 — Fund Flow

---

## Phase Status

| Phase | Name | Status | Plans |
|-------|------|--------|-------|
| 1 | Foundation | Complete | 5/5 |
| 2 | Entity Management | Complete | 5/5 |
| 3 | Fund Flow | In Progress | 2/2 |
| 4 | Demo Readiness | Not Started | 0/0 |

---

## Current Position

**Phase:** 3 — Fund Flow (In Progress)
**Plan:** 2 of 2 (03-02 — DONE)
**Status:** Plan Complete
**Progress:** [██████████] 100%

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases total | 4 |
| Requirements total | 63 |
| Requirements mapped | 63 |
| Plans created | 4 |
| Plans complete | 3 |

---

| Phase 01-foundation P04 | 88 min | 2 tasks | 8 files |
| Phase 01-foundation P05 | 6min | 3 tasks | 4 files |
| Phase 02-entity-management P01 | 2min | 3 tasks | 4 files |
| Phase 02-entity-management P02 | 2min | 3 tasks | 3 files |
| Phase 02-entity-management P03 | 2min | 3 tasks | 3 files |
| Phase 02-entity-management P04 | 3min | 3 tasks | 6 files |
| Phase 02-entity-management P05 | 3min | 3 tasks | 3 files |
| Phase 03-fund-flow P01 | <1min | 2 tasks | 5 files |
| Phase 03-fund-flow P02 | 2min | 2 tasks | 2 files |

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-09 | 4 phases at coarse granularity | Foundation → Entity Mgmt → Fund Flow → Demo Readiness maps cleanly to the dependency graph; no phase is skippable |
| 2026-03-09 | Blockchain abstraction (BLKC-01–04) in Phase 1 | Every service in Phase 2+ calls `get_blockchain()`; the Protocol + mock must exist before any service is written |
| 2026-03-09 | RBAC-01 in Phase 1, RBAC-02–05 in Phase 2 | The guard mechanism must exist before the entities it guards; ownership scoping is enforced in service layer |
| 2026-03-09 | Invoice submission (SCHL-03–04) deferred to Phase 3 | Invoice submission + approval are a single blockchain-tx workflow; splitting them across phases creates a half-working feature |
| 2026-03-09 | ACTV-01 in Phase 2, ACTV-02 in Phase 4 | Activity log writer must exist when services are built (Phase 2); public feed shape (relative time) is a demo-layer concern (Phase 4) |
| 2026-03-09 | Alembic `--template async` non-negotiable | Sync env.py + asyncpg deadlocks; noted as CRITICAL pitfall in research |
| 2026-03-09 | bcrypt pinned `>=4.1.2,<5.0.0` | 4.1.0 yanked, ≥5.0.0 breaks passlib; verified via pip index on 2026-03-09 |
| 2026-03-09 | FastAPI app with CORS and exception handlers | Created in Plan 01-01 - all 8 routers registered under /api prefix |
| 2026-03-09 | Pydantic BaseSettings for env management | All env vars loaded via app/core/config.py with safe defaults |
| 2026-03-09 | Docker Compose with PostgreSQL healthcheck | App waits for DB to be healthy before starting |
| 2026-03-09 | StarletteHTTPException handler after RequestValidationError in exception chain | Starlette's ExceptionMiddleware catches bare HTTP errors before our generic handler; dedicated handler required |
| 2026-03-09 | Alembic enum types with create_type=False pattern | Enum types created once with .create(op.get_bind()), columns reference with create_type=False to avoid 'type already exists' |
| 2026-03-09 | Late import of ActivityLog inside log() to prevent circular deps | models→database→services circular chain; late import inside function body is the only safe pattern |
| 2026-03-09 | activity_service.log() as async def with no awaits | Consistency with all Phase 2 service methods — callers use await uniformly |
| 2026-03-09 | totalNGOs alias with capital NGOs | Exact match to mock.js platformStats.totalNGOs — camelCase with NGO as acronym |
| 2026-03-09 | restore action maps to NGOStatus.pending not verified | NGO re-enters review queue after restoration — consistent with business requirement |
| 2026-03-09 | Router prefix-free pattern for role routers | donor/school/student routers have no prefix; main.py supplies /api/{role} prefix; avoids doubled path segments |
| 2026-03-09 | Files router has no APIRouter prefix (02-05) | main.py registers with prefix=/api/files; router-level prefix would create /api/files/files/upload double path |
| 2026-03-09 | _create_student() shared helper — canonical student creation | Single implementation prevents drift; both direct registration and accept-application enforce blockchain atomicity and scholarship ID format |
| 2026-03-09 | get_current_ngo defined locally in ngo.py (not dependencies.py) | NGO profile resolution is domain-specific; not appropriate for global dependencies.py |
| 2026-03-09 | db.refresh(ngo) after _create_student() commit | _create_student() internally commits which expires SQLAlchemy ORM state; refresh mandatory before updating counters |
| 2026-03-09 | blockchain.donate() called before db.commit() in create_donation | Tx atomicity requires blockchain tx recorded before database commit |
| 2026-03-09 | Ownership check via ForbiddenError in get_donation_detail | Prevents donors from viewing each other's donation details |

---

## Accumulated Context

### Architecture Constraints (carry forward to every plan)
- All route handlers and service methods must be `async def` — no blocking in event loop
- `async_sessionmaker(expire_on_commit=False)` — prevents MissingGreenlet on post-commit access
- `selectinload()` for one-to-many, `joinedload()` for many-to-one — never default lazy loading
- Service layer owns all `db.commit()` calls — no commits in route handlers
- `activity_service.log()` called before `db.commit()` — atomicity requirement
- Blockchain injected via `Depends(get_blockchain)` — no direct mock imports in callers
- All response schemas return Pydantic model instances (not dicts) — aliases only fire on Pydantic serialization
- CORS: explicit origins only (`localhost:3000`, `localhost:5173`) — wildcard + credentials is browser-rejected

### Key Pitfalls (from research — address in sequence)
- Phase 1: Alembic async env.py (#1), MissingGreenlet (#2), Pydantic v2 BaseResponse (#3), JWT sub as str (#4), CORS origins (#5), bcrypt pin (#6), async bcrypt hashing (#9), refresh token race (#11)
- Phase 2: Activity log before commit (#7), session sharing (#8), camelCase aliases via Pydantic models (#12)
- Phase 3: Optional[str] = None defaults (#10), session-per-request in concurrent async code (#8)

### Todos / Open Questions
- [ ] Verify `../edutrack/src/data/mock.js` field names before writing any Phase 2 schema — FE contract is exact
- [ ] Confirm seed script IDs match mock.js hardcoded route params before Phase 4 plan

---

## Session Continuity

**Last action:** Completed 03-02-PLAN.md - Donor Donation Endpoints (2026-03-09)
**Next action:** Ready for more Phase 3 plans

---

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 1 | Fix UAT gaps from phase 02-entity-management | 2026-03-09 | 494eec8 | [1-fix-uat-gaps-from-phase-02-entity-manage](.planning/quick/1-fix-uat-gaps-from-phase-02-entity-manage/) |

---

Last activity: 2026-03-09 - Completed quick task 1: Fix UAT gaps from phase 02-entity-management

---
*State initialized: 2026-03-09*
