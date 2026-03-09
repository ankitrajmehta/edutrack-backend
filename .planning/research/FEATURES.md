# Features Research: EduTrack Backend

**Domain:** Scholarship Management / NGO Fund Distribution / Blockchain Transparency Platform
**Researched:** 2026-03-09
**Overall confidence:** HIGH (PRD, user stories, mock data, and competitor analysis all confirm the feature set)

---

## Context: How This Platform Differs from Standard Grant/Scholarship Software

Standard platforms (Blackbaud Award Management, Submittable, CommunityForce, Fluxx) are built for single-org use with one administrative role. EduTrack is a **multi-stakeholder ecosystem** — five distinct principals, each with a separate dashboard:

| Standard Platform | EduTrack |
|-------------------|----------|
| One admin role | Admin + NGO + Donor + School + Student + Public |
| Fund tracking only | Fund tracking + blockchain tx hash per disbursement |
| Applicant → approval | Application → acceptance → student record → wallet → allocation |
| No public transparency | Public stats + activity feed — no auth required |
| No vendor invoices | School partner invoicing with NGO approval + settlement |
| No beneficiary wallets | Each student has a scholarship wallet with balance |

The blockchain layer is not cosmetic — every money movement (donation, allocation, invoice settlement) writes a tx hash to the DB, creating an end-to-end audit trail that is the platform's core value proposition to UNICEF.

---

## Table Stakes (Must Have)

Missing any of these: the platform is broken for at least one user role.

### AUTH — All Roles

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Register with role | Entry point for all non-Admin users | Low | Role assigned at registration; Admin is seeded |
| Login → JWT access + refresh | Standard stateless auth | Low | 30min access / 7d refresh — PRD specified |
| Token refresh | Prevent logout on page reload | Low | Silent refresh in FE |
| Logout (invalidate refresh) | Security hygiene | Low | DB-side refresh token table or revocation list |
| `GET /me` — current user + profile | FE header/sidebar needs this on load | Low | Returns role-specific nested profile |
| Role-based access control (RBAC) | 5 roles × different data scopes | Medium | FastAPI Depends() guards on every route |

### ADMIN — Platform Governance

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Platform dashboard (aggregate stats) | Admin needs single-pane of glass | Medium | totalDonations, totalStudents, totalNGOs, totalPrograms, totalSchools, fundsAllocated, fundsUtilized — mirrors `platformStats` in mock.js |
| NGO list with status filter | Core trust & safety workflow | Low | Filter: pending / verified / rejected / blacklisted |
| Verify NGO | Required before NGO can run programs | Low | Status → 'verified'; writes activity log |
| Reject NGO | Prevent bad actors from accessing funds | Low | Status → 'rejected'; writes activity log |
| Blacklist NGO | Nuclear option for fraud/abuse | Low | Status → 'blacklisted'; freezes programs |
| Restore NGO from blacklist | Admin needs undo | Low | Operational |
| Blacklist student | Prevent duplicate applications, fraud | Low | Status → 'blacklisted' |
| Restore student | Admin needs undo | Low | Operational |
| Combined blacklist view | Single view of all suspended actors | Low | JOIN of blacklisted NGOs + students |

### NGO — Program + Student Operations

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| NGO dashboard (own stats) | NGO needs scoped view, not global | Medium | Scoped to own programs/students/invoices |
| Create scholarship program | Core product action | Low | Name, description, categories, budget, dates |
| List / get own programs | Manage running programs | Low | — |
| Update program | Fix typos, extend dates, adjust budget | Low | — |
| Register student manually | NGO enrolls students directly | Medium | Auto-generates `EDU-YYYY-XXXXX` scholarship ID; calls `blockchain.create_wallet()` |
| List / get students (own) | Track enrolled students | Low | Includes wallet balance from blockchain |
| View student applications | Applicants from student role | Low | Pending queue for review |
| Accept application → auto-create student | Convert approved applicant to student record | Medium | Triggers scholarship ID generation + wallet creation |
| Reject application | Communicate decision | Low | Status → 'rejected'; optional reason |
| View invoices from schools | NGO is the payer | Low | Scoped to own NGO/programs |
| Approve invoice | Triggers blockchain settlement | **High** | PATCH → calls `blockchain.settle_invoice()` → sets tx_hash; writes activity log |
| Reject invoice | Decline spurious or duplicate claims | Low | Status → 'rejected'; optional reason |
| Allocate funds to student/program | Core redistribution action | **High** | POST → calls `blockchain.allocate_funds()` → records tx_hash; updates student walletBalance; writes activity log |
| Allocation history | Audit + reconciliation | Low | — |

