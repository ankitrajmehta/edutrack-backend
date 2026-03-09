# PRD: EduTrack — Transparent Child Benefit Delivery Platform (Backend)

## 1. Overview

**EduTrack** is a transparent, blockchain-powered scholarship and education benefit delivery platform built for Nepal's education ecosystem. It connects NGOs, donors, schools, students, and system administrators to ensure that education funds are transparently allocated, tracked, and delivered to children who need them.

The **backend** is responsible for:
- REST API layer serving the existing EduTrack frontend (no FE changes allowed)
- Business logic for all 5 user roles (Admin, NGO, Donor, School, Student)
- Sui blockchain smart contract integration for on-chain fund management
- Data persistence and document/file storage
- Authentication and role-based access control

**Tech Stack:**
- **Language:** Python (FastAPI)
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy (async) + Alembic (migrations)
- **Blockchain:** Sui Move smart contracts (via Sui Python SDK)
- **File Storage:** Local / S3-compatible (MinIO for dev)
- **Auth:** JWT (access + refresh tokens)
- **Task Queue:** Celery + Redis (optional, for async jobs)
- **Containerization:** Docker + Docker Compose

---

## 2. User Roles & Permissions

| Role | Description |
|------|-------------|
| **System Admin** | Platform operator. Verifies/blacklists NGOs and student accounts. Views platform-wide stats. |
| **Program Admin / NGO** | Organization managing scholarship programs, students, invoices, and fund allocation. |
| **Donor** | Individual or organization that browses NGOs/programs and donates funds. |
| **School** | Educational institution that registers as a partner and submits invoices for fund claims. |
| **Student** | Applies for scholarship programs. |
| **Public** | Unauthenticated viewer of aggregate platform stats and transparency dashboard. |

---

## 3. Data Models (Derived from Frontend Mock Data)

> These models must produce API responses compatible with the existing FE `mock.js` data shapes.

### 3.1 NGO / Organization
```
id, name, location, status (pending|verified|rejected), description,
tax_doc (file), reg_doc (file), avatar, color,
total_funded, students_helped, programs_count, registered_date,
programs[] (relation)
```

### 3.2 Program
```
id, ngo_id (FK), name, description, status (active|completed),
categories[] (tuition|books|uniforms|stationery|food|transport|lab equipment|training|infrastructure|materials),
total_budget, allocated, students_enrolled,
start_date, end_date
```

### 3.3 Student
```
id, name, age, school, grade, guardian, program_id (FK), ngo_id (FK),
scholarship_id (auto-generated, e.g. "EDU-2026-XXXXX"),
wallet_balance, total_received, status (active|graduated),
location
```

### 3.4 Donor
```
id, name, email, total_donated, donations_count
```

### 3.5 Donation
```
id, donor_id (FK), ngo_id (FK), program_id (FK, nullable),
student_id (FK, nullable), amount, date,
type (general|program|student), message (optional),
tx_hash (Sui transaction)
```

### 3.6 Invoice
```
id, school_id (FK), school_name, ngo_id (FK), program_id (FK),
amount, category, status (pending|approved|rejected),
items[] (desc, amount), date, approved_date,
supporting_doc (file)
```

### 3.7 School
```
id, name, location, status (pending|verified),
students_in_programs, total_invoiced
```

### 3.8 Activity Log
```
id, type (donation|invoice|verify|allocation|program|blacklist),
text, timestamp, actor_id
```

### 3.9 Platform Stats (Aggregated)
```
total_donations, total_students, total_ngos, total_programs,
total_schools, funds_allocated, funds_utilized
```

### 3.10 Scholarship Application
```
id, student_name, age, grade, school_name, school_district,
guardian_name, guardian_relation, guardian_contact,
reason_text, program_id (FK), status (pending|accepted|rejected),
applied_date
```

---

## 4. API Endpoints (REST)

### 4.1 Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register (NGO, Donor, School, Student) |
| POST | `/api/auth/login` | Login → JWT tokens |
| POST | `/api/auth/refresh` | Refresh access token |
| POST | `/api/auth/logout` | Invalidate token |
| GET  | `/api/auth/me` | Current user profile |

