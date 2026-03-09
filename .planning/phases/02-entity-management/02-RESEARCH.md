# Phase 2: Entity Management — Research

**Phase:** 02-entity-management
**Researched:** 2026-03-09
**Requirements:** RBAC-02–05, ADMN-01–05, NGO-01–07, DONOR-01–03, SCHL-01–02, STUD-01–03, ACTV-01, FILE-01–03, APIC-01–02

---

## Standard Stack (Already Established in Phase 1)

All of these are in place — no new dependencies needed for Phase 2:

| Concern | Solution | Location |
|---------|----------|----------|
| Async DB | `AsyncSession` via `get_db` | `app/core/database.py` |
| Auth injection | `get_current_user`, `require_role` | `app/core/dependencies.py` |
| Blockchain | `MockSuiService` via `get_blockchain` | `app/core/dependencies.py` |
| Error format | `NotFoundError`, `ForbiddenError`, `ConflictError` | `app/core/exceptions.py` |
| Response base | `BaseResponse` (from_attributes + populate_by_name) | `app/schemas/common.py` |
| ORM loading | `selectinload()` / `joinedload()` | Already configured on all models |
| File storage | `uploads/` directory exists | disk, aiofiles needed |

**New pip install required:** `aiofiles` for async file I/O (FILE-03). All other tools already in `requirements.txt`.

---

## Architecture Patterns (Carry Exactly From Phase 1)

### Route Handler Pattern
```python
@router.post("/programs", response_model=ProgramResponse, status_code=201)
async def create_program(
    data: ProgramCreate,
    current_user=Depends(require_role("ngo")),
    db: AsyncSession = Depends(get_db),
) -> ProgramResponse:
    return await ngo_service.create_program(db, data, current_user)
```
- One `Depends(require_role(...))` call
- One `await service.method(db, data, user)` call
- Return the Pydantic model instance directly
- Never call `db.commit()` in route handlers

### Service Pattern
```python
async def create_program(db: AsyncSession, data: ProgramCreate, current_user: User) -> ProgramResponse:
    # 1. Fetch current_ngo (ownership anchor)
    ngo = await _get_ngo_for_user(db, current_user.id)  # raises 404 if not found
    # 2. Validate / mutate
    program = Program(ngo_id=ngo.id, name=data.name, ...)
    db.add(program)
    await db.flush()  # get program.id before commit
    # 3. Log activity (BEFORE commit — atomicity)
    await activity_service.log(db, "program", f"Program '{program.name}' created by {ngo.name}", current_user.id)
    # 4. Commit
    await db.commit()
    # 5. Return Pydantic instance (never raw dict)
    return ProgramResponse.model_validate(program)
```

### Ownership Scoping Pattern
```python
async def _get_ngo_for_user(db: AsyncSession, user_id: int) -> NGO:
    result = await db.execute(select(NGO).where(NGO.user_id == user_id))
    ngo = result.scalar_one_or_none()
    if ngo is None:
        raise NotFoundError("NGO profile", user_id)
    return ngo

# In service method:
if program.ngo_id != ngo.id:
    raise ForbiddenError("You do not own this program")
```

### db.flush() Before db.commit() Pattern
Use `await db.flush()` whenever a newly-created object's `id` is needed before committing (e.g., student creation needs `student.id` for `blockchain.create_wallet(student.id)`). Follows auth_service.py precedent.

---

## Endpoint Inventory by Role Group

### Admin Endpoints (ADMN-01–05)

| Method | Path | Handler Returns | Requirements |
|--------|------|----------------|-------------|
| GET | `/api/admin/dashboard` | `AdminStatsResponse` | ADMN-01 |
| GET | `/api/admin/ngos` | `list[NGOResponse]` (filter `?status=`) | ADMN-02 |
| PATCH | `/api/admin/ngos/{id}/verify` | `NGOResponse` | ADMN-03 |
| PATCH | `/api/admin/ngos/{id}/reject` | `NGOResponse` | ADMN-03 |
| PATCH | `/api/admin/ngos/{id}/blacklist` | `NGOResponse` | ADMN-03 |
| PATCH | `/api/admin/ngos/{id}/restore` | `NGOResponse` | ADMN-03 |
| GET | `/api/admin/blacklist` | `BlacklistResponse` | ADMN-04 |
| PATCH | `/api/admin/students/{id}/blacklist` | `StudentResponse` | ADMN-05 |
| PATCH | `/api/admin/students/{id}/restore` | `StudentResponse` | ADMN-05 |