### DONOR — Browse + Donate

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Browse verified NGOs with stats | Donor selection UX | Low | Public-fields only; only verified NGOs shown |
| Browse active programs | Select donation target | Low | With NGO info joined |
| Browse students (direct support) | Student-level giving | Low | For targeted personal donations |
| Make donation | Core money movement | **High** | POST → calls `blockchain.donate()` → tx_hash recorded; updates NGO/program/student totals; writes activity log |
| Donation history (own) | Donor accountability | Low | — |
| Donation detail with fund flow | Transparency — "where did my money go?" | Medium | Show tx_hash + allocation chain; this is the killer feature for donors |

### SCHOOL — Partner Vendor

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Register as partner school | Entry to the system | Low | Status starts 'pending'; admin/NGO verifies |
| View own school profile | Self-service | Low | — |
| Submit invoice | Core revenue action for schools | Medium | Upload supporting document; link to program |
| List own invoices with status | Track payment pipeline | Low | Pending / approved / rejected |

### STUDENT — Application

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Browse active programs | Discovery | Low | Same public programs endpoint; authenticated |
| Submit scholarship application | Core student action | Low | Guardian info, reason, school details |
| View own application statuses | Track outcomes | Low | Pending / accepted / rejected |

### PUBLIC — Trust & Transparency

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Aggregate platform stats | External accountability ("where does money go?") | Low | Unauthenticated; mirrors `platformStats` |
| Recent activity feed | Real-time trust signal for donors and press | Low | Last N activity events; type-labeled |
| Verified NGOs list | Donor entry point before login | Low | Public fields only |
| Active programs list | Donor/student discovery before login | Low | Public fields only |

### CROSS-CUTTING — Infrastructure

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| File upload (supporting docs) | Invoice evidence, NGO registration docs | Medium | Upload → stored_path + file ID; local disk with S3-compatible interface |
| File download by ID | Retrieve stored documents | Low | Auth required; access-controlled |
| Activity log (write on all significant actions) | Platform-wide audit trail | Medium | Every donation, allocation, verify, invoice approval, blacklist writes a log entry |
| Blockchain mock layer (port-and-adapter) | Core architectural requirement | **High** | `create_wallet`, `donate`, `allocate_funds`, `settle_invoice`, `get_balance` — realistic tx hashes, simulated latency |
| Seed script (idempotent, matches mock.js) | FE works against real API from day 1 | Medium | Same IDs, same values, same relationships as `mock.js` — no FE changes permitted |
| camelCase API responses | FE contract — no exceptions | Medium | Pydantic v2 aliases on every schema field |
| Structured error format `{detail, code, statusCode}` | FE error handling consistency | Low | Global exception handler |
| Docker + Docker Compose | Reviewable, reproducible demo | Low | App + PostgreSQL |

---

## Differentiators (Competitive Advantage)

What separates EduTrack from any generic grant management platform. These are the UNICEF demo story.

### D1: Blockchain Transaction Hash on Every Money Movement

**What:** Every donation, allocation, and invoice settlement records a blockchain tx hash (Sui network) in the DB.

**Why it differentiates:** Standard platforms (Submittable, Blackbaud) track disbursements in a DB that only the platform owner can audit. EduTrack creates a *verifiable external record* — any skeptic can independently verify the tx hash on a public blockchain explorer. This is the trust model that makes sense for aid delivery in emerging markets where institutional trust is low.

**Confidence:** HIGH — PRD specifies this; UNICEF Venture Fund explicitly funds blockchain-for-impact projects; IATI standard's core use case is exactly this transparency.

**Complexity:** High (blockchain layer), though mock makes v1 tractable.

---

### D2: End-to-End Fund Flow Tracing (Donation → Allocation → Invoice → Settlement)

**What:** The donor detail view (`GET /donor/donations/{id}`) shows the full chain: donation tx_hash → which students/programs were funded → which invoices were settled for those students → final settlement tx_hash.

**Why it differentiates:** Most platforms show "you donated $X to NGO Y." EduTrack can show: "Your $5,000 funded Aarati Tamang's tuition at Shree Janapriya School (paid invoice inv-1, blockchain: 0xabc...def, 2026-02-05)." This is radical fund-flow transparency.

**Complexity:** Medium (JOIN across Donations → Students → Invoices with tx_hash fields).

---

### D3: Per-Student Scholarship Wallet with Balance

**What:** Each student has a blockchain wallet address + balance, not just a record in a ledger. Funds are allocated to the *student's wallet*, then drawn down by school invoices. The wallet balance is real-time queryable.

