# Phase 3: Fund Flow — Research

**Researched:** 2026-03-09
**Domain:** Blockchain-gated financial transactions (donations, fund allocations, invoice settlements) in async FastAPI + SQLAlchemy
**Confidence:** HIGH — all patterns from prior phases verified against live codebase; no new dependencies

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DONOR-04 | Donor can donate to an NGO, program, or student (triggers blockchain donation tx, sets tx_hash) | `Donation` model + `DonationType` enum exist; `blockchain.donate()` signature confirmed; `DonationResponse.txHash` alias already in schema |
| DONOR-05 | Donor can view their own donation history | `Donor.donations` relationship (selectin) exists; donor_service stub present; filter by `Donation.donor_id` |
| DONOR-06 | Donor can view a single donation detail including fund flow (where money went) | `Donation` has joinedload to `ngo`, `program`, `student`; fund-flow chain built from DB relationships |
| NGO-08 | NGO can list invoices submitted by schools for their programs | `Invoice` model exists; needs query: `Invoice.ngo_id == ngo.id`; ngo_service stub present |
| NGO-09 | NGO can approve an invoice (triggers blockchain settlement tx, sets tx_hash) or reject it | `Invoice.tx_hash` + `Invoice.approved_date` nullable columns exist; `blockchain.settle_invoice()` confirmed; ngo_service needs approve/reject methods |
| NGO-10 | NGO can allocate funds to a student or program (triggers blockchain allocation tx, sets tx_hash) | `blockchain.allocate_funds()` confirmed; `Student.wallet_balance` + `Student.total_received` mutable; **no Allocation ORM model** exists — must decide: new model vs direct student mutation |
| NGO-11 | NGO can view allocation history | Depends on NGO-10 decision: new Allocation model enables proper history; direct mutation loses history |
| SCHL-03 | School can submit an invoice to claim funds (with supporting document reference) | `Invoice` model complete; `school_service` stub present; `School.total_invoiced` mutable |
| SCHL-04 | School can view their own invoices with current status | `School.invoices` relationship (selectin) exists; filter by `Invoice.school_id` |
</phase_requirements>

---

## Summary

Phase 3 is the "money movement" phase — every endpoint either creates a financial record, changes one's status, or queries the fund-flow trail. There are three distinct blockchain operations (`donate`, `allocate_funds`, `settle_invoice`) that must fire in the service layer before `db.commit()`, keeping activity log entries atomic with the triggering action.

The codebase is in excellent shape. All ORM models (`Donation`, `Invoice`, `Student`, `Donor`, `Program`, `School`) exist with every column Phase 3 needs. All Pydantic schemas (`DonationResponse`, `InvoiceResponse`) are defined with correct camelCase aliases. All three blockchain methods are implemented in `MockSuiService` and accessible via `Depends(get_blockchain)`. The service stubs (`donor_service.py`, `ngo_service.py`, `school_service.py`) and router stubs (`donor.py`, `ngo.py`, `school.py`) are in place — Phase 3 fills them out.

The only structural decision is **NGO-10/NGO-11 allocation history**: the `Student` model can be mutated directly (simplest), but NGO-11 requires queryable history. A new `Allocation` ORM model is necessary to support `GET /api/ngo/allocations`. This needs a new Alembic migration.

**Primary recommendation:** Add a lightweight `Allocation` model (migration 0003), implement all service methods following the established blockchain-then-commit pattern, and wire up the remaining 11 endpoints across donor/ngo/school routers in a 4-plan wave structure.

---

## Standard Stack

### Core (Already in requirements.txt — no new installs needed)

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| FastAPI | ≥0.110 | Router, Depends, response_model | ✅ installed Phase 1 |
| SQLAlchemy | 2.x (async) | AsyncSession, select(), ORM | ✅ installed Phase 1 |
| asyncpg | latest | PostgreSQL async driver | ✅ installed Phase 1 |
| Pydantic v2 | ≥2.0 | Schemas, aliases, from_attributes | ✅ installed Phase 1 |
| Alembic | latest (async template) | Migration 0003 for Allocation table | ✅ installed Phase 1 |

**No new pip installs required for Phase 3.** Every tool is already present.

---

## Architecture Patterns

### Service Pattern (Mandatory — identical to Phase 2)

