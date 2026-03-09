# Requirements: EduTrack Backend

**Defined:** 2026-03-09
**Core Value:** Every education fund allocation is transparently tracked and verifiably delivered, giving donors, NGOs, and the public an auditable record from donation to student wallet.

## v1 Requirements

### Infrastructure

- [x] **INFRA-01**: Project scaffolding exists (directory structure from prompt.md) with all packages installable via requirements.txt
- [x] **INFRA-02**: PostgreSQL connection works via async SQLAlchemy (asyncpg driver) with Alembic migrations (async template)
- [x] **INFRA-03**: Docker Compose runs app + PostgreSQL with a single `docker compose up`
- [x] **INFRA-04**: `.env` / `config.py` (Pydantic BaseSettings) loads all required environment variables
- [x] **INFRA-05**: Global exception handler returns all errors as `{detail, code, statusCode}` JSON — no unhandled 500s leak stack traces to clients
- [ ] **INFRA-06**: Seed script (idempotent) populates DB with data matching mock.js exactly (same IDs, values, relationships)

### Authentication

- [x] **AUTH-01**: User can register with email, password, and role (ngo/donor/school/student)
- [x] **AUTH-02**: User can log in and receive a JWT access token (30min) and refresh token (7d)
- [ ] **AUTH-03**: User can refresh their access token using a valid refresh token
- [ ] **AUTH-04**: User can log out (refresh token invalidated)
- [ ] **AUTH-05**: User can retrieve their own profile via `GET /api/auth/me` including role-specific data
- [ ] **AUTH-06**: Protected endpoints reject requests with missing or expired tokens with HTTP 401

### Role-Based Access Control

- [ ] **RBAC-01**: Each endpoint enforces role requirement — wrong role receives HTTP 403
- [ ] **RBAC-02**: NGO users can only access/modify their own programs, students, invoices, and allocations
- [ ] **RBAC-03**: School users can only access/modify their own invoices and profile
- [ ] **RBAC-04**: Student users can only view their own applications
- [ ] **RBAC-05**: Donor users can only view their own donation history

### Admin

- [ ] **ADMN-01**: Admin can view aggregated platform stats (total donations, students, NGOs, programs, schools, funds allocated/utilized)
- [ ] **ADMN-02**: Admin can list all NGOs, filterable by status (pending/verified/rejected/blacklisted)
- [ ] **ADMN-03**: Admin can verify, reject, blacklist, or restore an NGO
- [ ] **ADMN-04**: Admin can view combined blacklist (blacklisted NGOs + students)
- [ ] **ADMN-05**: Admin can blacklist or restore a student

### NGO

- [ ] **NGO-01**: NGO can view their own dashboard stats (programs count, students helped, funds allocated)
- [ ] **NGO-02**: NGO can create a scholarship program with name, description, categories, budget, and dates
- [ ] **NGO-03**: NGO can list, view, and update their own programs
- [ ] **NGO-04**: NGO can register a student (generates EDU-YYYY-XXXXX scholarship ID, creates blockchain wallet)
- [ ] **NGO-05**: NGO can list and view their own students including wallet balance
- [ ] **NGO-06**: NGO can view pending scholarship applications for their programs
- [ ] **NGO-07**: NGO can accept an application (auto-creates student record) or reject it with a reason
- [ ] **NGO-08**: NGO can list invoices submitted by schools for their programs
- [ ] **NGO-09**: NGO can approve an invoice (triggers blockchain settlement tx, sets tx_hash) or reject it
- [ ] **NGO-10**: NGO can allocate funds to a student or program (triggers blockchain allocation tx, sets tx_hash)
- [ ] **NGO-11**: NGO can view allocation history

### Donor

- [ ] **DONOR-01**: Donor can browse verified NGOs with stats
- [ ] **DONOR-02**: Donor can browse active programs with NGO info
- [ ] **DONOR-03**: Donor can browse students available for direct support
- [ ] **DONOR-04**: Donor can donate to an NGO, program, or student (triggers blockchain donation tx, sets tx_hash)
- [ ] **DONOR-05**: Donor can view their own donation history
- [ ] **DONOR-06**: Donor can view a single donation detail including fund flow (where money went)

### School

- [ ] **SCHL-01**: School can register as a partner
- [ ] **SCHL-02**: School can view their own profile
- [ ] **SCHL-03**: School can submit an invoice to claim funds (with supporting document reference)
- [ ] **SCHL-04**: School can view their own invoices with current status

### Student

- [ ] **STUD-01**: Student can browse active scholarship programs
- [ ] **STUD-02**: Student can submit a scholarship application to a program
- [ ] **STUD-03**: Student can view the status of their own applications