**AdminStatsResponse fields** (from `mock.js platformStats` + NGO count):
```python
class AdminStatsResponse(BaseResponse):
    total_donations: float = Field(alias="totalDonations")
    total_students: int = Field(alias="totalStudents")
    total_ngos: int = Field(alias="totalNGOs")
    total_programs: int = Field(alias="totalPrograms")
    total_schools: int = Field(alias="totalSchools")
    funds_allocated: float = Field(alias="fundsAllocated")
    funds_utilized: float = Field(alias="fundsUtilized")
```

**BlacklistResponse** — combined list of blacklisted NGOs and students:
```python
class BlacklistResponse(BaseResponse):
    ngos: list[NGOResponse]
    students: list[StudentResponse]
```

**Activity logs for admin actions:**
- NGO verified: `type="verify"`, `text="NGO '{name}' verified"`, color=`"blue"`
- NGO rejected: `type="verify"`, `text="NGO '{name}' rejected"`, color=`"blue"`
- NGO blacklisted: `type="blacklist"`, `text="NGO '{name}' blacklisted"`, color=`"red"`
- Student blacklisted: `type="blacklist"`, `text="Student '{name}' blacklisted"`, color=`"red"`

### NGO Endpoints (NGO-01–07)

| Method | Path | Handler Returns | Requirements |
|--------|------|----------------|-------------|
| GET | `/api/ngo/dashboard` | `NGOStatsResponse` | NGO-01 |
| POST | `/api/ngo/programs` | `ProgramResponse` (201) | NGO-02 |
| GET | `/api/ngo/programs` | `list[ProgramResponse]` | NGO-03 |
| GET | `/api/ngo/programs/{id}` | `ProgramResponse` | NGO-03 |
| PUT | `/api/ngo/programs/{id}` | `ProgramResponse` | NGO-03 |
| POST | `/api/ngo/students` | `StudentResponse` (201) | NGO-04 |
| GET | `/api/ngo/students` | `list[StudentResponse]` | NGO-05 |
| GET | `/api/ngo/students/{id}` | `StudentResponse` | NGO-05 |
| GET | `/api/ngo/applications` | `list[ApplicationResponse]` | NGO-06 |
| PATCH | `/api/ngo/applications/{id}/accept` | `StudentResponse` (201) | NGO-07 |
| PATCH | `/api/ngo/applications/{id}/reject` | `ApplicationResponse` | NGO-07 |

**NGOStatsResponse fields:**
```python
class NGOStatsResponse(BaseResponse):
    programs_count: int = Field(alias="programsCount")
    students_helped: int = Field(alias="studentsHelped")
    funds_allocated: float = Field(alias="fundsAllocated")
```

**Activity logs for NGO actions:**
- Program created: `type="program"`, `text="Program '{name}' created by {ngo_name}"`, color=`"blue"`
- Student registered: `type="allocation"`, `text="Student '{name}' enrolled in {program_name}"`, color=`"purple"`
- Application accepted: `type="program"`, `text="Application from '{student_name}' accepted into '{program_name}'"`, color=`"blue"`
- Application rejected: `type="program"`, `text="Application from '{student_name}' rejected"`, color=`"blue"`

### Donor Endpoints (DONOR-01–03)

| Method | Path | Handler Returns | Requirements |
|--------|------|----------------|-------------|
| GET | `/api/donor/browse/ngos` | `list[NGOResponse]` (verified only) | DONOR-01 |
| GET | `/api/donor/browse/programs` | `list[ProgramResponse]` (active only) | DONOR-02 |
| GET | `/api/donor/browse/students` | `list[StudentResponse]` (active only) | DONOR-03 |