```python
# Source: live codebase — app/services/ngo_service.py pattern
async def approve_invoice(
    db: AsyncSession,
    invoice_id: int,
    ngo: NGO,
    blockchain: BlockchainService,
    actor_id: int,
) -> InvoiceResponse:
    # 1. Fetch entity
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise NotFoundError("Invoice", invoice_id)

    # 2. Ownership check — MANDATORY for every NGO service method
    if invoice.ngo_id != ngo.id:
        raise ForbiddenError("Invoice does not belong to your NGO")

    # 3. Business validation
    if invoice.status != InvoiceStatus.pending:
        raise AppValidationError(f"Invoice is already {invoice.status.value}")

    # 4. Blockchain call — BEFORE commit, BEFORE log
    tx = await blockchain.settle_invoice(
        str(ngo.id), str(invoice.school_id), str(invoice.id), invoice.amount
    )

    # 5. Mutate state
    invoice.status = InvoiceStatus.approved
    invoice.tx_hash = tx.tx_hash
    invoice.approved_date = datetime.now(timezone.utc)

    # 6. Activity log — BEFORE commit (atomicity requirement, Phase 2 pattern)
    await activity_service.log(
        db,
        "invoice",
        f"Invoice from '{invoice.school_name}' approved by {ngo.name}",
        actor_id,
    )

    # 7. Commit — single transaction covers all mutations
    await db.commit()
    return InvoiceResponse.model_validate(invoice)
```

### Route Handler Pattern (Mandatory — identical to Phase 2)

```python
# Source: live codebase — app/api/ngo.py pattern
@router.patch("/invoices/{invoice_id}/approve", response_model=InvoiceResponse)
async def approve_invoice(
    invoice_id: int,
    ngo: NGO = Depends(get_current_ngo),
    db: AsyncSession = Depends(get_db),
    blockchain: BlockchainService = Depends(get_blockchain),
    current_user=Depends(require_role("ngo")),
) -> InvoiceResponse:
    return await ngo_service.approve_invoice(db, invoice_id, ngo, blockchain, current_user.id)
```

### Allocation Model Decision (NGO-10/NGO-11)

**Problem:** NGO-11 requires `GET /api/ngo/allocations` — a queryable history of fund allocations. The `Student` model has `wallet_balance` and `total_received` (float fields), but no record of individual allocation events.

**Decision: Create `Allocation` ORM model** (new migration 0003).

Rationale:
- Without a model, NGO-11 would return an empty list or require awkward ActivityLog reverse-parsing
- The Allocation model is lightweight (6 columns) and follows the established pattern
- Enables sorting, filtering by student/program in future phases
- Consistent with how `Donation` and `Invoice` track individual financial events

```python
# app/models/allocation.py — NEW in Phase 3
class Allocation(Base):
    __tablename__ = "allocations"

    id = Column(Integer, primary_key=True, index=True)
    ngo_id = Column(Integer, ForeignKey("ngos.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True, index=True)
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="SET NULL"), nullable=True, index=True)
    amount = Column(Float, nullable=False)
    date = Column(DateTime, default=datetime.utcnow, nullable=False)
    tx_hash = Column(String(128), nullable=True)

    ngo = relationship("NGO", lazy="joined")
    student = relationship("Student", lazy="joined")
    program = relationship("Program", lazy="joined")
```

### Donation Service Pattern (DONOR-04)

```python
async def create_donation(
    db: AsyncSession,
    data: DonationCreate,
    current_user: User,
    blockchain: BlockchainService,
) -> DonationResponse:
    # Fetch donor record for this user
    result = await db.execute(select(Donor).where(Donor.user_id == current_user.id))
    donor = result.scalar_one_or_none()
    if donor is None:
        raise NotFoundError("Donor profile", current_user.id)

    # Determine blockchain target
    target_type = data.type  # "ngo" | "program" | "student"
    target_id = str(data.student_id or data.program_id or data.ngo_id)

    # Blockchain call FIRST — tx_hash must exist before commit
    tx = await blockchain.donate(str(donor.id), target_type, target_id, data.amount)

    # Create donation record
    donation = Donation(
        donor_id=donor.id,
        ngo_id=data.ngo_id,
        program_id=data.program_id,
        student_id=data.student_id,
        amount=data.amount,
        type=DonationType(data.type),
        message=data.message,
        tx_hash=tx.tx_hash,
    )
    db.add(donation)

    # Update donor totals
    donor.total_donated = donor.total_donated + data.amount
    donor.donations_count = donor.donations_count + 1

    # Log BEFORE commit
    await activity_service.log(
        db, "donation",
        f"{donor.name} donated ${data.amount:,.2f} to {_resolve_target_name(data)}",
        current_user.id,
    )
    await db.commit()
    return DonationResponse.model_validate(donation)
```

### Fund-Flow Chain (DONOR-06)

The `GET /api/donor/donations/{id}` response returns the complete fund-flow chain. Since all models are connected via FK relationships, this is a JOIN query:

