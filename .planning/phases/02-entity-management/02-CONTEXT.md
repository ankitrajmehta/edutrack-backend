# Phase 2: Entity Management - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Every stakeholder (Admin, NGO, Donor, School, Student) can manage their entities through scoped, role-enforced CRUD endpoints, with activity logging and file storage operational — all responses in camelCase matching mock.js.

**Delivers:**
- Admin: dashboard stats, NGO list (filter by status), verify/reject/blacklist/restore NGO, combined blacklist view, blacklist/restore student
- NGO: dashboard stats, program CRUD (own programs only), student registration (generates scholarship ID + mock wallet), student list/detail, application review (accept → auto-create student, reject with reason), allocation history view
- Donor: browse verified NGOs, browse active programs, browse students
- School: register as partner, view own profile
- Student: browse active programs, submit scholarship application, view own application statuses
- Activity logging: every significant action writes an ActivityLog entry in the same DB transaction
- File upload/download: multipart upload → `{fileId, url}`; download by ID

**Out of scope for this phase:**
- Invoice submission (SCHL-03–04) and approval (NGO-08–09) — Phase 3 (blockchain tx involved)
- Donation endpoints (DONOR-04–06) — Phase 3 (blockchain tx involved)
- Fund allocation (NGO-10–11) — Phase 3
- Public endpoints (`/api/public/*`) — Phase 4
- Activity feed public shape (relative time strings) — Phase 4 (ACTV-02)
- Seed script — Phase 4

</domain>

<decisions>
## Implementation Decisions

### File Upload Scope and Access Control
- **Upload (`POST /api/files/upload`):** Any authenticated user can upload — no role restriction at the file service level
- **Download (`GET /api/files/{id}`):** Any authenticated user with the file ID can download
- **Storage backend:** Local disk with S3-compatible interface — preserves v2 drop-in path to MinIO/S3; do NOT store in DB (abandons the interface goal)
- **Folder structure:** Organized by role: `/uploads/ngo/`, `/uploads/school/`, `/uploads/misc/` (other roles fall into misc)
- **Attachment pattern:** Decoupled — `POST /api/files/upload` returns `{fileId, url}` only; the caller then attaches the returned file ID to an entity field (e.g., `tax_doc`, `reg_doc`, `supporting_doc`) in a separate create/update request
- **Async I/O:** Use `aiofiles` for all disk reads/writes — no blocking `open()` calls in async context (FILE-03 requirement)

### Scholarship ID + Wallet on Student Registration
- **ID generation:** `EDU-{YYYY}-{XXXXX}` where `YYYY` = current year and `XXXXX` = zero-padded 5-digit random number; generated in service layer before DB insert
- **Wallet creation:** Call `blockchain.create_wallet(student_id)` via `Depends(get_blockchain)` after the student row is created and flushed (so `student.id` is available); store the returned `wallet_address` on the student record
- **Failure handling:** If the mock blockchain call fails, roll back the entire transaction — student is not created with a null wallet. The mock should not fail in practice, but the service must treat it atomically.
- **Two creation paths:** Direct registration by NGO (`POST /api/ngo/students`) and auto-create from accepted application (`PATCH /api/ngo/applications/{id}/accept`) — both use the same internal `_create_student()` helper to ensure identical ID generation + wallet creation logic
- **Uniqueness:** Scholarship ID must be unique; on collision (extremely rare), regenerate before insert

### Activity Logging per Action
- **Writer:** `activity_service.log(db, type, text, actor_id)` called inside the service method, before `db.commit()` — atomicity with the triggering action
- **Event types and text format:**
  - NGO verified: `type="verify"`, text=`"NGO '{name}' verified"`
  - NGO rejected: `type="verify"`, text=`"NGO '{name}' rejected"`
  - NGO blacklisted: `type="blacklist"`, text=`"NGO '{name}' blacklisted"`
  - Student blacklisted: `type="blacklist"`, text=`"Student '{name}' blacklisted"`
  - Program created: `type="program"`, text=`"Program '{name}' created by {ngo_name}"`
  - Student registered: `type="allocation"`, text=`"Student '{name}' enrolled in {program_name}"`
  - Application accepted: `type="program"`, text=`"Application from '{student_name}' accepted into '{program_name}'"`
  - Application rejected: `type="program"`, text=`"Application from '{student_name}' rejected"`
- **actor_id:** The authenticated user's `user.id` passed to every service method — never null
- **Color field:** ActivityLog has a `color` field (used in Phase 4 public feed); set a sensible default per type (e.g., verify=green, blacklist=red, program=blue, allocation=purple) so Phase 4 doesn't need a migration

### Application → Student Auto-Create Rules
- **Fields carried over from ScholarshipApplication to Student:**
  - `student_name` → `Student.name`
  - `age` → `Student.age`
  - `grade` → `Student.grade`
  - `school_name` → `Student.school`
  - `guardian_name` → `Student.guardian`
  - `school_district` → `Student.location`
  - `program_id` → `Student.program_id`
  - NGO derived from `Program.ngo_id` → `Student.ngo_id`
