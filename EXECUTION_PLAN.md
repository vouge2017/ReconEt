# ReconET — Execution Plan

**Date:** June 25, 2026  
**Goal:** Close critical gaps, build for real users, ship a pilot-ready product

---

## THE BIG PICTURE

We have a working PDF parser and matching engine. What we're missing is the **connective tissue** — the stuff that turns a tech demo into a product accountants actually use.

**Three phases:**
1. **Foundation** (Week 1-2) — Close critical gaps, make it usable
2. **Product** (Week 3-4) — Build for real accountant workflows
3. **Pilot** (Week 5-6) — Get it in front of real users

---

## PHASE 1: FOUNDATION (Week 1-2)

_Goal: Make it deployable, testable, and safe to use_

### 1.1 Excel Export [P0 — Day 1-2]

**Problem:** Accountants live in Excel. No export = no adoption.

**Solution:**
- After reconciliation, export matched/unmatched transactions to .xlsx
- Include columns: Date, Description, Reference, Bank Amount, GL Amount, Match Status, Confidence, Fee Breakdown
- Add "Download Excel" button on reconciliation results page
- Use `openpyxl` library (already in Python ecosystem)

**Who needs this:** Accountants, CFOs, auditors

**Files to create/modify:**
- `backend/app/api/reconciliation.py` — add export endpoint
- `backend/app/engine/excel_exporter.py` — new file
- `frontend/src/pages/Reconciliation.tsx` — add download button

---

### 1.2 Automated Tests [P0 — Day 2-3]

**Problem:** Financial product without tests is a liability.

**Solution:**
- Unit tests for CMap extractor (all 3 real PDFs)
- Unit tests for fee extraction (known patterns)
- Unit tests for matching engine (exact, date-shifted, fuzzy)
- Integration test: upload PDF → get matches → verify balance
- Use pytest, store test data in `data/real_cbe_samples/`

**Who needs this:** Us (development confidence), auditors (if they ask)

**Files to create:**
- `backend/tests/test_cmap_extractor.py`
- `backend/tests/test_fee_extractor.py`
- `backend/tests/test_matching.py`
- `backend/tests/test_integration.py`
- `backend/pytest.ini`

---

### 1.3 JWT Authentication [P0 — Day 3-4]

**Problem:** Can't deploy without auth. Multi-user needs login.

**Solution:**
- Simple JWT auth: register, login, get token
- Roles: `clerk` (upload + view), `cfo` (approve + export), `auditor` (read-only)
- Protect all API endpoints
- Use `python-jose` + `passlib`

**Who needs this:** Everyone — security baseline

**Files to create/modify:**
- `backend/app/api/auth.py` — new file
- `backend/app/models/user.py` — new file
- `backend/app/main.py` — add auth middleware
- `frontend/src/pages/Login.tsx` — new file

---

### 1.4 Error Handling & Logging [P0 — Day 4-5]

**Problem:** When something fails, we don't know why.

**Solution:**
- Structured logging (JSON format) for all extraction/parsing steps
- User-friendly error messages (not stack traces)
- Failed transaction tracking (why did parsing fail?)
- Log to file + console

**Who needs this:** Us (debugging), support team (future)

**Files to modify:**
- `backend/app/engine/cmap_extractor.py` — add logging
- `backend/app/adapters/cbe_pdf.py` — add logging
- `backend/app/main.py` — configure logging

---

## PHASE 2: PRODUCT (Week 3-4)

_Goal: Build features accountants actually need_

### 2.1 GL Account Mapping [P1 — Day 8-10]

**Problem:** We extract fees but don't know which GL account to debit.

**Solution:**
- Simple mapping table: `fee_type → GL account code`
- Default mappings (Bank Charges = 6xxx, Tax = 7xxx)
- User can configure per company
- When fee is extracted, auto-suggest GL account

**Who needs this:** Accountants, CFOs

**Data model:**
```sql
CREATE TABLE gl_account_mappings (
    id UUID PRIMARY KEY,
    company_id UUID REFERENCES companies(id),
    fee_type VARCHAR(50),  -- bank_charge, gov_tax, wht
    gl_account_code VARCHAR(20),
    gl_account_name VARCHAR(255),
    is_default BOOLEAN DEFAULT false
);
```

**Files to create:**
- `backend/app/engine/gl_mapper.py`
- `backend/app/api/gl_mappings.py`
- `frontend/src/pages/GLMappings.tsx`

---

### 2.2 Withholding Tax (WHT) Tracking [P1 — Day 10-11]

**Problem:** 2% WHT on bank fees is not tracked. Tax compliance gap.