```python
async def get_donation_detail(
    db: AsyncSession, donation_id: int, current_user: User
) -> DonationDetailResponse:
    result = await db.execute(
        select(Donation)
        .where(Donation.id == donation_id)
        .options(
            joinedload(Donation.donor),
            joinedload(Donation.ngo),
            joinedload(Donation.program).selectinload(Program.invoices),
            joinedload(Donation.student),
        )
    )
    donation = result.scalar_one_or_none()
    if donation is None:
        raise NotFoundError("Donation", donation_id)
    # Ownership check
    if donation.donor.user_id != current_user.id:
        raise ForbiddenError("You can only view your own donations")
    return DonationDetailResponse.model_validate(donation)
```

The `DonationDetailResponse` includes:
- donation `txHash` (set at creation)
- allocations made from the program (linked via `program.allocations` or `student` direct query)
- invoices settled for the program (linked via `program.invoices`)

**Implementation note:** A simplified approach that satisfies DONOR-06 without complex JOINs: return the donation with its linked program's approved invoices (each with `tx_hash`) and any Allocation records for the student. This "fund-flow chain" is built in Python from the ORM relationships, not a DB view.

### School Invoice Creation (SCHL-03)

```python
async def create_invoice(
    db: AsyncSession, data: InvoiceCreate, current_user: User
) -> InvoiceResponse:
    # Fetch school record
    result = await db.execute(select(School).where(School.user_id == current_user.id))
    school = result.scalar_one_or_none()
    if school is None:
        raise NotFoundError("School profile", current_user.id)

    # Compute total from items
    amount = sum(item.get("amount", 0) for item in data.items)

    invoice = Invoice(
        school_id=school.id,
        ngo_id=data.ngo_id,
        program_id=data.program_id,
        school_name=school.name,  # denormalized from School record
        amount=amount,
        category=data.category,
        status=InvoiceStatus.pending,
        items=data.items,
    )
    db.add(invoice)

    # Update school.total_invoiced
    school.total_invoiced = school.total_invoiced + amount

    # Log BEFORE commit — no blockchain call on submission
    await activity_service.log(
        db, "invoice",
        f"{school.name} submitted invoice for {data.category} (${amount:,.2f})",
        current_user.id,
    )
    await db.commit()
    return InvoiceResponse.model_validate(invoice)
```

**Key note:** School invoice submission does NOT call blockchain. Only `approve_invoice` (NGO-09) calls `blockchain.settle_invoice()`. The submission just creates a pending record.

---

## Endpoint Inventory

### Donor Endpoints (DONOR-04, DONOR-05, DONOR-06)

| Method | Path | Handler Returns | Blockchain | Requirements |
|--------|------|----------------|------------|-------------|
| POST | `/api/donor/donations` | `DonationResponse` (201) | `blockchain.donate()` | DONOR-04 |
| GET | `/api/donor/donations` | `list[DonationResponse]` | None | DONOR-05 |
| GET | `/api/donor/donations/{id}` | `DonationDetailResponse` | None | DONOR-06 |

### NGO Invoice Endpoints (NGO-08, NGO-09)

| Method | Path | Handler Returns | Blockchain | Requirements |
|--------|------|----------------|------------|-------------|
| GET | `/api/ngo/invoices` | `list[InvoiceResponse]` | None | NGO-08 |
| PATCH | `/api/ngo/invoices/{id}/approve` | `InvoiceResponse` | `blockchain.settle_invoice()` | NGO-09 |
| PATCH | `/api/ngo/invoices/{id}/reject` | `InvoiceResponse` | None | NGO-09 |

### NGO Allocation Endpoints (NGO-10, NGO-11)

| Method | Path | Handler Returns | Blockchain | Requirements |
|--------|------|----------------|------------|-------------|
| POST | `/api/ngo/allocations` | `AllocationResponse` (201) | `blockchain.allocate_funds()` | NGO-10 |
| GET | `/api/ngo/allocations` | `list[AllocationResponse]` | None | NGO-11 |

### School Invoice Endpoints (SCHL-03, SCHL-04)

| Method | Path | Handler Returns | Blockchain | Requirements |
|--------|------|----------------|------------|-------------|
| POST | `/api/school/invoices` | `InvoiceResponse` (201) | None | SCHL-03 |
| GET | `/api/school/invoices` | `list[InvoiceResponse]` | None | SCHL-04 |

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| `Optional[str] = None` in Pydantic v2 | Custom nullable field logic | `Optional[str] = Field(default=None, alias="...")` — already in `InvoiceResponse.tx_hash` | Pydantic v2 requires explicit `default=None`; implicit None is unreliable |
| Relationship loading | Manual JOIN queries | `selectinload()` / `joinedload()` already configured on models | ORM lazy loading deadlocks async sessions |
| Blockchain DI | Direct `MockSuiService()` instantiation | `Depends(get_blockchain)` — already established | Coupling to mock breaks swap-to-real pattern |
| Session management | Creating new sessions mid-request | `Depends(get_db)` — one session per request | Sharing sessions across concurrent tasks causes "Transaction already rolled back" |
| Activity color lookup | Hardcoded color strings | `activity_service.COLOR_MAP` — already defined | Consistent color across all activity types |
| camelCase aliases | Manual `.dict()` with key renaming | `BaseResponse` with `Field(alias=)` — established pattern | Pydantic model_validate fires aliases; raw dict does not |