### Public

- [ ] **PUBL-01**: Unauthenticated user can view aggregate platform stats
- [ ] **PUBL-02**: Unauthenticated user can view a recent activity feed (type, text, time as relative string)
- [ ] **PUBL-03**: Unauthenticated user can browse verified NGOs (public fields only)
- [ ] **PUBL-04**: Unauthenticated user can browse active programs (public fields only)

### Blockchain Abstraction

- [x] **BLKC-01**: `BlockchainService` Protocol (interface) defined in `app/services/blockchain/base.py` with methods: `create_wallet`, `donate`, `allocate_funds`, `settle_invoice`, `get_balance`
- [x] **BLKC-02**: Mock implementation returns realistic 64-char hex tx hashes and simulates async latency (0.1–0.4s)
- [x] **BLKC-03**: All blockchain calls log structured output
- [x] **BLKC-04**: Blockchain service injected via `Depends(get_blockchain)` — no direct imports of mock in callers
- [ ] **BLKC-05**: Sui Move smart contract (`contracts/sources/scholarship.move`) is syntactically valid and deployable to testnet

### Activity Logging

- [ ] **ACTV-01**: Every significant action (donation, invoice approval, fund allocation, NGO verify/blacklist, student registration, program creation, application accept/reject) writes an ActivityLog entry in the same DB transaction
- [ ] **ACTV-02**: Activity log entries expose `{type, color, text, time}` shape on the public activity feed endpoint, where `time` is a relative string ("2 hours ago")

### File Storage

- [ ] **FILE-01**: User can upload a file and receive a file ID and URL in response
- [ ] **FILE-02**: User can download a file by ID
- [ ] **FILE-03**: File storage uses local disk with an S3-compatible interface (drop-in swap for MinIO/S3)

### API Contract

- [ ] **APIC-01**: All API responses use camelCase field names matching `../edutrack/src/data/mock.js` exactly
- [ ] **APIC-02**: All Pydantic response schemas use `from_attributes=True` and `Field(alias="camelCase")` for any snake_case DB field
- [ ] **APIC-03**: The existing EduTrack frontend works against the live API from day one (no mock.js fallback needed)

## v2 Requirements

### Real Blockchain

- **BLKC-V2-01**: Real Sui SDK (`pysui`) implementation of `BlockchainService` (`app/services/blockchain/sui.py`)
- **BLKC-V2-02**: One-line swap in `dependencies.py` connects to testnet/mainnet

### Async Task Queue

- **TASK-V2-01**: Celery + Redis wraps long-running blockchain calls
- **TASK-V2-02**: Task status polling endpoint

### Automated Tests

- **TEST-V2-01**: `pytest` + `httpx` integration test suite with >80% coverage

### Pagination & Filtering

- **PAGE-V2-01**: All list endpoints support `?page=&limit=` pagination
- **PAGE-V2-02**: NGO list supports `?status=` filter (already partially scoped in v1 admin endpoint)

### Security Hardening

- **SEC-V2-01**: Rate limiting at Nginx/gateway layer
- **SEC-V2-02**: Encryption at rest for sensitive fields
- **SEC-V2-03**: Replace `passlib` (unmaintained) with direct `bcrypt` library

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real Sui SDK calls to testnet/mainnet | Interface fully defined; mock is one-file swap — deferred to v2 |
| Automated test suite | Architecture supports it; adds time without changing demo outcome |
| Celery/Redis task queue | Service layer async-ready; sync sufficient for demo traffic |
| Pagination / advanced filtering | Small data volume for demo; `?page=&limit=` added in v2 |
| Rate limiting / Nginx / encryption at rest | Dev environment only; production hardening in v2 |
| Email notifications | No email infra for demo; add in v2 with SendGrid/SES |
| Multi-language / i18n | Strings not hardcoded in logic; i18n layer added later |
| Frontend changes | `../edutrack/` is strictly read-only |
| KYC / AML verification | Beyond scope of grant demo |
| Real-time websockets | Demo uses polling; websockets in v2 |

## Traceability

