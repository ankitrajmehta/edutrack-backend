# PRD: EduTrack — Transparent Child Benefit Delivery Platform (Backend)

## Overview

EduTrack is a blockchain-powered scholarship and education benefit delivery platform for Nepal. It connects NGOs, donors, schools, students, and system administrators to ensure education funds are transparently allocated, tracked, and delivered.

**The backend provides:**
- REST API layer serving the existing EduTrack frontend (NO frontend changes allowed)
- Business logic for 6 user roles (Admin, NGO, Donor, School, Student, Public)
- Sui blockchain smart contract integration for on-chain fund management
- Data persistence and file storage
- JWT authentication and role-based access control

**Tech Stack:** Python (FastAPI), PostgreSQL, SQLAlchemy async + Alembic, Sui Move smart contracts, JWT auth, Docker Compose.

**Critical Constraint:** All API responses must match the data shapes in the FE `edutrack/src/data/mock.js` file. The FE must not be modified.

### User Roles

| Role | Description |
|------|-------------|
| System Admin | Verifies/blacklists NGOs and student accounts. Views platform-wide stats. |
| NGO / Program Admin | Manages scholarship programs, students, invoices, fund allocation. |
| Donor | Browses NGOs/programs, donates funds. |
| School | Registers as partner, submits invoices for fund claims. |
| Student | Applies for scholarship programs. |
| Public | Views aggregate platform stats (unauthenticated). |

### Data Models (from FE mock.js)

- **NGO**: id, name, location, status, description, taxDoc, regDoc, avatar, color, totalFunded, studentsHelped, programsCount, registeredDate, programs[]
- **Program**: id, ngoId, name, description, status, categories[], totalBudget, allocated, studentsEnrolled, startDate, endDate
- **Student**: id, name, age, school, grade, guardian, programId, ngoId, scholarshipId (EDU-YYYY-XXXXX), walletBalance, totalReceived, status, location
- **Donor**: id, name, email, totalDonated, donations (count)
- **Donation**: id, donorId, ngoId, programId?, studentId?, amount, date, type (general|program|student), message?, txHash
- **Invoice**: id, schoolId, schoolName, ngoId, programId, amount, category, status, items[{desc, amount}], date, approvedDate, supportingDoc
- **School**: id, name, location, status, studentsInPrograms, totalInvoiced
- **ScholarshipApplication**: id, studentName, age, grade, schoolName, schoolDistrict, guardianName, guardianRelation, guardianContact, reason, programId, status, appliedDate
- **ActivityLog**: id, type, text, timestamp, actorId
- **PlatformStats**: totalDonations, totalStudents, totalNGOs, totalPrograms, totalSchools, fundsAllocated, fundsUtilized

---

## Task 1: Project Scaffolding
Initialize the Python/FastAPI project structure.
- Create `app/` with subfolders: `api/`, `models/`, `schemas/`, `services/`, `core/`
- `app/core/config.py` — Pydantic BaseSettings loading from `.env`
- `app/main.py` — FastAPI app with CORS middleware
- `pyproject.toml` or `requirements.txt` with deps: fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, alembic, pydantic, python-jose, passlib, python-multipart
- `Dockerfile` + `docker-compose.yml` (app + PostgreSQL)
- `.env.example` with all required vars
- Health check endpoint: `GET /api/health` → `{"status": "ok"}`

## Task 2: Database Setup & Migrations
Configure SQLAlchemy async engine and Alembic.
- `app/core/database.py` — async engine, session factory, Base declarative
- Initialize Alembic with async template
- `alembic/env.py` configured for async
- Create and run initial (empty) migration
- Verify: `alembic upgrade head` succeeds

## Task 3: Core Data Models
Implement all SQLAlchemy models matching the data shapes in the Overview.
- Models for: User, NGO, Program, Student, Donor, Donation, Invoice, School, ScholarshipApplication, ActivityLog
- All foreign key relationships (NGO↔Programs, Program↔Students, etc.)
- Enum types for statuses (pending|verified|rejected, active|completed, etc.)
- Create Alembic migration for all tables
- Verify: all tables created in PostgreSQL

## Task 4: Pydantic Schemas
Create Pydantic v2 request/response schemas for all entities.
- Separate Create, Update, and Response schemas per entity
- Response schemas must use camelCase aliases matching FE mock.js field names
- Schema for paginated list responses: `{items: [], total, page, limit}`
- Verify: schema validation tests pass