---

## Common Pitfalls

### Pitfall 1: Blockchain Before Commit, Activity Before Commit — ORDER MATTERS

**What goes wrong:** Calling `db.commit()` before `blockchain.donate()` means if blockchain fails, the donation DB record is already persisted with no `tx_hash`. Calling `activity_service.log()` after `db.commit()` means the log entry is in a different transaction.

**Correct order:**
1. Blockchain call → get `tx_hash`
2. Mutate ORM object (set `tx_hash`)
3. `activity_service.log()` (adds to current session, no commit)
4. `db.commit()` — all three land atomically

**Warning signs:** Service method calls `db.commit()` before `activity_service.log()` or before blockchain returns.

### Pitfall 2: `Optional[str] = None` in Pydantic v2 (Documented in ROADMAP scope notes)

**What goes wrong:**
```python
# WRONG — Pydantic v2 does not infer Optional default
tx_hash: Optional[str] = Field(alias="txHash")  # raises ValidationError if field missing from ORM

# CORRECT
tx_hash: Optional[str] = Field(default=None, alias="txHash")
```

**Why it happens:** Pydantic v2 changed `Optional[str]` to mean "can be None" but NOT "defaults to None". Explicit `default=None` is required.

**Where this matters:** `InvoiceResponse.tx_hash`, `InvoiceResponse.approved_date`, and any new `AllocationResponse.tx_hash` field.

**Verification:** `InvoiceResponse` in live codebase already correctly has `default=None` — verify any NEW schemas added in Phase 3 follow the same pattern.

### Pitfall 3: Session-Per-Request — Never Share Across Concurrent Tasks

**What goes wrong:** If a service method spawns `asyncio.create_task()` or `asyncio.gather()` and passes the same `AsyncSession` to multiple coroutines, SQLAlchemy raises "This Session's transaction has been rolled back due to a previous exception during flush."

**Why it happens:** `AsyncSession` is not thread/task-safe. One task's exception rolls back the session, silently corrupting all other tasks sharing it.

**Prevention:** All Phase 3 service methods are linear (sequential async calls). Never pass `db` to a background task or `asyncio.gather()`. All three blockchain operations (`donate`, `allocate_funds`, `settle_invoice`) are sequential per request.

**Warning sign:** Any `asyncio.gather()` or `asyncio.create_task()` in a service method that receives `db: AsyncSession`.

### Pitfall 4: Stale ORM State After Commit (db.refresh Pattern)

**What goes wrong:** After `await db.commit()`, SQLAlchemy expires all ORM objects in the session (`expire_on_commit=False` prevents this at the sessionmaker level, but relationships loaded before the commit may be stale).

**Prevention:** The `expire_on_commit=False` setting on the session factory (Phase 1) prevents most cases. But if a service method calls a helper that commits THEN tries to use the parent object's relationships, use `await db.refresh(obj)`. Precedent: `ngo_service.register_student()` calls `await db.refresh(ngo)` after `_create_student()` commits.

### Pitfall 5: DonationDetailResponse Fund-Flow Chain (DONOR-06)

**What goes wrong:** DONOR-06 requires the "complete fund-flow chain: donation → allocation(s) → invoice settlement, each with its txHash." Building this naively as a JOIN query across 3 tables with complex eager loading can fail with the N+1 problem or cause SQLAlchemy to emit unexpected SQL.

**Correct approach:** Fetch the donation with its relationships loaded via `joinedload`/`selectinload`. Then, in Python, build the fund-flow chain by:
1. The donation itself (has `tx_hash`)
2. If `program_id` set: fetch `Allocation` records for `program_id` (have `tx_hash`)
3. If `program_id` set: fetch approved `Invoice` records for `program_id` (have `tx_hash`)
4. Return as a structured `DonationDetailResponse` with nested lists

This avoids complex DB views while satisfying the requirement.

### Pitfall 6: NGO Ownership on Invoice Operations (NGO-08, NGO-09)

**What goes wrong:** `GET /api/ngo/invoices` must return ONLY invoices for the authenticated NGO's programs — not all invoices in the DB. Similarly, approve/reject must verify `invoice.ngo_id == ngo.id`.