All donor browse endpoints are read-only. No ownership scoping needed — return all records matching the filter condition (verified/active status).

### School Endpoints (SCHL-01–02)

| Method | Path | Handler Returns | Requirements |
|--------|------|----------------|-------------|
| POST | `/api/schools/register` | `SchoolResponse` (201) | SCHL-01 |
| GET | `/api/schools/profile` | `SchoolResponse` | SCHL-02 |

**Note:** `POST /api/schools/register` — the school user already has a `School` row created during `auth/register`. This endpoint may be a "complete profile" or "confirm partner registration" action rather than true creation. Treat as: fetch existing school record, mark as "registered" (status stays pending until admin verifies), return profile. No duplicate creation logic.

### Student Endpoints (STUD-01–03)

| Method | Path | Handler Returns | Requirements |
|--------|------|----------------|-------------|
| GET | `/api/student/programs` | `list[ProgramResponse]` (active only) | STUD-01 |
| POST | `/api/student/apply` | `ApplicationResponse` (201) | STUD-02 |
| GET | `/api/student/applications` | `list[ApplicationResponse]` | STUD-03 |

**Student application scoping:** `GET /api/student/applications` — filter by `student_name` matching. The current student user does not have a `Student` ORM row until enrolled; applications are linked by `student_name` in the submitted form. Use `student_name` from the request body that was submitted. Store `user_id` on application for v1 filtering (add optional `user_id` FK to `ScholarshipApplication` model or filter by application records created by this user via session identity). **Simplest approach for v1:** Store the submitting user's ID on the application at creation time; `GET /api/student/applications` filters by `application.submitted_by_user_id == current_user.id`.

### File Endpoints (FILE-01–03)

| Method | Path | Handler Returns | Requirements |
|--------|------|----------------|-------------|
| POST | `/api/files/upload` | `FileUploadResponse` | FILE-01, FILE-03 |
| GET | `/api/files/{id}` | `FileResponse` (FileResponse) | FILE-02 |

**FileUploadResponse:**
```python
class FileUploadResponse(BaseResponse):
    file_id: int = Field(alias="fileId")
    url: str
```

**Upload implementation pattern:**
```python
from fastapi import UploadFile, File
import aiofiles
import os, uuid

async def upload_file(db, file: UploadFile, current_user: User) -> FileUploadResponse:
    # Determine folder by role
    folder_map = {"ngo": "ngo", "school": "school"}
    folder = folder_map.get(current_user.role.value, "misc")
    upload_dir = f"uploads/{folder}"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    ext = os.path.splitext(file.filename)[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = f"{upload_dir}/{stored_name}"
    
    # Async write — NEVER use blocking open() in async context
    async with aiofiles.open(stored_path, "wb") as f:
        content = await file.read()
        await f.write(content)
    
    # Persist FileRecord
    record = FileRecord(
        original_name=file.filename,
        stored_path=stored_path,
        mime_type=file.content_type,
        size_bytes=len(content),
        uploaded_by=current_user.id,
    )
    db.add(record)
    await db.commit()
    
    return FileUploadResponse(file_id=record.id, url=f"/api/files/{record.id}")
```

**Download implementation:**
```python
from fastapi.responses import FileResponse as FastAPIFileResponse

async def download_file(db, file_id: int) -> FastAPIFileResponse:
    record = await db.get(FileRecord, file_id)
    if record is None:
        raise NotFoundError("File", file_id)
    # FastAPI FileResponse handles async streaming
    return FastAPIFileResponse(record.stored_path, filename=record.original_name)
```

**Note:** `FastAPIFileResponse` from `fastapi.responses` (not Pydantic) handles async file streaming natively — no manual `aiofiles` read needed for download.

---

## Critical Implementation Details

### 1. ActivityLog — Missing `color` Column

The `ActivityLog` ORM model currently has NO `color` column. Phase 2 requires it (set per event type; Phase 4 public feed reads it). **Must add a new Alembic migration** adding `color VARCHAR(50)` to `activity_logs`.