### 4.2 Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/admin/dashboard` | Platform overview stats |
| GET  | `/api/admin/ngos` | List all NGOs (with status filter) |
| PATCH | `/api/admin/ngos/{id}/verify` | Approve NGO verification |
| PATCH | `/api/admin/ngos/{id}/reject` | Reject NGO |
| PATCH | `/api/admin/ngos/{id}/blacklist` | Blacklist an NGO |
| GET  | `/api/admin/blacklist` | List blacklisted NGOs & students |
| PATCH | `/api/admin/students/{id}/blacklist` | Blacklist student account |
| PATCH | `/api/admin/ngos/{id}/restore` | Restore blacklisted NGO |
| PATCH | `/api/admin/students/{id}/restore` | Restore blacklisted student |

### 4.3 NGO / Program Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/ngo/dashboard` | NGO-specific dashboard stats |
| POST | `/api/ngo/programs` | Create scholarship program |
| GET  | `/api/ngo/programs` | List own programs |
| GET  | `/api/ngo/programs/{id}` | Program detail |
| PUT  | `/api/ngo/programs/{id}` | Update program |
| POST | `/api/ngo/students` | Register student + generate scholarship ID + assign wallet |
| GET  | `/api/ngo/students` | List registered students |
| GET  | `/api/ngo/students/{id}` | Student detail with wallet info |
| GET  | `/api/ngo/applications` | List pending student applications |
| PATCH | `/api/ngo/applications/{id}/accept` | Accept student application |
| PATCH | `/api/ngo/applications/{id}/reject` | Reject student application |
| GET  | `/api/ngo/invoices` | List invoices from schools |
| PATCH | `/api/ngo/invoices/{id}/approve` | Approve invoice |
| PATCH | `/api/ngo/invoices/{id}/reject` | Reject invoice |
| POST | `/api/ngo/allocations` | Allocate funds to student/program |
| GET  | `/api/ngo/allocations` | List fund allocations |
| POST | `/api/ngo/receipts` | Create receipt with supporting docs |

### 4.4 Donor
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/donor/browse/ngos` | Browse verified NGOs |
| GET  | `/api/donor/browse/programs` | Browse active programs |
| GET  | `/api/donor/browse/students` | Browse students (for direct donation) |
| POST | `/api/donor/donate` | Make donation (triggers Sui tx) |
| GET  | `/api/donor/donations` | List own donations with tracking |
| GET  | `/api/donor/donations/{id}` | Donation detail + fund flow |

### 4.5 School
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/schools/register` | Register school as partner |
| GET  | `/api/schools/profile` | School profile |
| POST | `/api/schools/invoices` | Submit invoice to NGO |
| GET  | `/api/schools/invoices` | List own invoices |
| POST | `/api/schools/invoices/{id}/documents` | Upload supporting doc |

### 4.6 Student
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/student/programs` | Browse available programs |
| POST | `/api/student/apply` | Apply for a scholarship |
| GET  | `/api/student/applications` | View own applications & status |

### 4.7 Public
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/public/stats` | Aggregate platform stats |
| GET  | `/api/public/activity` | Recent platform activity feed |
| GET  | `/api/public/ngos` | List verified NGOs (public view) |
| GET  | `/api/public/programs` | List active programs (public view) |

---

## 5. Sui Blockchain Integration

### 5.1 Smart Contract (Move)
The Move contract handles on-chain fund management:

- **Scholarship Wallet**: Each student gets an on-chain wallet object
- **Donation Escrow**: Donations are held in a program/NGO escrow until allocated
- **Fund Allocation**: NGO allocates from escrow → student wallets
- **Invoice Settlement**: Approved invoices trigger on-chain payment to school
- **Transparency Ledger**: All fund movements are on-chain and publicly auditable

### 5.2 Key Contract Functions
| Function | Description |
|----------|-------------|
| `create_scholarship_wallet(student_id)` | Creates on-chain wallet for student |
| `donate(donor, target_type, target_id, amount)` | Deposits funds into escrow |
| `allocate_funds(ngo, program, student, amount)` | Moves from escrow → student wallet |
| `settle_invoice(ngo, school, invoice_id, amount)` | Pays school from program escrow |
| `get_balance(wallet_id)` | Reads on-chain balance |
| `get_transaction_history(entity_id)` | Reads fund flow history |

### 5.3 Off-chain ↔ On-chain Sync
- Backend creates Sui transactions and records `tx_hash` in the database
- Periodic sync job verifies on-chain state matches off-chain records
- All financial operations are dual-written (DB + chain)

---

## 6. Atomic Task Breakdown

> Tasks are ordered by dependency. Each task is independently testable and deployable.

---

### PHASE 1: Foundation & Infrastructure

