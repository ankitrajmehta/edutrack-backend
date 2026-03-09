---
status: complete
phase: 03-fund-flow
source: [03-01-SUMMARY.md, 03-02-SUMMARY.md, 03-03-SUMMARY.md, 03-04-SUMMARY.md]
started: 2026-03-10T00:25:00Z
updated: 2026-03-10T00:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running server/service. Clear ephemeral state (temp DBs, caches, lock files). Start the application from scratch. Server boots without errors, any seed/migration completes (alembic upgrade head), and a primary query (health check, homepage load, or basic API call) returns live data.
result: pass

### 2. Create Donation (Donor)
expected: As an authenticated donor, POST to /donations with an amount. The server calls the blockchain before committing, returns a donation response with a transaction hash, and logs the activity. The response includes the donation ID, amount, and tx_hash.
result: pass

### 3. List Donations (Donor — ownership scoped)
expected: As an authenticated donor, GET /donations returns only that donor's own donations — not donations from other donors. The list is scoped to the authenticated user's donor_id.
result: pass

### 4. Get Donation Detail with Fund-Flow Chain
expected: As an authenticated donor, GET /donations/{id} returns a DonationDetailResponse that includes the base donation fields PLUS an allocations list and an invoices list showing the full fund-flow chain. Requesting another donor's donation ID returns a 403 Forbidden.
result: pass

### 5. NGO List Invoices
expected: As an authenticated NGO user, GET /invoices returns only that NGO's invoices (scoped by ngo_id). Invoices from other NGOs do not appear.
result: pass

### 6. NGO Approve Invoice
expected: As an authenticated NGO user, POST/PATCH to approve an invoice with status=pending triggers blockchain settlement (tx_hash returned), then the invoice status changes to approved/settled. Attempting to approve a non-pending invoice returns a validation error.
result: pass

### 7. NGO Reject Invoice
expected: As an authenticated NGO user, rejecting an invoice changes its status to rejected with no blockchain call. The operation completes without a tx_hash.
result: pass

### 8. NGO Create Allocation
expected: As an authenticated NGO user, creating an allocation (targeting a student_id OR program_id) calls blockchain.allocate_funds() before the DB commit. The student's wallet balance is updated, and the allocation record is returned with an amount and tx_hash.
result: pass

### 9. NGO List Allocations
expected: As an authenticated NGO user, GET /allocations returns only that NGO's allocations (scoped by ngo_id). Allocations from other NGOs do not appear.
result: pass

### 10. School Create Invoice
expected: As an authenticated school user, POST /invoices with a list of line items (each with an amount) creates an invoice with status=pending. The invoice's total amount is computed server-side from the sum of items — not taken from client input. The school's total_invoiced counter is incremented.
result: pass

### 11. School List Invoices
expected: As an authenticated school user, GET /invoices returns only that school's own invoices (scoped by school_id). Invoices from other schools do not appear.
result: pass

### 12. Ownership Enforcement (Cross-entity access denied)
expected: A donor attempting to access another donor's donation detail gets 403. An NGO attempting to approve/reject an invoice belonging to a different NGO gets 403. These ownership checks are consistently enforced across all fund-flow endpoints.
result: pass

## Summary

total: 12
passed: 12
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