```python
# In activity_service.py
COLOR_MAP = {
    "verify": "blue",
    "blacklist": "red",
    "program": "blue",
    "allocation": "purple",
    "donation": "green",
    "invoice": "amber",
}

async def log(db: AsyncSession, type: str, text: str, actor_id: int) -> None:
    from app.models.activity_log import ActivityLog
    entry = ActivityLog(
        type=type,
        text=text,
        actor_id=actor_id,
        color=COLOR_MAP.get(type, "gray"),
    )
    db.add(entry)
    # DO NOT commit here — caller commits atomically with the triggering action
```

### 2. ScholarshipApplication — Missing Columns

The `ScholarshipApplication` ORM model is missing two columns needed for Phase 2:
- `rejection_reason` (`Text`, nullable) — stored when NGO rejects application
- `submitted_by_user_id` (`Integer`, FK→users.id, nullable) — stored at apply time for `GET /student/applications` filtering

**Must add a new Alembic migration** for both columns.

```python
# In application model:
rejection_reason = Column(Text, nullable=True)
submitted_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
```

### 3. Student Registration — Scholarship ID Generation

```python
import random

async def _generate_scholarship_id(db: AsyncSession) -> str:
    """Generate unique EDU-YYYY-XXXXX, retry on collision."""
    from app.models.student import Student
    year = datetime.now().year
    for _ in range(10):  # max 10 retries
        number = str(random.randint(0, 99999)).zfill(5)
        candidate = f"EDU-{year}-{number}"
        result = await db.execute(select(Student).where(Student.scholarship_id == candidate))
        if result.scalar_one_or_none() is None:
            return candidate
    raise ConflictError("scholarship_id", "generation failed after 10 retries")
```

### 4. Student Creation — Two Paths, One Helper

Both `POST /api/ngo/students` and `PATCH /api/ngo/applications/{id}/accept` must use the same `_create_student()` helper:

```python
async def _create_student(
    db: AsyncSession,
    ngo: NGO,
    name: str, age: int, school: str, grade: str,
    guardian: str, location: str, program_id: int,
    blockchain: BlockchainService,
    actor_id: int,
) -> Student:
    scholarship_id = await _generate_scholarship_id(db)
    student = Student(
        ngo_id=ngo.id,
        program_id=program_id,
        name=name, age=age, school=school, grade=grade,
        guardian=guardian, location=location,
        scholarship_id=scholarship_id,
    )
    db.add(student)
    await db.flush()  # get student.id before blockchain call
    
    # Create blockchain wallet — atomic: if this fails, student is not created
    wallet_result = await blockchain.create_wallet(str(student.id))
    student.wallet_address = wallet_result.wallet_address
    
    # Log activity BEFORE commit
    program_result = await db.get(Program, program_id)
    program_name = program_result.name if program_result else "Unknown Program"
    await activity_service.log(
        db, "allocation",
        f"Student '{name}' enrolled in {program_name}",
        actor_id,
    )
    await db.commit()
    return student
```

**Failure handling:** If `blockchain.create_wallet()` raises, the exception propagates before `db.commit()` — the session rolls back automatically. Student row is not persisted (it was only flushed, not committed).

### 5. Application Accept → Student Auto-Create Field Mapping

From `ScholarshipApplication` → `Student`:
```
application.student_name → student.name
application.age          → student.age
application.grade        → student.grade
application.school_name  → student.school
application.guardian_name → student.guardian
application.school_district → student.location
application.program_id   → student.program_id
program.ngo_id           → student.ngo_id
```

After student is created:
- Set `application.status = ApplicationStatus.accepted`
- Optionally log `application.student_id = student.id` (not in model — log via activity only)

### 6. RBAC Ownership Injection Pattern

All NGO routes get `current_ngo` derived from `current_user`:

```python
# In ngo.py router:
async def get_current_ngo(
    current_user=Depends(require_role("ngo")),
    db: AsyncSession = Depends(get_db),
) -> NGO:
    result = await db.execute(select(NGO).where(NGO.user_id == current_user.id))
    ngo = result.scalar_one_or_none()
    if ngo is None:
        raise NotFoundError("NGO profile", current_user.id)
    return ngo
```

