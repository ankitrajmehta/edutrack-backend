# PRD: EduTrack — Transparent Child Benefit Delivery Platform (Backend)

## 1. Overview

**EduTrack** is a blockchain-powered scholarship and education benefit delivery platform for Nepal's education ecosystem. It connects NGOs, donors, schools, students, and system administrators to ensure education funds are transparently allocated, tracked, and delivered.

This is the **v1 implementation** — scoped for a grant demo, but built to production-grade standards. Every design decision should support the path to production without requiring rewrites.

The backend is responsible for:
- REST API layer serving the existing EduTrack frontend (no FE changes allowed)
- Business logic for all 5 user roles (Admin, NGO, Donor, School, Student)
- Sui blockchain integration via a clean abstraction layer (mocked implementation, real SDK interface)
- Data persistence and document/file storage
- JWT authentication and role-based access control
- Activity logging and transparency audit trail

**Tech Stack:**
- **Language:** Python 3.11+
- **Framework:** FastAPI (async)
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy (async) + Alembic (migrations)
- **Blockchain:** Sui Move smart contracts — port-and-adapter abstraction (mock now, real Sui SDK is a one-file swap)
- **File Storage:** Local disk with S3-compatible interface (drop-in MinIO/S3 for prod)
- **Auth:** JWT (access 30min + refresh 7d)
- **Containerization:** Docker + Docker Compose

**Explicitly deferred to v2 — conscious scope decisions, not shortcuts:**
- Real Sui SDK calls to testnet/mainnet (interface fully defined; mock is swap-in-place)
- Celery/Redis async task queue (sync for now; service layer is async-ready)
- Automated test suite (architecture fully supports it; tests added next milestone)
- Rate limiting, encryption at rest, Nginx reverse proxy
- Pagination and advanced filtering on list endpoints

---

## 2. User Roles & Permissions

| Role | Description |
|------|-------------|
| **System Admin** | Platform operator. Verifies/blacklists NGOs and students. Views platform-wide stats. |
| **NGO / Program Admin** | Manages scholarship programs, students, invoices, and fund allocation. |
| **Donor** | Browses NGOs/programs and donates funds. |
| **School** | Registers as partner, submits invoices for fund claims. |
| **Student** | Applies for scholarship programs. |
| **Public** | Unauthenticated — views aggregate stats and activity feed. |

---

## 3. Data Models

All models must produce API responses compatible with the FE `mock.js` data shapes (camelCase keys). DB columns use snake_case; Pydantic schemas alias to camelCase.

### 3.1 User (auth)
```
id, email, hashed_password, role (admin|ngo|donor|school|student),
is_active, created_at
```

### 3.2 NGO
```
id, user_id (FK→User), name, location, status (pending|verified|rejected|blacklisted),
description, tax_doc, reg_doc, avatar, color,
total_funded, students_helped, programs_count, registered_date
→ programs[] (relation)
```

### 3.3 Program
```
id, ngo_id (FK→NGO), name, description, status (active|completed),
categories (JSON: tuition|books|uniforms|stationery|food|transport|...),
total_budget, allocated, students_enrolled, start_date, end_date
```

### 3.4 Student
```
id, ngo_id (FK→NGO), program_id (FK→Program),
name, age, school, grade, guardian, location,
scholarship_id (EDU-YYYY-XXXXX, auto-generated),
wallet_balance, total_received, status (active|graduated|blacklisted)
```

### 3.5 Donor
```
id, user_id (FK→User), name, email, total_donated, donations_count
```

### 3.6 Donation
```
id, donor_id (FK→Donor), ngo_id (FK→NGO),
program_id (FK→Program, nullable), student_id (FK→Student, nullable),
amount, date, type (general|program|student), message (nullable),
tx_hash (blockchain reference)
```

### 3.7 Invoice
```
id, school_id (FK→School), ngo_id (FK→NGO), program_id (FK→Program),
school_name, amount, category, status (pending|approved|rejected),
items (JSON: [{desc, amount}]), date, approved_date (nullable),
supporting_doc (file reference), tx_hash (set on approval)
```

