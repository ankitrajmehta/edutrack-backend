# Project State: EduTrack Backend

**Initialized:** 2026-03-09
**Status:** Ready to plan Phase 1

---

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-03-09)

**Core value:** Every education fund allocation is transparently tracked and verifiably delivered, giving donors, NGOs, and the public an auditable record from donation to student wallet.

**Current focus:** Phase 1 — Foundation

---

## Phase Status

| Phase | Name | Status | Plans |
|-------|------|--------|-------|
| 1 | Foundation | In Progress | 1/4 |
| 2 | Entity Management | Not Started | 0/0 |
| 3 | Fund Flow | Not Started | 0/0 |
| 4 | Demo Readiness | Not Started | 0/0 |

---

## Current Position

**Phase:** 1 — Foundation
**Plan:** 1 of 4 (01-01)
**Status:** Completed
**Progress:** ████████░░ 25%

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases total | 4 |
| Requirements total | 63 |
| Requirements mapped | 63 |
| Plans created | 4 |
| Plans complete | 1 |

---

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

**Last action:** Completed 01-01-PLAN.md - Infrastructure Setup (2026-03-09)
**Next action:** Execute /gsd-execute-phase 01-01 to run the plan

---
*State initialized: 2026-03-09*