This pattern means service methods receive a typed `NGO` object, not a raw `user_id` — ownership checks are `record.ngo_id == ngo.id`.

### 7. camelCase Response Shapes — Mock.js Field Verification

Verified against `../edutrack/src/data/mock.js`:

| Model | Field | camelCase Alias | Schema Status |
|-------|-------|----------------|---------------|
| NGO | `total_funded` | `totalFunded` | ✓ existing |
| NGO | `students_helped` | `studentsHelped` | ✓ existing |
| NGO | `programs_count` | `programsCount` | ✓ existing |
| NGO | `registered_date` | `registeredDate` | ✓ existing |
| NGO | `tax_doc` | `taxDoc` | ✓ existing |
| NGO | `reg_doc` | `regDoc` | ✓ existing |
| Student | `scholarship_id` | `scholarshipId` | ✓ existing |
| Student | `wallet_address` | `walletAddress` | ✓ existing |
| Student | `wallet_balance` | `walletBalance` | ✓ existing |
| Student | `total_received` | `totalReceived` | ✓ existing |
| Student | `program_id` | `programId` | ✓ existing |
| Student | `ngo_id` | `ngoId` | ✓ existing |
| Program | `total_budget` | `totalBudget` | ✓ existing |
| Program | `students_enrolled` | `studentsEnrolled` | ✓ existing |
| Program | `ngo_id` | `ngoId` | ✓ existing |
| Program | `start_date` | `startDate` | ✓ existing |
| Program | `end_date` | `endDate` | ✓ existing |
| Application | `program_id` | `programId` | ✓ existing |
| Application | `student_name` | `studentName` | ✓ existing |
| Application | `school_name` | `schoolName` | ✓ existing |
| Application | `school_district` | `schoolDistrict` | ✓ existing |
| Application | `guardian_name` | `guardianName` | ✓ existing |
| Application | `guardian_relation` | `guardianRelation` | ✓ existing |
| Application | `guardian_contact` | `guardianContact` | ✓ existing |
| Application | `applied_date` | `appliedDate` | ✓ existing |
| School | `students_in_programs` | `studentsInPrograms` | ✓ existing |
| School | `total_invoiced` | `totalInvoiced` | ✓ existing |
| Donor | `total_donated` | `totalDonated` | ✓ existing |
| Donor | `donations_count` | `donationsCount` | ✓ existing |
| File | `id` | `fileId` | ✗ NEW SCHEMA NEEDED |
| ActivityLog | `color` | `color` | ✗ MISSING COLUMN |
| AdminStats | `total_donations` | `totalDonations` | ✗ NEW SCHEMA NEEDED |
| AdminStats | `total_ngos` | `totalNGOs` | ✗ NEW SCHEMA NEEDED |
| AdminStats | `funds_allocated` | `fundsAllocated` | ✗ NEW SCHEMA NEEDED |
| AdminStats | `funds_utilized` | `fundsUtilized` | ✗ NEW SCHEMA NEEDED |

**Donor mock.js shape note:** `donations` field in mock is a count integer, not a list. Confirmed: `DonorResponse.donations_count` maps to mock `donations` count. The `DonorResponse` schema currently uses alias `"donationsCount"` — verify FE reads `donationsCount` not `donations`. **(Disambiguation needed in planning.)**

### 8. New Alembic Migration Required

Phase 2 needs one migration adding:
1. `color VARCHAR(50)` on `activity_logs` table
2. `rejection_reason TEXT` on `scholarship_applications` table
3. `submitted_by_user_id INTEGER REFERENCES users(id)` on `scholarship_applications` table

Use same raw SQL `op.execute()` pattern from Phase 1 (no `op.add_column` with typed enums — stay with raw SQL to avoid asyncpg issues).

---

## Plan Decomposition Strategy

Phase 2 has 30 requirements. The CONTEXT.md calls for breaking into logical sub-plans by role group. Recommended split into **5 plans**:

### Plan 01 — Foundation: activity_service + migration (Wave 1)
**Requirements:** ACTV-01, APIC-01, APIC-02
- Implement `activity_service.log()` (the one function called by ALL other services)
- New Alembic migration: add `color` to `activity_logs`, `rejection_reason` + `submitted_by_user_id` to `scholarship_applications`
- This must land before any service that calls `activity_service.log()` — all other plans depend on it
- **Files:** `app/services/activity_service.py`, `alembic/versions/0002_phase2_additions.py`

### Plan 02 — Admin Service + Routes (Wave 2, depends on 01)
**Requirements:** ADMN-01–05, RBAC-02 (partial — NGO/student ownership enforced here)
- `AdminStatsResponse`, `BlacklistResponse` schemas
- `admin_service.py`: dashboard stats (COUNT/SUM queries), NGO status mutations (verify/reject/blacklist/restore), student blacklist/restore
- `app/api/admin.py` route handlers
- Activity logging for all admin actions
- **Files:** `app/services/admin_service.py`, `app/api/admin.py`, `app/schemas/admin.py`

### Plan 03 — NGO Service + Routes (Wave 2, depends on 01)
**Requirements:** NGO-01–07, RBAC-02 (NGO ownership scoping)
- `NGOStatsResponse` schema, `get_current_ngo` dependency
- `ngo_service.py`: programs CRUD, student registration (scholarship ID + wallet), student list/detail, application list, accept/reject
- `app/api/ngo.py` route handlers
- Shared `_create_student()` helper for both direct registration and accept-application paths
- **Files:** `app/services/ngo_service.py`, `app/api/ngo.py`, `app/schemas/ngo.py` (additions)

### Plan 04 — Donor + School + Student Routes (Wave 2, depends on 01)
**Requirements:** DONOR-01–03, SCHL-01–02, STUD-01–03, RBAC-03, RBAC-04, RBAC-05
- All three are lightweight (read-heavy, minimal business logic)
- `donor_service.py`: browse NGOs/programs/students (simple filtered queries)
- `school_service.py`: register (return existing School profile), get profile
- `student_service.py`: browse active programs, submit application, list own applications
- Route files: `app/api/donor.py`, `app/api/school.py`, `app/api/student.py`
- **Files:** `app/services/donor_service.py`, `app/services/school_service.py`, `app/services/student_service.py`, `app/api/donor.py`, `app/api/school.py`, `app/api/student.py`

### Plan 05 — File Service + Routes (Wave 2, depends on 01)
**Requirements:** FILE-01–02–03
- Install `aiofiles`
- `file_service.py`: async upload, async download (FileResponse streaming)
- `FileUploadResponse` schema
- `app/api/files.py` route handlers
- **Files:** `app/services/file_service.py`, `app/api/files.py`, `app/schemas/file.py` (new), `requirements.txt`

**Wave structure:**
```
Wave 1: Plan 01 (activity_service + migration) — no deps
Wave 2: Plans 02, 03, 04, 05 — all depend on Plan 01, parallel to each other
```

---

## Common Pitfalls (Phase 2 Specific)

| Pitfall | Risk | Prevention |
|---------|------|-----------|
| `activity_service.log()` after `db.commit()` | Log entry in different transaction than triggering action | Always log BEFORE `await db.commit()` — non-negotiable |
| Returning raw dict from service | camelCase aliases don't fire, FE receives snake_case | Return `Model.model_validate(orm_obj)` — never `{...}` dicts |
| Blocking `open()` in upload handler | Blocks event loop during file write | Use `aiofiles.open()` — never `open()` in async context |
| `selectinload` vs `joinedload` confusion | N+1 queries or wrong join type | selectinload = one-to-many (programs, students); joinedload = many-to-one (student.ngo, student.program) |
| Sharing AsyncSession across concurrent tasks | "This Session's transaction has been rolled back" | Session-per-request only — never pass session to background tasks |
| Student wallet creation fails silently | Student created without wallet_address | Call blockchain AFTER flush, BEFORE commit; exception propagates and rolls back |
| Ownership check skipped | Cross-NGO data access (HTTP 200 instead of 403) | Every NGO service method must check `record.ngo_id == ngo.id` |
| Application `submitted_by_user_id` missing | `GET /student/applications` returns all applications | Add column in migration, set at submission time |
| `model_validate()` on post-commit object | `MissingGreenlet` if relationships not loaded | Use `expire_on_commit=False` (already set in Phase 1 session factory) + explicit `selectinload`/`joinedload` in queries |