### 3.8 School
```
id, user_id (FK→User), name, location, status (pending|verified),
students_in_programs, total_invoiced
```

### 3.9 ScholarshipApplication
```
id, program_id (FK→Program),
student_name, age, grade, school_name, school_district,
guardian_name, guardian_relation, guardian_contact,
reason, status (pending|accepted|rejected), applied_date
```

### 3.10 ActivityLog
```
id, type (donation|invoice|verify|allocation|program|blacklist),
text, timestamp, actor_id (FK→User)
```

### 3.11 FileRecord
```
id, original_name, stored_path, mime_type, size_bytes,
uploaded_by (FK→User), created_at
```

---

## 4. API Endpoints

### 4.1 Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register (role: ngo/donor/school/student) |
| POST | `/api/auth/login` | Login → access + refresh tokens |
| POST | `/api/auth/refresh` | Refresh access token |
| POST | `/api/auth/logout` | Invalidate refresh token |
| GET  | `/api/auth/me` | Current user + role-specific profile |

### 4.2 Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/admin/dashboard` | Aggregated platform stats |
| GET  | `/api/admin/ngos` | List NGOs (filter: `?status=`) |
| PATCH | `/api/admin/ngos/{id}/verify` | Verify NGO |
| PATCH | `/api/admin/ngos/{id}/reject` | Reject NGO |
| PATCH | `/api/admin/ngos/{id}/blacklist` | Blacklist NGO |
| PATCH | `/api/admin/ngos/{id}/restore` | Restore blacklisted NGO |
| GET  | `/api/admin/blacklist` | Combined blacklisted NGOs + students |
| PATCH | `/api/admin/students/{id}/blacklist` | Blacklist student |
| PATCH | `/api/admin/students/{id}/restore` | Restore student |

### 4.3 NGO
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/ngo/dashboard` | NGO-scoped stats |
| POST | `/api/ngo/programs` | Create program |
| GET  | `/api/ngo/programs` | List own programs |
| GET  | `/api/ngo/programs/{id}` | Program detail |
| PUT  | `/api/ngo/programs/{id}` | Update program |
| POST | `/api/ngo/students` | Register student (generates scholarship ID) |
| GET  | `/api/ngo/students` | List students |
| GET  | `/api/ngo/students/{id}` | Student detail with wallet info |
| GET  | `/api/ngo/applications` | Pending applications |
| PATCH | `/api/ngo/applications/{id}/accept` | Accept → auto-create student record |
| PATCH | `/api/ngo/applications/{id}/reject` | Reject with reason |
| GET  | `/api/ngo/invoices` | List invoices from schools |
| PATCH | `/api/ngo/invoices/{id}/approve` | Approve invoice (triggers blockchain tx) |
| PATCH | `/api/ngo/invoices/{id}/reject` | Reject invoice |
| POST | `/api/ngo/allocations` | Allocate funds (triggers blockchain tx) |
| GET  | `/api/ngo/allocations` | Allocation history |

### 4.4 Donor
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/donor/browse/ngos` | Verified NGOs with stats |
| GET  | `/api/donor/browse/programs` | Active programs with NGO info |
| GET  | `/api/donor/browse/students` | Students available for direct support |
| POST | `/api/donor/donate` | Make donation (triggers blockchain tx) |
| GET  | `/api/donor/donations` | Own donation history |
| GET  | `/api/donor/donations/{id}` | Donation detail with fund flow |

### 4.5 School
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/schools/register` | Register school as partner |
| GET  | `/api/schools/profile` | Own school profile |
| POST | `/api/schools/invoices` | Submit invoice |
| GET  | `/api/schools/invoices` | Own invoices with status |

### 4.6 Student
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/student/programs` | Browse active programs |
| POST | `/api/student/apply` | Submit scholarship application |
| GET  | `/api/student/applications` | Own application statuses |

### 4.7 Public (no auth)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/public/stats` | Aggregate platform stats |
| GET  | `/api/public/activity` | Recent activity feed |
| GET  | `/api/public/ngos` | Verified NGOs (public fields) |
| GET  | `/api/public/programs` | Active programs (public fields) |