#### Task 1.1 — Project Scaffolding
- Initialize Python project with `pyproject.toml` / `requirements.txt`
- Set up FastAPI app structure: `app/`, `app/api/`, `app/models/`, `app/schemas/`, `app/services/`, `app/core/`
- Configure `app/core/config.py` (env vars, settings via Pydantic `BaseSettings`)
- Create `Dockerfile` and `docker-compose.yml` (app + PostgreSQL + Redis)
- Set up `.env.example`
- **Deliverable:** App runs with a health-check endpoint `GET /api/health`

#### Task 1.2 — Database Setup & Migrations
- Configure SQLAlchemy async engine + session factory
- Set up Alembic for migrations
- Create initial migration (empty)
- **Deliverable:** `alembic upgrade head` runs without errors

#### Task 1.3 — Core Data Models
- Implement SQLAlchemy models for all 10 entities (Section 3)
- Define relationships (NGO ↔ Programs ↔ Students, etc.)
- Create Alembic migration for all tables
- **Deliverable:** All tables created in PostgreSQL, verified via `psql`

#### Task 1.4 — Pydantic Schemas (Request/Response)
- Create Pydantic v2 schemas matching the FE `mock.js` shape for all entities
- Separate `Create`, `Update`, `Response` schemas per entity
- **Deliverable:** Schema validation tests pass

#### Task 1.5 — Auth System (JWT)
- Implement password hashing (bcrypt)
- JWT token generation (access: 30min, refresh: 7d)
- Login/register/refresh/logout endpoints
- `get_current_user` dependency
- Role-based permission decorators (`require_role("admin")`)
- **Deliverable:** Register → Login → Access protected route works end-to-end

#### Task 1.6 — File Upload Service
- Implement file upload/download (tax docs, registration docs, invoices, supporting docs)
- Store metadata in DB, file on local disk (S3 adapter for prod)
- `POST /api/files/upload` + `GET /api/files/{id}`
- **Deliverable:** Upload PDF → retrieve by ID

---

### PHASE 2: Core Business Logic (CRUD + Role APIs)

#### Task 2.1 — Admin: Dashboard & Stats
- `GET /api/admin/dashboard` — aggregate counts (pending NGOs, verified, rejected, schools, students, funds)
- Query platform stats from DB
- **Deliverable:** Returns JSON matching `platformStats` shape from `mock.js`

#### Task 2.2 — Admin: NGO Verification & Blacklisting
- `GET /api/admin/ngos` with `?status=` filter
- `PATCH /api/admin/ngos/{id}/verify` — set status → verified
- `PATCH /api/admin/ngos/{id}/reject` — set status → rejected
- `PATCH /api/admin/ngos/{id}/blacklist` — set status → blacklisted
- `PATCH /api/admin/ngos/{id}/restore` — set status back to verified
- Activity log entry on each action
- **Deliverable:** Admin can verify & blacklist NGOs via API

#### Task 2.3 — Admin: Student Blacklisting
- `PATCH /api/admin/students/{id}/blacklist`
- `PATCH /api/admin/students/{id}/restore`
- `GET /api/admin/blacklist` — combined blacklisted NGOs + students list
- **Deliverable:** Blacklist/restore students via API

#### Task 2.4 — NGO: Registration & Profile
- `POST /api/auth/register` (type=ngo) — creates org account with doc uploads
- NGO profile fetched from `GET /api/auth/me` (when role=ngo)
- Return data matching `ngos[]` shape from `mock.js`
- **Deliverable:** NGO registers, profile returns correct shape

#### Task 2.5 — NGO: Program CRUD
- `POST /api/ngo/programs` — create with name, description, categories, budget, dates
- `GET /api/ngo/programs` — list own programs
- `GET /api/ngo/programs/{id}` — detail
- `PUT /api/ngo/programs/{id}` — update
- Response matches `programs[]` shape
- **Deliverable:** Full program lifecycle via API

#### Task 2.6 — NGO: Student Registration
- `POST /api/ngo/students` — register student with name, age, grade, school, guardian, program
- Auto-generate `scholarship_id` (format: `EDU-{YEAR}-{XXXXX}`)
- Initialize `wallet_balance = 0`, `total_received = 0`
- `GET /api/ngo/students` — list with program info
- `GET /api/ngo/students/{id}` — detail with wallet
- Response matches `students[]` shape
- **Deliverable:** Register student → get back scholarship ID