## Task 5: Authentication System
Implement JWT-based auth with role-based access control.
- Password hashing with bcrypt
- JWT access tokens (30min) + refresh tokens (7d)
- `POST /api/auth/register` — register with role (ngo, donor, school, student)
- `POST /api/auth/login` → returns access + refresh tokens
- `POST /api/auth/refresh` → new access token
- `POST /api/auth/logout` → invalidate token
- `GET /api/auth/me` → current user profile
- `get_current_user` FastAPI dependency
- `require_role("admin")` decorator/dependency
- Verify: register → login → access protected route end-to-end

## Task 6: File Upload Service
Implement file upload for documents (tax docs, registration docs, invoices, supporting documents).
- `app/services/file_service.py` — save to local disk, return metadata
- `POST /api/files/upload` → stores file, returns file ID + URL
- `GET /api/files/{id}` → download file
- Store file metadata (name, type, size, path) in DB
- Verify: upload PDF, retrieve by ID

## Task 7: Admin Dashboard & Stats API
Implement system admin dashboard endpoint.
- `GET /api/admin/dashboard` — returns aggregated stats:
  - Pending/verified/rejected NGO counts
  - Total schools, students, programs
  - Total funds processed, funds allocated, funds utilized, utilization %
- Response must match `platformStats` shape from mock.js
- Requires admin role
- Verify: returns correct aggregate JSON

## Task 8: Admin NGO Verification & Blacklisting
Implement NGO management endpoints for system admin.
- `GET /api/admin/ngos?status=pending|verified|rejected` — list with filter
- `PATCH /api/admin/ngos/{id}/verify` — set status → verified
- `PATCH /api/admin/ngos/{id}/reject` — set status → rejected
- `PATCH /api/admin/ngos/{id}/blacklist` — set status → blacklisted
- `PATCH /api/admin/ngos/{id}/restore` — restore to verified
- Create ActivityLog entry on each action
- Requires admin role
- Verify: admin can verify, reject, blacklist, and restore NGOs

## Task 9: Admin Student & Blacklist Management
Implement student blacklisting and combined blacklist view.
- `PATCH /api/admin/students/{id}/blacklist` — blacklist student
- `PATCH /api/admin/students/{id}/restore` — restore student
- `GET /api/admin/blacklist` — combined list of blacklisted NGOs + students
- Create ActivityLog entry on each action
- Requires admin role
- Verify: blacklist/restore students, view combined blacklist

## Task 10: NGO Registration & Profile
Implement NGO account creation and profile retrieval.
- `POST /api/auth/register` (type=ngo) — creates org with name, location, description, tax_doc upload, reg_doc upload
- NGO defaults to status=pending
- `GET /api/auth/me` (when role=ngo) — returns full NGO profile
- Response matches `ngos[]` shape from mock.js
- Verify: NGO registers with docs, profile returns correct shape

## Task 11: NGO Program CRUD
Implement scholarship program management.
- `POST /api/ngo/programs` — create with name, description, categories[], totalBudget, startDate, endDate
- `GET /api/ngo/programs` — list own programs
- `GET /api/ngo/programs/{id}` — program detail
- `PUT /api/ngo/programs/{id}` — update program
- Auto-set status=active on create, track studentsEnrolled and allocated
- Response matches `programs[]` shape from mock.js
- Requires ngo role
- Verify: create, list, get, update program lifecycle

## Task 12: NGO Student Registration
Implement student registration with scholarship ID generation.
- `POST /api/ngo/students` — register with name, age, grade, school, guardian, location, programId
- Auto-generate scholarshipId: `EDU-{YEAR}-{XXXXX}` (zero-padded sequential)
- Initialize walletBalance=0, totalReceived=0, status=active
- Increment studentsEnrolled on program
- `GET /api/ngo/students` — list students for this NGO
- `GET /api/ngo/students/{id}` — student detail with wallet info
- Response matches `students[]` shape from mock.js
- Requires ngo role
- Verify: register student → get scholarship ID, list students