**Prevention:** All NGO service methods already enforce `record.ngo_id == ngo.id` (established in Phase 2). Apply the same check in every Phase 3 NGO invoice method.

### Pitfall 7: Invoice Amount Calculation on Submission

**What goes wrong:** The `Invoice.amount` column is `NOT NULL`. On school invoice submission (SCHL-03), the request body has `items: [{"desc": str, "amount": float}]` but no top-level `amount` field. The service must compute `amount = sum(item["amount"] for item in data.items)`.

**Why it matters:** `InvoiceCreate` schema does not include `amount` — the frontend sends items only. The service layer computes the total. This is already the intended design (matches mock.js where `amount` in invoices equals the sum of `items[].amount`).

---

## New Schema Required: AllocationResponse + AllocationCreate

Since no Allocation model exists yet, new schemas must be created:

```python
# app/schemas/allocation.py — NEW in Phase 3
from datetime import datetime
from typing import Optional
from pydantic import Field
from app.schemas.common import BaseResponse


class AllocationCreate(BaseResponse):
    student_id: int = Field(alias="studentId")
    program_id: Optional[int] = Field(default=None, alias="programId")
    amount: float


class AllocationResponse(BaseResponse):
    id: int
    ngo_id: int = Field(alias="ngoId")
    student_id: Optional[int] = Field(default=None, alias="studentId")
    program_id: Optional[int] = Field(default=None, alias="programId")
    amount: float
    date: datetime
    tx_hash: Optional[str] = Field(default=None, alias="txHash")
```

**mock.js alignment:** Allocations are not a separate entity in mock.js — they appear as `program.allocated` (float) and `student.walletBalance` (float). The `AllocationResponse` schema is **server-side only** (not fed to the FE mock). The FE accesses wallet balance via `StudentResponse.walletBalance` which Phase 3 keeps up-to-date by mutating `Student.wallet_balance`.

---

## New Migration: 0003_phase3_allocations.py

Phase 3 requires one Alembic migration adding the `allocations` table:

```python
# alembic/versions/0003_phase3_allocations.py
def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS allocations (
            id SERIAL PRIMARY KEY,
            ngo_id INTEGER NOT NULL REFERENCES ngos(id) ON DELETE CASCADE,
            student_id INTEGER REFERENCES students(id) ON DELETE SET NULL,
            program_id INTEGER REFERENCES programs(id) ON DELETE SET NULL,
            amount FLOAT NOT NULL,
            date TIMESTAMP NOT NULL DEFAULT NOW(),
            tx_hash VARCHAR(128)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_allocations_ngo_id ON allocations (ngo_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_allocations_student_id ON allocations (student_id)")
```

**Pattern:** Raw `op.execute()` SQL — consistent with migrations 0001 and 0002. No `op.add_column` with typed enums.

---

## DonationDetailResponse Design (DONOR-06)

The fund-flow chain requirement needs a richer response shape than `DonationResponse`. Two options:

**Option A: Nested response (recommended)**
```python
class FundFlowAllocation(BaseResponse):
    id: int
    student_id: int = Field(alias="studentId")
    amount: float
    tx_hash: Optional[str] = Field(default=None, alias="txHash")
    date: datetime

class FundFlowInvoice(BaseResponse):
    id: int
    school_name: str = Field(alias="schoolName")
    amount: float
    status: str
    tx_hash: Optional[str] = Field(default=None, alias="txHash")
    approved_date: Optional[datetime] = Field(default=None, alias="approvedDate")

class DonationDetailResponse(DonationResponse):
    # Inherits all DonationResponse fields
    allocations: list[FundFlowAllocation] = []
    invoices: list[FundFlowInvoice] = []
```

**Option B: Flat donation response (minimal)** — return only `DonationResponse` (same as list endpoint). This technically satisfies DONOR-06 if the requirement just means "single donation with txHash".

**Recommendation: Option A** — the roadmap success criteria explicitly says "returns the complete fund-flow chain: donation → allocation(s) → invoice settlement, each with its txHash." A nested response is the only way to surface multiple txHash values.

---

## Plan Decomposition Strategy

Phase 3 has 9 requirements across 4 role groups. Recommended split into **4 plans**:

### Plan 01 — Migration + Allocation Model (Wave 1)

**Requirements:** Enables NGO-10, NGO-11
- Create `app/models/allocation.py` (new Allocation ORM model)
- Create `app/schemas/allocation.py` (AllocationCreate, AllocationResponse, DonationDetailResponse with fund-flow fields)
- Create `alembic/versions/0003_phase3_allocations.py` (allocations table)
- Register Allocation in `app/models/__init__.py`
- **Files:** `app/models/allocation.py`, `app/schemas/allocation.py`, `alembic/versions/0003_phase3_allocations.py`, `app/models/__init__.py`

