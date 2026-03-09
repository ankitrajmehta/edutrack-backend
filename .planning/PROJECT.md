# EduTrack Backend

## What This Is

EduTrack is a blockchain-powered scholarship and education benefit delivery platform for Nepal's education ecosystem. The backend provides a production-grade REST API serving the existing EduTrack frontend (read-only), handling all business logic for 5 user roles (Admin, NGO, Donor, School, Student), Sui blockchain integration via a port-and-adapter abstraction (mock now, real SDK swap later), JWT authentication with RBAC, PostgreSQL persistence, file storage, and a full activity/audit trail.

This is a v1 grant demo built to production-grade standards — no architectural shortcuts. Every design decision must support the path to production without requiring rewrites.

## Core Value

Every education fund allocation is transparently tracked and verifiably delivered, giving donors, NGOs, and the public an auditable record from donation to student wallet.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] REST API serving the existing EduTrack frontend with camelCase responses matching mock.js data shapes
- [ ] JWT authentication (access 30min + refresh 7d) with role-based access control for 5 roles
- [ ] Full CRUD for NGOs, Programs, Students, Donors, Donations, Invoices, Schools, Applications
- [ ] Sui blockchain abstraction layer (port-and-adapter) with mock implementation returning realistic tx hashes
- [ ] Activity log / audit trail written on every significant action
- [ ] File upload/download with local disk storage (S3-compatible interface)
- [ ] Admin dashboard: verify/reject/blacklist NGOs and students, platform-wide stats
- [ ] NGO dashboard: programs, students, invoices, fund allocations, application review
- [ ] Donor browse and donate flows with fund flow transparency
- [ ] School partner registration and invoice submission
- [ ] Student scholarship application and status tracking
- [ ] Public endpoints: aggregate stats, activity feed, verified NGOs/programs (no auth)
- [ ] Database seed script (idempotent) matching mock.js data exactly
- [ ] Docker + Docker Compose setup (app + PostgreSQL)
- [ ] Move smart contract (syntactically valid, deployable to Sui testnet)

### Out of Scope

- Real Sui SDK calls to testnet/mainnet — interface fully defined; mock is one-file swap
- Automated test suite — architecture supports it; added next milestone
- Celery/Redis async task queue — service layer async-ready; queue wrapper next milestone
- Pagination and advanced filtering — small data volume for demo; `?page=&limit=` added later
- Rate limiting, encryption at rest, Nginx reverse proxy — dev environment only
- Multi-language / i18n — strings not hardcoded in logic; i18n layer added later
- Frontend changes — `../edutrack/` is read-only

## Context

- **Frontend exists and is read-only.** The API must match `../edutrack/src/data/mock.js` camelCase field names exactly. All Pydantic schemas must alias snake_case DB columns to camelCase API fields.
- **Grant demo context.** Presented to UNICEF Venture Fund (March 2026 call, $100K equity-free). Demo quality must read as production-grade.
- **Greenfield backend.** No existing backend code — building from scratch into the defined directory structure in `prompt.md`.
- **Blockchain = Sui Move.** Smart contracts use the Sui Move language. The mock implementation must return realistic 64-char hex tx hashes and simulate async latency.
- **Nepal education ecosystem.** 5 distinct stakeholders: System Admin (platform operator), NGO/Program Admin (fund distributor), Donor (fund provider), School (service vendor), Student (beneficiary).
- **tasks.md exists** with detailed task breakdown — implementation should follow that order.

## Constraints

- **Tech Stack:** Python 3.11+, FastAPI (async), PostgreSQL, SQLAlchemy async + Alembic, Pydantic v2, JWT via python-jose + passlib — no deviations
- **FE Contract:** All API response keys must match mock.js camelCase exactly — no renames permitted
- **Architecture:** Thin route handlers, service layer owns all business logic, dependency injection throughout, no global mutable state
- **Async:** All DB operations and external calls must use `async def` — no sync blocking in async context
- **Error Format:** All errors return `{detail, code, statusCode}` — consistent across all endpoints
- **No Frontend Changes:** `../edutrack/` directory is strictly read-only

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Port-and-adapter for blockchain | One-file swap from mock to real Sui SDK without changing callers | — Pending |
| Local disk storage with S3-compatible interface | Drop-in MinIO/S3 for production without code changes | — Pending |
| camelCase aliases on all Pydantic schemas | Frontend mock.js uses camelCase; backend DB uses snake_case | — Pending |
| Scholarship ID auto-generation (EDU-YYYY-XXXXX) | Unique, human-readable ID for each student beneficiary | — Pending |
| Async SQLAlchemy throughout | All endpoints async; blocking DB calls would deadlock the event loop | — Pending |

---
*Last updated: 2026-03-09 after initialization*