**Why it differentiates:** In traditional scholarship management, money flows NGO → school directly. The student is passive. EduTrack makes the student an economic principal — their wallet is the authorization source. This enables future direct-to-student disbursement (mobile money, digital tokens).

**Complexity:** High (wallet creation via blockchain, balance queries, allocation tracking against wallet).

---

### D4: Auto-Generated Human-Readable Scholarship ID (`EDU-YYYY-XXXXX`)

**What:** Every enrolled student gets a unique `EDU-2026-00142` style ID, generated from the year + sequential counter.

**Why it differentiates:** Creates a verifiable, portable identity for beneficiaries. A student can cite their scholarship ID to any partner school — the school can query the API to verify enrollment. This is the beginning of a digital beneficiary credential.

**Complexity:** Low (auto-generated on student creation, formatted from sequence).

---

### D5: Multi-Role Activity Feed (Public + Role-Scoped)

**What:** A real-time activity feed visible to the public showing recent donations, approvals, allocations, and program launches — labeled by event type and actor.

**Why it differentiates:** Platforms like Submittable are opaque to outsiders. EduTrack's public activity feed is the "open ledger" that earns public trust without requiring blockchain expertise. The pattern is borrowed from blockchain explorers but made human-readable.

**Complexity:** Low (activity log table + feed endpoint; types: donation | invoice | verify | allocation | program | blacklist).

---

### D6: Granular Donation Targeting (General / Program / Student)

**What:** Donors can give at three levels of specificity: (a) to an NGO generally, (b) to a specific program, or (c) directly to a named student.

**Why it differentiates:** Standard platforms accept general donations. Student-level targeted giving enables the "sponsor a child" model which is proven to drive higher donor engagement and retention. The tx_hash at each level makes the targeting verifiable.

**Complexity:** Medium (donation type enum, nullable FK chains in Donation model, fund routing logic in service layer).

---

### D7: NGO Lifecycle Governance (Pending → Verified → Blacklisted → Restored)

**What:** A full NGO state machine with Admin as gatekeeper. No verified = no programs = no funds.

**Why it differentiates:** Most grant platforms assume the grantee is already vetted. EduTrack's verification gate — requiring tax and registration documents — makes it a trusted infrastructure layer, not just a tool. This is table stakes for UNICEF deployment where NGO credibility is a legal and reputational concern.

**Complexity:** Low-medium (state machine + document upload + activity log).

---

## Anti-Features (Explicitly Defer)

Things to **not build** in v1. Each has a clear rationale. Not shortcuts — conscious scope decisions.

| Anti-Feature | Why Defer | What to Do Instead | Complexity If Built |
|---|---|---|---|
| Real Sui SDK calls to testnet/mainnet | Interface fully defined; one-file swap when ready | Mock returns realistic tx hashes; port-and-adapter ensures zero-change upgrade | High |
| Celery/Redis async task queue | Service layer is already async-ready | Run blockchain calls inline (mock is fast); Celery wrapper added next milestone | High |
| Automated test suite | Architecture (service layer isolation, DI) fully supports it | Ship structure now; tests in milestone 2 | Medium |
| Pagination + advanced filtering | Small demo dataset; FE doesn't request it | `?page=&limit=` + offset added when data grows | Low |
| Rate limiting | No traffic in grant demo | Nginx/gateway layer in production | Low |
| Email notifications | Not in FE contract; no email provider configured | Activity log is the notification mechanism for now | Medium |
| Donor KYC / AML checks | Regulatory requirement for real money; mock platform | Out-of-scope for grant demo; flag as v3 | High |
| Student grade/academic tracking | No FE views for it; not in mock.js | Scholarship ID + status is sufficient | Medium |
| Multi-language / i18n | Strings not hardcoded in logic; FE is English-only | i18n layer added after v1 launch | Medium |
| Role-based data export (CSV/PDF) | Not in mock.js; not in PRD | Ad-hoc exports added per stakeholder request | Medium |
| NGO-to-NGO fund transfers | Complex multi-party settlement; not in user stories | Single NGO owns each program | High |
| Recurring donations | Not in mock.js; no subscription model | One-time donations only for v1 | Medium |
| Volunteer management | Entirely separate domain from fund distribution | Salesforce for Nonprofits sells this separately for a reason | High |
| Impact measurement / outcomes | Post-award reporting; not in PRD | Defer to v2; IATI standard defines the data model | High |
| School-to-student direct payment | Bypasses NGO governance layer | Invoice → NGO approval → NGO allocates; schools never touch student wallets | High |
| Donor-to-student direct transfer | Bypasses NGO oversight | Donor → NGO → student wallet is the trust chain | Medium |
| Encryption at rest | Dev environment only | PostgreSQL TDE + field-level encryption in production | Medium |
| Multi-tenancy (multiple platforms) | Single Nepal deployment | Platform is single-tenant; multi-tenant is a SaaS pivot | High |