### 4.8 Files
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/files/upload` | Upload file → returns ID + URL |
| GET  | `/api/files/{id}` | Download file by ID |

---

## 5. Blockchain Abstraction Layer

The blockchain integration uses a **port-and-adapter pattern**. All callers use the `BlockchainService` interface — the underlying implementation is swappable without changing any caller.

### 5.1 Interface (`app/services/blockchain/base.py`)
```python
class BlockchainService(Protocol):
    async def create_wallet(self, student_id: str) -> WalletResult: ...
    async def donate(self, donor_id: str, target_type: str, target_id: str, amount: float) -> TxResult: ...
    async def allocate_funds(self, ngo_id: str, program_id: str, student_id: str, amount: float) -> TxResult: ...
    async def settle_invoice(self, ngo_id: str, school_id: str, invoice_id: str, amount: float) -> TxResult: ...
    async def get_balance(self, wallet_id: str) -> float: ...
```

### 5.2 Mock Implementation (`app/services/blockchain/mock_sui.py`)
- Fully implements `BlockchainService`
- Returns realistic Sui-style tx hashes (`secrets.token_hex(32)` → 64-char hex)
- Simulates async network latency (`asyncio.sleep(0.1–0.4)`)
- Logs every call with structured output
- All results persisted to DB (identical to what the real implementation does)

### 5.3 Move Contract (`contracts/sources/scholarship.move`)
- Complete, syntactically valid Move module
- All functions implemented with correct signatures and full documentation
- Ready to `sui move publish` to testnet — just needs funded wallet and Sui CLI

### 5.4 Upgrading to Real Sui SDK
1. `pip install pysui`
2. Implement `SuiBlockchainService` in `app/services/blockchain/sui.py` (same interface)
3. Change one line in `app/core/dependencies.py`: `blockchain_service = SuiBlockchainService(...)`
4. Zero other changes required

---

## 6. Architecture Principles

These are non-negotiable regardless of demo vs. production context:

- **Thin route handlers** — handlers do auth, call one service method, return response. No business logic in handlers.
- **Service layer owns business logic** — all DB writes, stat updates, activity logging, and blockchain calls inside service methods. Services are independently testable.
- **Async throughout** — all DB operations and external calls use `async def`. No sync blocking in async context.
- **Explicit error handling** — no silent exception swallowing. All errors caught, logged, and returned as structured JSON via a global exception handler.
- **Type safety** — full type hints on all function signatures. Pydantic v2 for all request/response validation.
- **Dependency injection** — DB sessions, current user, blockchain service all injected via FastAPI `Depends()`. No global mutable state.
- **Consistent error format** — all errors return `{detail, code, statusCode}`. HTTP 400/401/403/404/409/422/500.
- **Idempotent operations** — migrations and seed script safe to re-run.
- **Structured logging** — use Python `logging` with consistent format. Errors always logged before raising.

---

## 7. FE Contract

All API responses use **camelCase** keys matching `../edutrack/src/data/mock.js`. The frontend must not be modified.

`scripts/seed.py` populates the DB with data identical to `mock.js` (same IDs, values, relationships). The FE works against the real API from day one.

---

## 8. Out of Scope (v1) — Deferred, Not Forgotten

| Feature | Deferred Because | Production Path |
|---------|-----------------|-----------------|
| Real Sui SDK calls | Interface defined; one-file swap | Implement `SuiBlockchainService`, update DI binding |
| Automated tests | Architecture supports it; next milestone | `pytest` + `httpx` integration tests, >80% coverage |
| Celery/Redis | Service layer async-ready | Wrap service calls in Celery tasks |
| Pagination/filtering | Small data volume for demo | Add `?page=&limit=` + SQLAlchemy `.offset().limit()` |
| Rate limiting | No traffic in demo | Nginx/gateway layer in production |
| Encryption at rest | Dev environment only | Configure PostgreSQL TDE + field-level encryption |
| Multi-language | Strings not hardcoded in logic | i18n layer over response text |