**Solution:**
- Detect WHT patterns in bank statements
- Track WHT separately from VAT
- Include in fee breakdown
- Add WHT summary to reports

**Who needs this:** Accountants, tax officers

**Files to modify:**
- `backend/app/engine/fee_extractor.py` — add WHT patterns
- `backend/app/engine/excel_exporter.py` — add WHT column

---

### 2.3 Exception Reporting [P1 — Day 11-13]

**Problem:** When transactions don't match, we need to know why.

**Solution:**
- Categorize unmatched transactions:
  - Amount mismatch (fees not extracted?)
  - Date mismatch (>3 days lag?)
  - Missing GL entry
  - Missing bank transaction
  - Duplicate
- Generate exception report (Excel + on-screen)
- Show suggested fixes

**Who needs this:** Accountants (daily), auditors (monthly)

**Files to create:**
- `backend/app/engine/exception_reporter.py`
- `backend/app/api/exceptions.py`
- `frontend/src/pages/Exceptions.tsx`

---

### 2.4 Period Lock [P1 — Day 13-14]

**Problem:** Without period lock, users can backdate matches.

**Solution:**
- Company can lock a period (e.g., "January 2026 is closed")
- Locked periods: no new matches, no edits
- Only CFO/admin can unlock
- Audit trail for lock/unlock actions

**Who needs this:** CFOs, auditors

**Data model:**
```sql
CREATE TABLE periods (
    id UUID PRIMARY KEY,
    company_id UUID REFERENCES companies(id),
    period_month INTEGER,
    period_year INTEGER,
    status VARCHAR(20) DEFAULT 'open',  -- open, locked
    locked_by UUID REFERENCES users(id),
    locked_at TIMESTAMP
);
```

**Files to create:**
- `backend/app/api/periods.py`
- `frontend/src/components/PeriodLock.tsx`

---

### 2.5 Executive Dashboard [P1 — Day 14-16]

**Problem:** CFOs don't want to see transactions — they want summaries.

**Solution:**
- Dashboard showing:
  - Total matched vs unmatched (pie chart)
  - Match rate trend (line chart)
  - Outstanding cheques (count + amount)
  - Fee summary (total fees paid this month)
  - Exception count by category
- Simple, clean, one-page view

**Who needs this:** CFOs, finance managers

**Files to create:**
- `frontend/src/pages/Dashboard.tsx`
- `backend/app/api/dashboard.py`

---

## PHASE 3: PILOT (Week 5-6)

_Goal: Get real users, validate, iterate_

### 3.1 Multi-Bank Support [P2 — Day 22-25]

**Problem:** Only CBE works. 35 other Ethiopian banks exist.

**Solution:**
- Get sample statements from Dashen, Awash
- Build adapters (same pattern as CBE — CMap or text extraction)
- Auto-detect bank from statement content
- Priority: Dashen (Mastercard partner), Awash (largest private)

**Who needs this:** Any company banking with non-CBE banks

**Files to create:**
- `backend/app/adapters/dashen_pdf.py`
- `backend/app/adapters/awash_pdf.py`

---

### 3.2 Reconciliation Report [P2 — Day 25-27]

**Problem:** Need a printable/shareable report for management review.

**Solution:**
- Generate PDF report with:
  - Company name, period, account
  - Summary: matched X, unmatched Y, total fees Z
  - Detailed match list with explanations
  - Exception list with suggested actions
  - Signature line for approval
- Export as PDF

**Who needs this:** CFOs (sign-off), auditors (evidence)

**Files to create:**
- `backend/app/engine/report_generator.py`
- `backend/app/api/reports.py`

---

### 3.3 User Roles & Permissions [P2 — Day 27-28]

**Problem:** Clerk, CFO, and auditor see different things.

**Solution:**
- **Clerk:** Upload PDF, view matches, flag exceptions
- **CFO:** All clerk actions + approve matches, lock periods, export reports
- **Auditor:** Read-only view of all data, audit trail access

**Who needs this:** All organizations with >1 person

**Files to modify:**
- `backend/app/api/auth.py` — add role checks
- `frontend/src/components/RoleGuard.tsx`

---

### 3.4 Pilot Onboarding [P2 — Day 28-30]

**Problem:** Need to make it easy for first users to start.

**Solution:**
- Onboarding wizard:
  1. Create company
  2. Add bank accounts
  3. Upload first statement
  4. Review matches
  5. Export to Excel
- Sample data pre-loaded for demo
- Video walkthrough (screen recording)

**Who needs this:** First pilot users

---

## PRIORITY MATRIX