## Task 13: NGO Application Management
Implement student application review.
- `GET /api/ngo/applications` — list pending applications for this NGO's programs
- `PATCH /api/ngo/applications/{id}/accept` — accept → automatically registers student (Task 12 logic) + generates scholarship ID
- `PATCH /api/ngo/applications/{id}/reject` — reject with optional reason
- Create ActivityLog on accept/reject
- Requires ngo role
- Verify: accept application → student auto-created with ID

## Task 14: NGO Invoice Management
Implement invoice review by NGOs.
- `GET /api/ngo/invoices` — list invoices from schools for this NGO's programs
- `PATCH /api/ngo/invoices/{id}/approve` — set status=approved, approvedDate=now
- `PATCH /api/ngo/invoices/{id}/reject` — set status=rejected
- Create ActivityLog entry
- Requires ngo role
- Verify: list, approve, reject invoices

## Task 15: NGO Fund Allocation
Implement fund distribution from NGO to students/programs.
- `POST /api/ngo/allocations` — body: {programId, studentId?, amount}
- When targeting student: increment student.walletBalance + student.totalReceived
- Always: increment program.allocated
- `GET /api/ngo/allocations` — list allocation history
- Create ActivityLog entry
- Requires ngo role
- Verify: allocate funds → student wallet updated, program allocated updated

## Task 16: NGO Receipts & Documents
Implement receipt creation with supporting document uploads.
- `POST /api/ngo/receipts` — create receipt with description, amount, file attachment
- `GET /api/ngo/receipts` — list receipts
- Requires ngo role
- Verify: create receipt with doc, list receipts

## Task 17: Donor Browse & Discovery
Implement browsing endpoints for donors.
- `GET /api/donor/browse/ngos` — list verified NGOs with stats (totalFunded, studentsHelped, programsCount)
- `GET /api/donor/browse/programs` — list active programs with NGO info
- `GET /api/donor/browse/students` — list active students for direct donation
- Response shapes match mock.js arrays
- Requires donor role
- Verify: donor can browse all three entity types

## Task 18: Donor Donation Flow
Implement donation creation.
- `POST /api/donor/donate` — body: {ngoId, programId?, studentId?, amount, type (general|program|student), name, email, message?}
- Record donation in DB with date=now
- Update donor.totalDonated + donor.donations count
- Update ngo.totalFunded
- Create ActivityLog entry
- Requires donor role
- Verify: create donation → donor stats updated, NGO stats updated

## Task 19: Donor Donation Tracking
Implement donation history and details.
- `GET /api/donor/donations` — list own donations with program/NGO names
- `GET /api/donor/donations/{id}` — detail with fund allocation trail
- Response matches `donations[]` shape from mock.js
- Requires donor role
- Verify: list and view donation details

## Task 20: School Registration
Implement school partner registration.
- `POST /api/schools/register` — register with name, location, partner documents
- Defaults to status=pending
- `GET /api/schools/profile` — own school profile
- Response matches `schools[]` shape from mock.js
- Requires school role
- Verify: school registers, profile returns correct shape

## Task 21: School Invoice Submission
Implement invoice creation and tracking for schools.
- `POST /api/schools/invoices` — body: {ngoId, programId, category, items[{desc, amount}], supportingDoc (file)}
- Total amount auto-calculated from line items
- Status defaults to pending
- `GET /api/schools/invoices` — list own invoices with status
- `POST /api/schools/invoices/{id}/documents` — upload additional supporting doc
- Response matches `invoices[]` shape from mock.js
- Requires school role
- Verify: submit invoice with line items, view with status

## Task 22: Student Scholarship Application
Implement student application flow.
- `GET /api/student/programs` — browse active programs with spots remaining (cap - studentsEnrolled)
- `POST /api/student/apply` — body: {programId, fullName, age, grade, schoolName, schoolDistrict, guardianName, guardianRelation, guardianContact, reason}
- Status defaults to pending
- `GET /api/student/applications` — own applications with status (pending|accepted|rejected)
- Requires student role
- Verify: student applies, can see application status

## Task 23: Public Transparency Dashboard API
Implement unauthenticated public-facing endpoints.
- `GET /api/public/stats` — aggregate stats matching `platformStats` shape
- `GET /api/public/activity` — recent activity feed matching `recentActivity[]` shape (type, color, text, time)
- `GET /api/public/ngos` — verified NGOs (limited public fields)
- `GET /api/public/programs` — active programs (limited public fields)
- No auth required
- Verify: all 4 endpoints return correct shapes without authentication