- **No User account created:** The accepted applicant becomes a Student record only — no auth user row. The student's scholarship program manages their record; they don't log into the system via this path.
- **Application status:** Set to `accepted`; the auto-created student record is linked by ID in the application row (add `student_id` FK reference if not already on the model, or log the association in the activity log)
- **Rejection:** `PATCH /api/ngo/applications/{id}/reject` sets status to `rejected`; a `reason` string in the request body is stored (add `rejection_reason` column to ScholarshipApplication if not present)

### RBAC Ownership Scoping (carried from Phase 1 design)
- NGO service methods receive `current_ngo` (the NGO profile of the logged-in user), not just `user_id` — ownership check is `record.ngo_id == current_ngo.id`; HTTP 403 if mismatch
- School service: `current_school` injected; scope checks on profile and invoice views
- Student service: browse and apply are open to any authenticated student; own application list filtered by matching `student_name` or linked user (clarify in planning — student role may not have a Student ORM row linked to their user until they're enrolled)
- Donor service: browse endpoints (NGOs, programs, students) are read-only; no ownership scoping needed for Phase 2 (donation history is Phase 3)

### Response Schema Conventions (carried from Phase 1)
- All response schemas inherit `BaseResponse` (`from_attributes=True`, `populate_by_name=True`)
- All snake_case fields aliased to camelCase matching mock.js exactly
- Services return Pydantic model instances — never raw dicts (camelCase aliases only fire on Pydantic serialization)
- `selectinload()` for one-to-many, `joinedload()` for many-to-one — never default lazy loading

### Claude's Discretion
- Exact activity log color values per type (as long as they're set, not null)
- Whether `rejection_reason` is a new column or just logged in activity text
- Exact scholarship ID collision retry logic (simple re-roll is fine)
- Admin dashboard stat computation queries (straightforward COUNT/SUM aggregations)
- Order of items in list responses (default to DB insertion order for Phase 2; ordering is a v2 concern)

</decisions>

<specifics>
## Specific Ideas

- `tasks.md` and `prompt.md` define the exact implementation order and patterns — planner should reference these
- mock.js field names are the ground truth for camelCase aliases — researcher must verify exact field names (e.g., `scholarshipId`, `walletAddress`, `createdAt`) before finalizing schemas
- The grant demo is for UNICEF Venture Fund (March 2026) — all responses must look production-grade, not demo-quality
- Phase 2 is the largest phase (30 requirements) — plan should break it into logical sub-plans by role group (e.g., Admin endpoints, NGO endpoints, Donor/School/Student endpoints, File service)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/schemas/common.py`: `BaseResponse` (all response schemas inherit this — do not redefine)
- `app/schemas/ngo.py`: `NGOCreate`, `NGOUpdate`, `NGOResponse` — already scaffolded with camelCase aliases; verify against mock.js before using
- `app/schemas/student.py`: `StudentCreate`, `StudentResponse` — scaffolded; `scholarshipId` and `walletAddress` aliases already defined
- `app/schemas/program.py`: `ProgramCreate`, `ProgramUpdate`, `ProgramResponse` — scaffolded with camelCase aliases
- `app/schemas/application.py`: exists as stub — needs `ApplicationResponse` with status field
- `app/services/activity_service.py`: stub — Phase 2 implements the `log()` function here
- `app/services/ngo_service.py`, `admin_service.py`, `donor_service.py`, `school_service.py`, `student_service.py`, `file_service.py`: all stubs with docstring `"implemented in Plan 02"`
- `app/api/ngo.py`, `admin.py`, `donor.py`, `files.py`, `school.py`, `student.py`: all empty routers registered in `main.py` — Phase 2 fills these in
- `app/core/dependencies.py`: `get_db`, `get_current_user`, `require_role`, `get_blockchain` — all available for injection
- `uploads/` directory: already exists on disk — file storage target ready

### Established Patterns
- **Route handler pattern:** `async def handler(data: Schema, user = Depends(require_role("ngo")), db = Depends(get_db)) -> ResponseSchema` — one service call, return result
- **Service pattern:** fetch → validate ownership → mutate → `activity_service.log()` → `db.commit()` → return Pydantic model instance
- **Error pattern:** raise `NotFoundError` / `ForbiddenError` / `ConflictError` — global handler in `main.py` converts to `{detail, code, statusCode}`
- **Auth pattern:** `auth_service.py` shows the full register flow including `db.flush()` before `db.commit()` for getting IDs — replicate in student creation
- **Relationship loading:** `selectinload()` for `NGO.programs`, `NGO.students`; `joinedload()` for `Student.ngo`, `Student.program` — already configured on ORM models

### Integration Points
- `app/main.py`: all 8 routers already registered under `/api` prefix — Phase 2 just fills in the route handlers
- `app/core/dependencies.py`: `get_blockchain()` already returns `MockSuiBlockchain` — call `await blockchain.create_wallet(student_id)` in student creation service
- `app/models/__init__.py`: all 11 ORM models already imported — no new models needed for Phase 2
- `alembic/`: migrations complete from Phase 1 — if `rejection_reason` or `color` columns are added to models, a new migration is required

</code_context>

<deferred>
## Deferred Ideas

- Storing files in the database (BYTEA) — considered but rejected to preserve S3-compatible interface for v2 production path
- Pagination on list endpoints — v2 concern (PAGE-V2-01); Phase 2 returns all records
- Student user account creation on application acceptance — no auth flow for students in v1; student record only

</deferred>

---

*Phase: 02-entity-management*
*Context gathered: 2026-03-09*