### Plan 02 — Donor Service + Routes (Wave 2, depends on 01)

**Requirements:** DONOR-04, DONOR-05, DONOR-06
- `donor_service.py`: add `create_donation()`, `list_donations()`, `get_donation_detail()`
- `donor.py` router: add `POST /donations` (201), `GET /donations`, `GET /donations/{id}`
- DonationDetailResponse with fund-flow chain (allocations + invoices for the program)
- **Files:** `app/services/donor_service.py`, `app/api/donor.py`

### Plan 03 — NGO Invoice + Allocation (Wave 2, depends on 01)

**Requirements:** NGO-08, NGO-09, NGO-10, NGO-11
- `ngo_service.py`: add `list_invoices()`, `approve_invoice()`, `reject_invoice()`, `create_allocation()`, `list_allocations()`
- `ngo.py` router: add `GET /invoices`, `PATCH /invoices/{id}/approve`, `PATCH /invoices/{id}/reject`, `POST /allocations`, `GET /allocations`
- `approve_invoice()` calls `blockchain.settle_invoice()` + sets `invoice.approved_date` + `invoice.tx_hash`
- `create_allocation()` calls `blockchain.allocate_funds()` + updates `student.wallet_balance` + `student.total_received` + creates `Allocation` record
- **Files:** `app/services/ngo_service.py`, `app/api/ngo.py`

### Plan 04 — School Invoice (Wave 2, depends on 01)

**Requirements:** SCHL-03, SCHL-04
- `school_service.py`: add `create_invoice()`, `list_invoices()`
- `school.py` router: add `POST /invoices` (201), `GET /invoices`
- No blockchain call on submission (pending only) — only NGO approval triggers blockchain
- **Files:** `app/services/school_service.py`, `app/api/school.py`

**Wave structure:**
```
Wave 1: Plan 01 (Allocation model + migration) — no deps
Wave 2: Plans 02, 03, 04 — all depend on Plan 01, parallel to each other
```

---

## Activity Log Strings for Phase 3

Consistent with Phase 2 `COLOR_MAP` (already in `activity_service.py`):

| Action | type | color | text pattern |
|--------|------|-------|-------------|
| Donation created | `"donation"` | `"green"` | `"{donor_name} donated ${amount:,.2f} to {target_name}"` |
| Invoice submitted | `"invoice"` | `"amber"` | `"{school_name} submitted invoice for {category} (${amount:,.2f})"` |
| Invoice approved | `"invoice"` | `"amber"` | `"Invoice from '{school_name}' approved by {ngo_name}"` |
| Invoice rejected | `"invoice"` | `"amber"` | `"Invoice from '{school_name}' rejected by {ngo_name}"` |
| Fund allocated | `"allocation"` | `"purple"` | `"{ngo_name} allocated ${amount:,.2f} to {student_name}"` |

**Note:** `"invoice"` type maps to `"amber"` in `COLOR_MAP`. This matches mock.js activity feed (`{ type: 'invoice', color: 'amber', ... }`).

---

## camelCase Field Verification (Phase 3 Schemas)

Verified against `../edutrack/src/data/mock.js`:

| Schema | Field | camelCase Alias | Status |
|--------|-------|----------------|--------|
| DonationResponse | `donor_id` | `donorId` | ✅ existing |
| DonationResponse | `ngo_id` | `ngoId` | ✅ existing |
| DonationResponse | `program_id` | `programId` | ✅ existing |
| DonationResponse | `student_id` | `studentId` | ✅ existing |
| DonationResponse | `tx_hash` | `txHash` | ✅ existing |
| InvoiceResponse | `school_id` | `schoolId` | ✅ existing |
| InvoiceResponse | `school_name` | `schoolName` | ✅ existing |
| InvoiceResponse | `ngo_id` | `ngoId` | ✅ existing |
| InvoiceResponse | `program_id` | `programId` | ✅ existing |
| InvoiceResponse | `approved_date` | `approvedDate` | ✅ existing |
| InvoiceResponse | `supporting_doc` | `supportingDoc` | ✅ existing |
| InvoiceResponse | `tx_hash` | `txHash` | ✅ existing |
| AllocationResponse | `ngo_id` | `ngoId` | ❌ NEW SCHEMA NEEDED |
| AllocationResponse | `student_id` | `studentId` | ❌ NEW SCHEMA NEEDED |
| AllocationResponse | `program_id` | `programId` | ❌ NEW SCHEMA NEEDED |
| AllocationResponse | `tx_hash` | `txHash` | ❌ NEW SCHEMA NEEDED |
| DonationDetailResponse | (inherits DonationResponse) | — | ❌ NEW SCHEMA NEEDED |