```
                    URGENT
                      │
         ┌────────────┼────────────┐
         │            │            │
         │  Excel     │  JWT Auth  │
         │  Export    │            │
         │            │  Tests     │
IMPORTANT├────────────┼────────────┤ LESS IMPORTANT
         │            │            │
         │  GL Map    │  Dashboard │
         │  WHT       │  Multi-bank│
         │  Exceptions│  Reports   │
         │  Period    │  Roles     │
         │  Lock      │  Onboarding│
         │            │            │
         └────────────┼────────────┘
                      │
                   NOT URGENT
```

**Do First (Week 1-2):** Excel Export → Tests → Auth → Logging  
**Do Next (Week 3-4):** GL Mapping → WHT → Exceptions → Period Lock → Dashboard  
**Do Later (Week 5-6):** Multi-bank → Reports → Roles → Onboarding

---

## WHAT EACH USER GETS

### Accountant (Clerk)
| Feature | Phase | Impact |
|---|---|---|
| Upload PDF → auto-parse | ✅ Done | Saves 2-3 hours/month |
| Fee-aware matching | ✅ Done | 90%+ match rate |
| Excel export | Phase 1 | Can share with team |
| Exception list | Phase 2 | Know what's unmatched |
| GL account suggestions | Phase 2 | Faster journal entries |

### CFO
| Feature | Phase | Impact |
|---|---|---|
| Executive dashboard | Phase 2 | One-glance status |
| Match approval | Phase 2 | Control over accuracy |
| Period lock | Phase 2 | Prevent backdating |
| Reconciliation report | Phase 3 | Sign-off document |
| Fee summary | Phase 2 | Know bank costs |

### Auditor
| Feature | Phase | Impact |
|---|---|---|
| Audit trail | ✅ Done | Full traceability |
| Read-only access | Phase 3 | No accidental edits |
| Exception reports | Phase 2 | Focus review areas |
| Supporting evidence | Phase 3 | Attach statements |
| Confidence scores | ✅ Done | Trust the matches |

### Tax Officer
| Feature | Phase | Impact |
|---|---|---|
| VAT tracking | ✅ Done | 15% VAT on fees |
| WHT tracking | Phase 2 | 2% WHT on fees |
| Fee breakdown | ✅ Done | Full transparency |
| Export to tax format | Phase 3 | ERCA compliance |

---

## TECHNICAL DEPENDENCIES

### Phase 1 Dependencies
```
Excel Export    → openpyxl (pip install)
Tests           → pytest (pip install)
Auth            → python-jose, passlib (pip install)
Logging         → built-in logging module
```

### Phase 2 Dependencies
```
GL Mapping      → database tables (PostgreSQL)
WHT             → fee_extractor.py updates
Exceptions      → matching engine output
Dashboard       → Chart.js or Recharts (frontend)
Period Lock     → database tables + auth middleware
```

### Phase 3 Dependencies
```
Multi-bank      → sample statements from Dashen/Awash
Reports         → ReportLab or WeasyPrint (PDF generation)
Roles           → auth middleware extension
Onboarding      → frontend wizard components
```

---

## RISK REGISTER

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Accountants reject Excel format | Medium | High | Show mockup before building |
| CBE changes PDF format | Low | High | CMap extractor is adaptable |
| Token/auth too complex for users | Medium | Medium | Keep it simple, social login later |
| Performance with large statements | Medium | Medium | Test with 100+ page PDFs |
| No pilot users found | Low | High | Use accountant interview contacts |
| Competitor enters market | Low | Medium | Move fast, build relationships |

---

## SUCCESS METRICS

### Phase 1 (Foundation)
- [ ] Excel export works for all 3 real PDFs
- [ ] >80% test coverage on core engine
- [ ] Auth works (register, login, token)
- [ ] All errors logged with context

### Phase 2 (Product)
- [ ] GL mapping configurable per company
- [ ] WHT detected and tracked
- [ ] Exception report categorizes all unmatched
- [ ] Period lock prevents backdating
- [ ] Dashboard shows key metrics

### Phase 3 (Pilot)
- [ ] At least 2 banks supported
- [ ] Reconciliation report generates PDF
- [ ] 3 user roles working
- [ ] 1 pilot company onboarded
- [ ] Feedback collected and prioritized

---

## DAILY STANDUP FORMAT

```
What I did yesterday:
- [list]

What I'm doing today:
- [list]

Blockers:
- [list or "none"]
```

---

## WEEKLY REVIEW

Every Friday:
1. What shipped this week?
2. What's blocking us?
3. Are we on track for pilot?
4. What did we learn from users?
5. What's the priority for next week?

---

*"Plan the work. Work the plan. Adjust when reality hits."*