---

## Feature Dependencies

> Key rule: **a feature cannot be built before its dependencies exist.** These ordering constraints directly drive phase sequencing.

```
LEVEL 0 — Bootstrap (no dependencies)
└── Database schema + migrations (all models)
└── Docker + Docker Compose
└── Seed script (depends on schema)

LEVEL 1 — Auth foundation (depends on: User model)
└── POST /auth/register
└── POST /auth/login → JWT
└── POST /auth/refresh
└── POST /auth/logout
└── GET /auth/me
└── RBAC guard (FastAPI Depends)

LEVEL 2 — Entity registration (depends on: auth, migrations)
└── NGO registration (on auth/register for role=ngo)
└── School registration (POST /schools/register)
└── Donor profile creation (on auth/register for role=donor)
└── File upload (blocking: NGO reg docs, invoice docs)

LEVEL 3 — Admin governance (depends on: NGO registration, file upload)
└── Admin NGO list + verify/reject/blacklist/restore
└── Admin student blacklist/restore
└── Admin dashboard stats (depends on: all entity counts)

LEVEL 4 — Blockchain abstraction layer (independent, but blocks all money movement)
└── BlockchainService interface (Protocol)
└── MockSuiBlockchainService implementation
└── create_wallet() — blocks: student registration
└── donate() — blocks: donation endpoint
└── allocate_funds() — blocks: NGO allocation endpoint
└── settle_invoice() — blocks: invoice approval
└── get_balance() — blocks: student wallet display

LEVEL 5 — NGO operations (depends on: verified NGO, blockchain layer)
└── Create/list/update programs (depends on: verified NGO status)
└── Register student (depends on: program exists + blockchain.create_wallet())
└── NGO dashboard stats (depends on: programs, students, invoices exist)

LEVEL 6 — Student lifecycle (depends on: programs, NGO operations)
└── Student browse programs
└── Student apply (POST /student/apply)
└── Student view own applications
└── NGO view + accept/reject applications
    └── Accept → auto-create student record (depends on: blockchain.create_wallet())

LEVEL 7 — Fund flow (depends on: blockchain layer, donors, NGOs, students)
└── Donor donate (depends on: blockchain.donate(), verified NGO, optional program/student)
    └── Updates: NGO.totalFunded, Program.allocated, Student.walletBalance
└── NGO allocate funds (depends on: blockchain.allocate_funds(), student wallet exists)
    └── Updates: Student.walletBalance, Student.totalReceived

LEVEL 8 — School invoicing (depends on: verified school, program exists, blockchain layer)
└── School submit invoice (depends on: school registered + verified, program exists, file upload)
└── NGO view invoices
└── NGO approve invoice (depends on: blockchain.settle_invoice())
    └── Sets: Invoice.txHash, Invoice.approvedDate, Invoice.status='approved'
└── NGO reject invoice

LEVEL 9 — Activity log (depends on: all money movement events)
└── Written on: donation, allocation, invoice approval, NGO verify/blacklist, student blacklist
└── Public activity feed (GET /public/activity)

LEVEL 10 — Public endpoints (depends on: verified NGOs + programs + activity log)
└── GET /public/stats (depends on: all entity tables populated)
└── GET /public/activity (depends on: activity log)
└── GET /public/ngos (depends on: NGO table)
└── GET /public/programs (depends on: Program table)
```

### Critical Dependency Chains

**The Donor Flow** (hardest end-to-end path):
```
Schema → Auth → NGO register → Admin verify NGO
       → Donor register → Donor browse NGOs
       → Blockchain.donate() → tx_hash → Donation record
       → Activity log entry → Public feed
       → Donor detail: fund flow trace
```

**The Student Wallet Flow** (core value proposition):
```
Schema → NGO register → Admin verify → Program create
       → Student apply OR NGO manual-register
       → Blockchain.create_wallet() → wallet address stored
       → NGO allocate → Blockchain.allocate_funds()
       → Student.walletBalance updated → tx_hash recorded
       → School invoice submitted
       → NGO approve invoice → Blockchain.settle_invoice()
       → Invoice.txHash set → School paid
```