**mock.js donation shape:** `{ id, donorId, ngoId, programId, amount, date, type }` — no `txHash` in mock data but the API response MUST include it (ROADMAP success criterion 1 explicitly requires it). The schema already has `txHash` field.

---

## Validation Architecture

> `workflow.nyquist_validation = true` in `.planning/config.json` — this section is REQUIRED.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + httpx (v2 requirements) — not yet installed |
| Config file | none — Wave 0 gap |
| Quick run command | `pytest tests/ -x -q` (once installed) |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DONOR-04 | POST /api/donor/donations returns 201 with txHash (64-char hex) | unit/integration | `pytest tests/test_donor_service.py::test_create_donation -x` | ❌ Wave 0 |
| DONOR-05 | GET /api/donor/donations returns only authenticated donor's donations | unit | `pytest tests/test_donor_service.py::test_list_donations_scoped -x` | ❌ Wave 0 |
| DONOR-06 | GET /api/donor/donations/{id} returns fund-flow chain with nested txHash | unit | `pytest tests/test_donor_service.py::test_donation_detail_fund_flow -x` | ❌ Wave 0 |
| NGO-08 | GET /api/ngo/invoices returns only NGO-owned invoices | unit | `pytest tests/test_ngo_service.py::test_list_invoices_scoped -x` | ❌ Wave 0 |
| NGO-09 | PATCH approve sets status=approved, tx_hash set, activity log written | unit | `pytest tests/test_ngo_service.py::test_approve_invoice -x` | ❌ Wave 0 |
| NGO-09 | PATCH reject sets status=rejected, activity log written | unit | `pytest tests/test_ngo_service.py::test_reject_invoice -x` | ❌ Wave 0 |
| NGO-10 | POST /api/ngo/allocations updates student.wallet_balance, creates Allocation record with txHash | unit | `pytest tests/test_ngo_service.py::test_create_allocation -x` | ❌ Wave 0 |
| NGO-11 | GET /api/ngo/allocations returns only this NGO's allocations | unit | `pytest tests/test_ngo_service.py::test_list_allocations_scoped -x` | ❌ Wave 0 |
| SCHL-03 | POST /api/school/invoices creates pending invoice, amount=sum(items), activity log written | unit | `pytest tests/test_school_service.py::test_create_invoice -x` | ❌ Wave 0 |
| SCHL-04 | GET /api/school/invoices returns only this school's invoices | unit | `pytest tests/test_school_service.py::test_list_invoices_scoped -x` | ❌ Wave 0 |

> **Note:** Test suite is v2 scope (TEST-V2-01 in REQUIREMENTS.md). For v1 demo, manual curl verification is the validation approach. Wave 0 gaps above represent the future test infrastructure needed.

### Sampling Rate (Manual for v1)

- **Per task commit:** Curl smoke test for the specific endpoint added
- **Per wave merge:** All 11 endpoint smoke tests
- **Phase gate:** All 4 success criteria from ROADMAP.md verified before `/gsd-verify-work`

### Manual Verification Commands (v1)

```bash
# Setup
NGO_TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ngo@test.com","password":"testpass"}' | python -c "import sys,json; print(json.load(sys.stdin)['accessToken'])")

DONOR_TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"donor@test.com","password":"testpass"}' | python -c "import sys,json; print(json.load(sys.stdin)['accessToken'])")

SCHOOL_TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"school@test.com","password":"testpass"}' | python -c "import sys,json; print(json.load(sys.stdin)['accessToken'])")

# DONOR-04: Create donation — check txHash in response
curl -s -X POST http://localhost:8000/api/donor/donations \
  -H "Authorization: Bearer $DONOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ngoId":1,"amount":100.0,"type":"general"}' | python -c "import sys,json; r=json.load(sys.stdin); print('PASS' if len(r.get('txHash',''))==64 else 'FAIL: no txHash')"

# NGO-09: Approve invoice — check txHash and status
curl -s -X PATCH http://localhost:8000/api/ngo/invoices/1/approve \
  -H "Authorization: Bearer $NGO_TOKEN" | python -c "import sys,json; r=json.load(sys.stdin); print('PASS' if r.get('status')=='approved' and r.get('txHash') else 'FAIL')"

# NGO-10: Create allocation — check student wallet updated
ALLOC=$(curl -s -X POST http://localhost:8000/api/ngo/allocations \
  -H "Authorization: Bearer $NGO_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"studentId":1,"amount":500.0}')
echo $ALLOC | python -c "import sys,json; r=json.load(sys.stdin); print('PASS' if len(r.get('txHash',''))==64 else 'FAIL: no txHash')"

# SCHL-03: Submit invoice
curl -s -X POST http://localhost:8000/api/school/invoices \
  -H "Authorization: Bearer $SCHOOL_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ngoId":1,"category":"tuition","items":[{"desc":"Tuition","amount":500.0}]}' | python -c "import sys,json; r=json.load(sys.stdin); print('PASS' if r.get('status')=='pending' and r.get('amount')==500.0 else 'FAIL')"
```

