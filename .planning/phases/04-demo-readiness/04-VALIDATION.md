---
phase: 4
slug: demo-readiness
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None (automated test suite is v2; manual + curl smoke tests for this phase) |
| **Config file** | none — Wave 0 delivers new files, not test config |
| **Quick run command** | `curl -s http://localhost:8000/api/public/stats` |
| **Full suite command** | Manual browser walkthrough: all 15 routes, all 5 roles |
| **Estimated runtime** | ~5 minutes manual |

---

## Sampling Rate

- **After every task commit:** Run the task-specific curl command listed below
- **After every plan wave:** Manual browser walkthrough for affected routes
- **Before `/gsd-verify-work`:** Full docker compose up → seed → all 15 routes verified
- **Max feedback latency:** ~2 minutes per task (curl checks)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | PUBL-01, PUBL-02, PUBL-03, PUBL-04, ACTV-02 | smoke | `curl -s http://localhost:8000/api/public/stats \| python3 -m json.tool` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | INFRA-06 | smoke | `python scripts/seed.py && python scripts/seed.py` (run twice — no error) | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | APIC-03 | smoke | Open browser at `http://localhost:5173` — public dashboard loads | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 2 | APIC-03 | smoke | Navigate all 15 routes — no JS console errors | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 3 | BLKC-05 | manual | `cd contracts && sui move build` (must succeed) | ❌ W0 | ⬜ pending |
| 04-03-02 | 03 | 3 | INFRA-06 | smoke | `docker compose up -d && sleep 5 && curl -s http://localhost:8000/api/public/stats` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

All deliverables are new files created by the plans themselves — no pre-existing test scaffold needed:

- [ ] `scripts/seed.py` — created in Plan 04-01
- [ ] `app/schemas/public.py` — created in Plan 04-01
- [ ] `app/services/public_service.py` — created in Plan 04-01
- [ ] `app/api/public.py` (filled) — populated in Plan 04-01
- [ ] `OpenScholar/src/data/api.js` — created in Plan 04-02
- [ ] `OpenScholar/src/data/mock.js` (rewritten) — Plan 04-02
- [ ] `contracts/Move.toml` — created in Plan 04-03
- [ ] `contracts/sources/scholarship.move` — created in Plan 04-03
- [ ] `.env.example` — created in Plan 04-03

*Existing infrastructure covers backend route registration — `app/main.py` already registers `public.router`.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Frontend all 15 pages render without errors | APIC-03 | Browser visual — no headless test suite | Open `http://localhost:5173`, navigate each route in nav, check browser console for JS errors |
| Role switching works with token cache | APIC-03 | Interactive — requires clicking navbar role switcher | Switch from admin → NGO → donor → back to admin; verify each role shows correct dashboard |
| Seed idempotency — no duplicates on second run | INFRA-06 | Requires running seed twice and inspecting DB | `python scripts/seed.py && python scripts/seed.py`; check `SELECT COUNT(*) FROM ngos` = 5 |
| `sui move build` passes | BLKC-05 | Requires Sui CLI installed | `cd contracts && sui move build` — zero errors or warnings |
| Activity feed relative times are correct | ACTV-02 | Visual/time-dependent | Public dashboard activity section shows "2 hours ago", "5 hours ago", etc. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