#### Task 2.7 — NGO: Student Application Management
- `GET /api/ngo/applications` — list pending applications for NGO's programs
- `PATCH /api/ngo/applications/{id}/accept` — accept → create student record + scholarship ID
- `PATCH /api/ngo/applications/{id}/reject` — reject with reason
- **Deliverable:** Accept/Reject student applications
  
#### Task 2.8 — NGO: Invoice Management
- `GET /api/ngo/invoices` — list invoices from schools for own programs
- `PATCH /api/ngo/invoices/{id}/approve` — approve + set approved_date
- `PATCH /api/ngo/invoices/{id}/reject` — reject
- Response matches `invoices[]` shape
- **Deliverable:** NGO can review and approve/reject invoices

#### Task 2.9 — NGO: Fund Allocation
- `POST /api/ngo/allocations` — allocate funds to student or program
- `GET /api/ngo/allocations` — list allocation history
- Update `wallet_balance` and `total_received` on student
- Update `allocated` on program
- **Deliverable:** Fund allocation reflected in student wallet and program stats

#### Task 2.10 — NGO: Receipts & Documents
- `POST /api/ngo/receipts` — create receipt with file attachment
- `GET /api/ngo/receipts` — list receipts
- **Deliverable:** Create and retrieve receipts

#### Task 2.11 — Donor: Browse & Discover
- `GET /api/donor/browse/ngos` — verified NGOs with stats
- `GET /api/donor/browse/programs` — active programs with NGO info
- `GET /api/donor/browse/students` — students available for direct support
- Public-compatible shapes matching `ngos[]`, `programs[]`, `students[]`
- **Deliverable:** Donor can browse all entities

#### Task 2.12 — Donor: Donation Flow
- `POST /api/donor/donate` — body: `{ngo_id, program_id?, student_id?, amount, type, name, email, message}`
- Record donation in DB
- Update `total_donated` and `donations_count` on donor
- Update `total_funded` on NGO
- Create activity log entry
- **Deliverable:** Donor can make a donation, donation recorded  

#### Task 2.13 — Donor: Donation Tracking
- `GET /api/donor/donations` — own donation history
- `GET /api/donor/donations/{id}` — detail with fund allocation trail
- Response matches `donations[]` shape
- **Deliverable:** Donor can track their donations

#### Task 2.14 — School: Registration
- `POST /api/schools/register` — register with name, location, partner docs
- `GET /api/schools/profile` — own profile
- Status defaults to `pending` until admin/NGO verifies
- Response matches `schools[]` shape
- **Deliverable:** School can register as partner

#### Task 2.15 — School: Invoice Submission
- `POST /api/schools/invoices` — submit with NGO, program, category, line items, supporting doc
- `GET /api/schools/invoices` — own invoices with status
- Response matches `invoices[]` shape
- **Deliverable:** School can submit and track invoices

#### Task 2.16 — Student: Scholarship Application
- `GET /api/student/programs` — browse active programs with spots remaining
- `POST /api/student/apply` — submit application (name, age, grade, school, guardian, reason, program_id)
- `GET /api/student/applications` — own application statuses
- **Deliverable:** Student can apply and track application status

#### Task 2.17 — Public: Transparency Dashboard
- `GET /api/public/stats` — aggregate stats matching `platformStats` shape
- `GET /api/public/activity` — recent activity feed matching `recentActivity[]` shape
- `GET /api/public/ngos` — verified NGOs (limited fields)
- `GET /api/public/programs` — active programs (limited fields)
- **Deliverable:** Public-facing transparency data available

---

### PHASE 3: Blockchain Integration

#### Task 3.1 — Sui Project Scaffolding
- Initialize Move project under `contracts/`
- Define package structure: `sources/scholarship.move`
- Set up local Sui config and test keys
- **Deliverable:** `sui move build` succeeds

#### Task 3.2 — Scholarship Wallet Contract
- Implement `ScholarshipWallet` object (student_id, balance)
- `create_wallet()` — creates wallet owned by platform
- `deposit()` — adds funds to wallet
- `get_balance()` — reads balance
- Unit tests in Move
- **Deliverable:** Wallet creation and deposit tested on localnet

#### Task 3.3 — Donation Escrow Contract
- Implement `ProgramEscrow` object (program_id, balance)
- `create_escrow()` — creates escrow for a program
- `donate()` — deposits SUI tokens into escrow
- `allocate()` — transfers from escrow to student wallet
- Unit tests in Move
- **Deliverable:** Donation → escrow → allocation flow tested