### Wave 0 Gaps

- [ ] `tests/test_donor_service.py` — covers DONOR-04, DONOR-05, DONOR-06
- [ ] `tests/test_ngo_service.py` — covers NGO-08, NGO-09, NGO-10, NGO-11
- [ ] `tests/test_school_service.py` — covers SCHL-03, SCHL-04
- [ ] `tests/conftest.py` — shared fixtures (in-memory SQLite or test PostgreSQL)
- [ ] Framework install: `pip install pytest pytest-asyncio httpx` — if test suite needed for v1

*(Automated testing is v2 scope — manual curl verification is the v1 validation approach)*

---

## Files Created/Modified in Phase 3

| File | Action | Plan |
|------|--------|------|
| `app/models/allocation.py` | Create | 01 |
| `app/schemas/allocation.py` | Create | 01 |
| `app/schemas/donation.py` | Update (add DonationDetailResponse) | 01 |
| `alembic/versions/0003_phase3_allocations.py` | Create | 01 |
| `app/models/__init__.py` | Update (register Allocation) | 01 |
| `app/services/donor_service.py` | Implement (add donation methods) | 02 |
| `app/api/donor.py` | Implement (add donation endpoints) | 02 |
| `app/services/ngo_service.py` | Implement (add invoice + allocation methods) | 03 |
| `app/api/ngo.py` | Implement (add invoice + allocation endpoints) | 03 |
| `app/services/school_service.py` | Implement (add invoice methods) | 04 |
| `app/api/school.py` | Implement (add invoice endpoints) | 04 |

---

## Open Questions

1. **Fund-flow chain depth (DONOR-06)**
   - What we know: ROADMAP says "donation → allocation(s) → invoice settlement, each with its txHash"
   - What's unclear: How tightly coupled is a donation to specific allocations? A general donation to an NGO may not directly link to student allocations — the chain is conceptual, not a strict FK trail
   - Recommendation: For a program/student donation, return allocations for that program and invoices for that program. For a general NGO donation, return an empty allocations/invoices list — the donation `txHash` alone satisfies DONOR-04

2. **Allocation to program (NGO-10)**
   - What we know: ROADMAP says "allocate funds to a student or program"
   - What's unclear: Does allocation to a program update `Program.allocated` (float) rather than `Student.wallet_balance`?
   - Recommendation: Support both cases. If `student_id` provided → update `Student.wallet_balance + total_received`. If `program_id` only → update `Program.allocated`. `AllocationCreate` has both fields optional (at least one required).

3. **Invoice reject body (NGO-09)**
   - What we know: Invoice rejection sets `status = "rejected"` and logs activity
   - What's unclear: Does rejection require a reason string in the request body?
   - Recommendation: Mirror the application rejection pattern from Phase 2 — add an optional `InvoiceRejectRequest` body with `reason: Optional[str]`. If `Invoice` model needs a `rejection_reason` column, it does NOT currently have one — but that would need migration 0003 addition. Keep it optional/nullable.

---

## Sources

### Primary (HIGH confidence)
- Live codebase: `app/models/donation.py`, `app/models/invoice.py`, `app/models/student.py`, `app/models/allocation.py` (doesn't exist yet), `app/services/blockchain/base.py` — verified by direct file read
- Live codebase: `app/services/ngo_service.py` — blockchain + activity_service pattern verified as working in Phase 2
- Live codebase: `app/schemas/donation.py`, `app/schemas/invoice.py` — camelCase aliases verified
- Live codebase: `../edutrack/src/data/mock.js` — donation, invoice, allocation field names verified

### Secondary (MEDIUM confidence)
- ROADMAP.md Phase 3 success criteria — defines what "fund-flow chain" means for DONOR-06
- STATE.md accumulated context — carries forward session-per-request, activity-before-commit constraints

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, all tools verified in live codebase
- Architecture: HIGH — all patterns established in Phase 2, verified against actual service implementations
- Pitfalls: HIGH — Optional[str] Pydantic v2 behavior documented in ROADMAP; session sharing pitfall documented in Phase 2 research; all others verified from code reading
- Allocation model decision: HIGH — NGO-11 history requirement necessitates persistent record; no alternative satisfies the requirement without complex ActivityLog parsing

**Research date:** 2026-03-09
**Valid until:** Stable — no fast-moving dependencies. Valid until Phase 3 implementation begins.