## Task 24: Activity Logging Service
Implement centralized activity logging used by all other tasks.
- `app/services/activity_service.py` — `log_activity(type, text, actor_id)`
- Types: donation, invoice, verify, allocation, program, blacklist
- Auto-generates human-readable text (e.g., "Sarah Mitchell donated $2,500 to Mountain Girls Scholarship")
- Relative time formatting for activity feed ("2 hours ago", "1 day ago")
- Called from Tasks 8, 9, 13, 14, 15, 18
- Verify: actions produce correctly formatted activity log entries

## Task 25: Seed Data Script
Create a script that populates the DB with data matching the FE mock.js exactly.
- `scripts/seed.py` — inserts all mock data: 5 NGOs, 5 programs, 5 students, 5 donors, 7 donations, 4 invoices, 4 schools, 8 activity entries, platform stats
- All IDs, field values, and relationships must match mock.js
- Idempotent (can be re-run safely)
- Verify: `python scripts/seed.py` → API returns data identical to mock.js

## Task 26: CORS, camelCase & Frontend Integration
Configure the backend to work with the existing FE dev server.
- CORS middleware allowing FE origin (localhost:5173 or configurable)
- All JSON responses use camelCase keys (matching JS conventions in mock.js)
- Test: FE can call BE APIs without CORS errors
- Verify: run FE + BE simultaneously, confirm no CORS issues

## Task 27: Pagination, Filtering & Error Handling
Add pagination and filtering to all list endpoints, plus consistent error handling.
- All list endpoints support `?page=1&limit=20`
- Status filters on NGO, program, invoice, school lists
- Date range filter on donations, invoices
- Global exception handler → consistent error JSON: `{detail, status_code}`
- 400 (validation), 401 (auth), 403 (permission), 404 (not found)
- Verify: pagination params work, error responses are consistent

## Task 28: Sui Move Contract — Scholarship Wallets & Escrow
Write the core Sui Move smart contract.
- Initialize Move project under `contracts/`
- `ScholarshipWallet` object: student_id, balance
- `ProgramEscrow` object: program_id, balance
- Functions: `create_wallet()`, `create_escrow()`, `donate()` (deposit to escrow), `allocate()` (escrow→wallet), `settle_invoice()` (escrow→school), `get_balance()`
- Emits events for all fund movements
- Unit tests in Move
- Verify: `sui move build` + `sui move test` pass

## Task 29: Python Sui Integration Service
Create the Python service layer that calls the Sui contract.
- `app/services/sui_service.py` — wraps all contract calls
- Functions: `create_wallet()`, `donate()`, `allocate_funds()`, `settle_invoice()`, `get_balance()`, `get_tx_history()`
- Signs and submits transactions from backend wallet
- Stores tx_hash + object_id in DB alongside off-chain records
- Graceful degradation if Sui is unavailable (log warning, continue off-chain only)
- Verify: Python can call all contract functions on devnet/testnet

## Task 30: Wire Blockchain into API Endpoints
Connect Sui operations to the existing API endpoints.
- Student registration (Task 12) → also calls `sui_service.create_wallet()`
- Donation (Task 18) → also calls `sui_service.donate()`
- Fund allocation (Task 15) → also calls `sui_service.allocate_funds()`
- Invoice approval (Task 14) → also calls `sui_service.settle_invoice()`
- All tx_hash values stored and returned in API responses
- Verify: financial flows produce on-chain transactions

## Task 31: Automated Tests
Write comprehensive tests for the backend.
- Unit tests for all service functions (pytest)
- Integration tests for all API endpoints (httpx async client + pytest)
- Contract tests verifying API response shapes match FE mock.js expectations
- Test auth flows, permission checks, edge cases
- Verify: `pytest` passes with >80% coverage

## Task 32: Deployment Configuration
Finalize production-ready deployment setup.
- Production `docker-compose.prod.yml` (app + PG)
- Multi-stage Dockerfile (build + runtime)
- Environment-based config (dev/staging/prod)
- `scripts/start.sh` — runs migrations + seeds + starts uvicorn
- README.md with setup, run, and deployment instructions
- Verify: `docker compose up` launches the full stack successfully