#### Task 3.4 — Invoice Settlement Contract
- `settle_invoice()` — transfers from escrow to school address
- Emits settlement event with invoice_id
- Unit tests
- **Deliverable:** Invoice settlement on-chain tested

#### Task 3.5 — Python ↔ Sui Integration Layer
- Create `app/services/sui_service.py`
- Functions: `create_wallet()`, `donate()`, `allocate()`, `settle_invoice()`, `get_balance()`
- Sign & submit transactions from backend wallet
- Store `tx_hash` + `object_id` in DB
- **Deliverable:** Python service can call all contract functions

#### Task 3.6 — Wire Blockchain into API Endpoints
- Donation endpoint → also calls `sui_service.donate()`
- Student registration → calls `sui_service.create_wallet()`
- Fund allocation → calls `sui_service.allocate()`
- Invoice approval → calls `sui_service.settle_invoice()`
- Store tx references, gracefully degrade if chain unavailable
- **Deliverable:** All financial flows have on-chain component

#### Task 3.7 — On-chain ↔ Off-chain Sync Job
- Background task (Celery or asyncio) to verify DB state matches chain state
- Flag discrepancies for admin review
- **Deliverable:** Sync job runs and reports mismatches

---

### PHASE 4: Integration & Polish

#### Task 4.1 — Seed Data Script
- Create `scripts/seed.py` that populates DB with data matching `mock.js`
- All 5 NGOs, 5 programs, 5 students, 5 donors, 7 donations, 4 invoices, 4 schools
- **Deliverable:** `python scripts/seed.py` populates identical data to FE mock

#### Task 4.2 — CORS & Frontend Integration Config
- Configure CORS to allow the FE dev server origin
- Ensure all API responses use camelCase (matching FE expectations)
- Test with the running FE (no FE code changes)
- **Deliverable:** FE can call BE APIs without CORS errors

#### Task 4.3 — API Documentation
- Auto-generated OpenAPI spec via FastAPI `/docs`
- Add descriptions to all endpoints
- **Deliverable:** Swagger UI accessible at `/docs`

#### Task 4.4 — Error Handling & Validation
- Global exception handler with consistent error format
- Input validation via Pydantic (400 errors)
- Auth errors (401), permission errors (403), not-found (404)
- **Deliverable:** All error cases return consistent JSON

#### Task 4.5 — Activity Logging Service
- Centralized service that logs every significant action
- Auto-generates activity feed entries for the public dashboard
- **Deliverable:** All user actions create activity log entries

#### Task 4.6 — Pagination & Filtering
- Add pagination (`?page=&limit=`) to all list endpoints
- Add filtering by status, date range, category where applicable
- **Deliverable:** FE pagination/filtering works

#### Task 4.7 — Automated Tests
- Unit tests for all services (pytest)
- Integration tests for API endpoints (httpx + pytest)
- Contract tests verifying response shapes match FE expectations
- **Deliverable:** `pytest` passes with >80% coverage

#### Task 4.8 — Deployment Configuration
- Production Docker Compose (app + PG + Redis)
- Environment-based config (dev/staging/prod)
- Nginx reverse proxy config
- **Deliverable:** `docker compose up` launches full stack

---

## 7. FE ↔ BE Contract Summary

The FE currently imports mock data from `src/data/mock.js`. The migration path:
1. BE seeds data matching mock shape exactly
2. FE data layer swapped from static imports → `fetch()` calls (out of scope — no FE changes)
3. All API responses use camelCase keys to match JS conventions

> **Constraint:** ZERO frontend code changes. The BE must produce responses whose shape is an exact superset of the mock data structures.

---

## 8. Non-Functional Requirements

| Requirement | Target |
|------------|--------|
| API response time | < 200ms (p95) |
| Concurrent users | 100+ (pilot) |
| Data encryption | HTTPS, bcrypt passwords, encrypted PII at rest |
| Blockchain finality | < 3s (Sui) |
| Uptime | 99.5% |
| Audit trail | All fund movements logged on-chain + off-chain |

---

## 9. Out of Scope (v1)

- Zero-knowledge proof integration for privacy-preserving enrollment (future)
- Mobile app / teacher verification tools
- EMIS integration
- Payment gateway (credit card processing — donations use SUI tokens)
- Early warning system for at-risk students
- Multi-language support