| Requirement | Phase | Phase Name | Status |
|-------------|-------|------------|--------|
| INFRA-01 | Phase 1 | Foundation | Pending |
| INFRA-02 | Phase 1 | Foundation | Pending |
| INFRA-03 | Phase 1 | Foundation | Pending |
| INFRA-04 | Phase 1 | Foundation | Pending |
| INFRA-05 | Phase 1 | Foundation | Pending |
| INFRA-06 | Phase 4 | Demo Readiness | Pending |
| AUTH-01 | Phase 1 | Foundation | Pending |
| AUTH-02 | Phase 1 | Foundation | Pending |
| AUTH-03 | Phase 1 | Foundation | Pending |
| AUTH-04 | Phase 1 | Foundation | Pending |
| AUTH-05 | Phase 1 | Foundation | Pending |
| AUTH-06 | Phase 1 | Foundation | Pending |
| RBAC-01 | Phase 1 | Foundation | Pending |
| RBAC-02 | Phase 2 | Entity Management | Pending |
| RBAC-03 | Phase 2 | Entity Management | Pending |
| RBAC-04 | Phase 2 | Entity Management | Pending |
| RBAC-05 | Phase 2 | Entity Management | Pending |
| ADMN-01 | Phase 2 | Entity Management | Pending |
| ADMN-02 | Phase 2 | Entity Management | Pending |
| ADMN-03 | Phase 2 | Entity Management | Pending |
| ADMN-04 | Phase 2 | Entity Management | Pending |
| ADMN-05 | Phase 2 | Entity Management | Pending |
| NGO-01 | Phase 2 | Entity Management | Pending |
| NGO-02 | Phase 2 | Entity Management | Pending |
| NGO-03 | Phase 2 | Entity Management | Pending |
| NGO-04 | Phase 2 | Entity Management | Pending |
| NGO-05 | Phase 2 | Entity Management | Pending |
| NGO-06 | Phase 2 | Entity Management | Pending |
| NGO-07 | Phase 2 | Entity Management | Pending |
| NGO-08 | Phase 3 | Fund Flow | Pending |
| NGO-09 | Phase 3 | Fund Flow | Pending |
| NGO-10 | Phase 3 | Fund Flow | Pending |
| NGO-11 | Phase 3 | Fund Flow | Pending |
| DONOR-01 | Phase 2 | Entity Management | Pending |
| DONOR-02 | Phase 2 | Entity Management | Pending |
| DONOR-03 | Phase 2 | Entity Management | Pending |
| DONOR-04 | Phase 3 | Fund Flow | Pending |
| DONOR-05 | Phase 3 | Fund Flow | Pending |
| DONOR-06 | Phase 3 | Fund Flow | Pending |
| SCHL-01 | Phase 2 | Entity Management | Pending |
| SCHL-02 | Phase 2 | Entity Management | Pending |
| SCHL-03 | Phase 3 | Fund Flow | Pending |
| SCHL-04 | Phase 3 | Fund Flow | Pending |
| STUD-01 | Phase 2 | Entity Management | Pending |
| STUD-02 | Phase 2 | Entity Management | Pending |
| STUD-03 | Phase 2 | Entity Management | Pending |
| PUBL-01 | Phase 4 | Demo Readiness | Pending |
| PUBL-02 | Phase 4 | Demo Readiness | Pending |
| PUBL-03 | Phase 4 | Demo Readiness | Pending |
| PUBL-04 | Phase 4 | Demo Readiness | Pending |
| BLKC-01 | Phase 1 | Foundation | Pending |
| BLKC-02 | Phase 1 | Foundation | Pending |
| BLKC-03 | Phase 1 | Foundation | Pending |
| BLKC-04 | Phase 1 | Foundation | Pending |
| BLKC-05 | Phase 4 | Demo Readiness | Pending |
| ACTV-01 | Phase 2 | Entity Management | Pending |
| ACTV-02 | Phase 4 | Demo Readiness | Pending |
| FILE-01 | Phase 2 | Entity Management | Pending |
| FILE-02 | Phase 2 | Entity Management | Pending |
| FILE-03 | Phase 2 | Entity Management | Pending |
| APIC-01 | Phase 2 | Entity Management | Pending |
| APIC-02 | Phase 2 | Entity Management | Pending |
| APIC-03 | Phase 4 | Demo Readiness | Pending |

**Coverage:**
- v1 requirements: 63 total
- Mapped to phases: 63
- Unmapped: 0 ✓

| Phase | Requirements |
|-------|-------------|
| Phase 1 — Foundation | INFRA-01–05, AUTH-01–06, RBAC-01, BLKC-01–04 (16 requirements) |
| Phase 2 — Entity Management | RBAC-02–05, ADMN-01–05, NGO-01–07, DONOR-01–03, SCHL-01–02, STUD-01–03, ACTV-01, FILE-01–03, APIC-01–02 (30 requirements) |
| Phase 3 — Fund Flow | NGO-08–11, DONOR-04–06, SCHL-03–04 (9 requirements) |
| Phase 4 — Demo Readiness | INFRA-06, PUBL-01–04, BLKC-05, ACTV-02, APIC-03 (8 requirements) |

---
*Requirements defined: 2026-03-09*
*Last updated: 2026-03-09 — traceability confirmed after roadmap creation*