**The Invoice Settlement Chain**:
```
School register (pending) → [verification] → School verified
→ Program exists → School submits invoice + supporting doc (file upload)
→ NGO sees invoice → NGO approves → blockchain.settle_invoice()
→ Invoice.status='approved', Invoice.txHash set, Invoice.approvedDate set
→ Activity log: "Tuition invoice from X approved"
```

---

## Role-to-Feature Matrix

| Feature Area | Admin | NGO | Donor | School | Student | Public |
|---|---|---|---|---|---|---|
| Auth (register/login/me) | seed only | ✅ | ✅ | ✅ | ✅ | ❌ |
| Platform stats | ✅ | partial | ❌ | ❌ | ❌ | ✅ (aggregate) |
| NGO verify/blacklist | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| NGO dashboard | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Program CRUD | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Program browse | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ |
| Student register | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Student apply | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| Application review | ❌ | ✅ | ❌ | ❌ | view own | ❌ |
| Student blacklist | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Donate | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Browse NGOs/donors | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ (public) |
| Fund allocation | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Submit invoice | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Approve/reject invoice | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Activity feed | ✅ | partial | ❌ | ❌ | ❌ | ✅ |
| File upload/download | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |

---

## Complexity Summary

| Complexity Level | Features |
|---|---|
| **High** (cross-cutting, blockchain-dependent, or multi-step state transitions) | Blockchain abstraction layer, Donation with fund routing, Fund allocation to student wallet, Invoice approval with settlement, Application acceptance → auto-student record |
| **Medium** (multi-table, stat aggregation, or business logic) | NGO dashboard stats, Admin dashboard stats, Donation fund flow trace view, Student wallet balance query, Activity log writes, File upload+store, Seed script |
| **Low** (CRUD, status updates, simple queries) | Auth flows, NGO/school/student registration, Program CRUD, Application list/view, Invoice list/view, Public feed, Blacklist/restore operations |

---

## What Platforms in This Space Commonly Miss

These are patterns found across Submittable, Blackbaud, and CommunityForce customer complaints and post-mortem discussions. EduTrack should explicitly address or defer consciously:

1. **Opaque fund tracking after disbursement** — Money goes in, nobody knows where it went. EduTrack's tx_hash chain and fund-flow donor view directly addresses this. *EduTrack: solved by design.*

2. **No beneficiary voice** — Grant management systems track recipients as passive objects, not agents. EduTrack's student application flow and scholarship wallet give beneficiaries first-class status. *EduTrack: partially addressed in v1.*

3. **Siloed stakeholder views** — Donors can't see what NGOs do; NGOs can't see what schools do with money. EduTrack's role-scoped dashboards + public feed bridges these silos. *EduTrack: solved.*

4. **Document management chaos** — Invoice supporting docs and NGO registration docs stored in email or shared drives. EduTrack's file upload system with DB-linked records solves this. *EduTrack: solved.*

5. **No audit trail for status changes** — Who approved this? When? Grant platforms often have no logging. EduTrack's activity log captures actor + timestamp + type on every state transition. *EduTrack: solved.*

6. **Manual reconciliation** — Finance teams reconcile spreadsheets against the platform. EduTrack's tx_hash as the source of truth eliminates this for verified transactions. *EduTrack: future-solved when real blockchain; mock approximates.*

7. **Vendor lock-in for payments** — Submittable's Impact Wallet is a proprietary payment rail. EduTrack's Sui blockchain is an open, public rail — no vendor dependency. *EduTrack: structural advantage.*

8. **Missing fraud controls** — No mechanism to blacklist bad actors. EduTrack has NGO and student blacklisting with admin restore. *EduTrack: solved.*

---

## Sources

- **PRD (prd.md):** Primary specification — endpoints, data models, roles — HIGH confidence
- **User Stories (docs/End-to-End Product Flow):** Stakeholder intent — HIGH confidence
- **mock.js:** Canonical data shapes and field names — HIGH confidence (FE contract)
- **Submittable (funds-distribution):** Industry patterns for grant lifecycle — MEDIUM confidence (official product page)
- **Blackbaud Award Management:** Scholar management industry norms — MEDIUM confidence (official product page)
- **CommunityForce features page:** Multi-phase awards management lifecycle — MEDIUM confidence (official product page)
- **UNICEF Venture Fund:** Grant context and open-source/blockchain mandate — HIGH confidence (official page)
- **IATI Standard:** Aid transparency data model and stakeholder patterns — HIGH confidence (official standard body)
- **Salesforce Nonprofit Cloud:** Industry reference for stakeholder management, program/outcome management patterns — MEDIUM confidence (marketing page, some marketing inflation)