---

## Validation Architecture

> Used by plan-checker Dimension 8 (Nyquist validation)

### What Can Be Tested Without External Services

All Phase 2 logic is pure async Python + SQLAlchemy — fully testable with `pytest-asyncio` + SQLite in-memory (or `asyncpg` with a test DB).

### Key Behaviors Worth Testing (if tests were written)

1. **activity_service.log():** Writes ActivityLog row with correct type, text, color, actor_id before commit
2. **Admin NGO verify:** Status changes to `verified`, ActivityLog written in same transaction
3. **Student creation:** `scholarship_id` matches `EDU-{YEAR}-{N5}`, `wallet_address` non-null, activity log written
4. **Application accept:** Student created from application fields, application status → `accepted`, activity log written
5. **Application reject:** `rejection_reason` stored, application status → `rejected`
6. **NGO ownership:** Accessing another NGO's program returns 403
7. **File upload:** FileRecord written to DB, file exists on disk at `uploads/{role}/{uuid}.ext`
8. **camelCase aliases:** Response JSON keys match mock.js exactly (e.g., `scholarshipId` not `scholarship_id`)

### Integration Smoke Tests (Manual for v1)

After each plan completes, verify via curl:
```bash
# Auth setup
TOKEN=$(curl -s -X POST /api/auth/login -d '{"email":"ngo@test.com","password":"..."}' | jq -r '.accessToken')

# NGO: create program
curl -s -X POST /api/ngo/programs -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Test Program","totalBudget":10000,"categories":["tuition"]}' | jq .ngoId

# NGO: register student  
curl -s -X POST /api/ngo/students -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Test Student","programId":1,...}' | jq '{scholarshipId,walletAddress}'

# Admin: verify NGO
curl -s -X PATCH /api/admin/ngos/1/verify -H "Authorization: Bearer $ADMIN_TOKEN" | jq .status
```

---

## Files Created/Modified in Phase 2

| File | Action | Plan |
|------|--------|------|
| `app/services/activity_service.py` | Implement | 01 |
| `alembic/versions/0002_phase2_additions.py` | Create | 01 |
| `app/schemas/admin.py` | Create | 02 |
| `app/services/admin_service.py` | Implement | 02 |
| `app/api/admin.py` | Implement | 02 |
| `app/services/ngo_service.py` | Implement | 03 |
| `app/api/ngo.py` | Implement | 03 |
| `app/schemas/ngo.py` | Update (NGOStatsResponse) | 03 |
| `app/services/donor_service.py` | Implement | 04 |
| `app/services/school_service.py` | Implement | 04 |
| `app/services/student_service.py` | Implement | 04 |
| `app/api/donor.py` | Implement | 04 |
| `app/api/school.py` | Implement | 04 |
| `app/api/student.py` | Implement | 04 |
| `app/schemas/file.py` | Create | 05 |
| `app/services/file_service.py` | Implement | 05 |
| `app/api/files.py` | Implement | 05 |
| `requirements.txt` | Add aiofiles | 05 |

---

## RESEARCH COMPLETE

**Key decisions captured:**
1. 5-plan split (activity_service → admin → ngo → donor+school+student → files), Wave 1 + Wave 2 parallel
2. Migration 0002 needed for `color`, `rejection_reason`, `submitted_by_user_id`
3. `_create_student()` helper shared between direct registration and accept-application paths
4. `aiofiles` only new dependency
5. `submitted_by_user_id` on `ScholarshipApplication` for student's own-application filter
6. `FastAPIFileResponse` for download (no manual aiofiles read)
7. `get_current_ngo` local dependency for all NGO routes (injects typed NGO object)
8. Activity log BEFORE commit — enforced in all 5 service files

**Blockers:** None — all patterns established in Phase 1, mock.js field names verified, models and stubs in place.
