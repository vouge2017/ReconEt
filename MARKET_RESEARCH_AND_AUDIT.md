# ReconET — Market Research & Expert Audit

**Date:** June 25, 2026  
**Purpose:** Map the ecosystem, learn from other markets, audit our product against expert standards

---

## PART 1: Ethiopian Market Ecosystem

### 🏛️ Regulatory Bodies & Institutions

| Institution | Role | Relevance to ReconET | Contact/Website |
|---|---|---|---|
| **NBE (National Bank of Ethiopia)** | Central bank, regulates all banks | Sets fee structures, bank directives, FX rules | nbe.gov.et |
| **AABE (Accounting & Auditing Board of Ethiopia)** | Sets accounting standards | IFRS adoption, audit requirements | aabe.gov.et |
| **ERCA (Ethiopian Revenue & Customs Authority)** | Tax collection, customs | VAT on bank fees, tax compliance | erca.gov.et |
| **Ethiopian Insurance Corporation** | Insurance regulation | Not directly relevant | — |
| **Ministry of Finance** | Government fiscal policy | Public sector accounting | mof.gov.et |

### 🏦 Banks (MVP Target: CBE, Dashen, Awash)

| Bank | Market Share | Corporate Customers | Digital Maturity | Statement Format |
|---|---|---|---|---|
| **CBE** | Largest (state-owned) | Thousands | Medium — portal exists, PDF only | 8-column PDF (confirmed) |
| **Dashen Bank** | Top 5 private | Growing | High — Mastercard partner | Unknown — need sample |
| **Awash Bank** | Top 3 private | Large corporate base | High — digital transformation focus | Unknown — need sample |
| **Abyssinia Bank** | Mid-size | SME focus | Medium | Unknown |
| **Wegagen Bank** | Mid-size | Growing | Medium | Unknown |
| **Telebirr (Ethio Telecom)** | Mobile money | Consumer/SME | Very high (mobile) | Different — mobile receipts |

**Key Insight:** NBE published directive SBB/99/2026 for bank branches in Special Economic Zones — banks are expanding. Corporate banking is growing.

### 📚 Accounting & IFRS in Ethiopia

**AABE Status:**
- Ethiopia is **actively adopting IFRS** (confirmed by IFRS Foundation jurisdiction page)
- AABE is the official body responsible for IFRS implementation
- IFRS for SMEs is being rolled out — many Ethiopian SMEs still use cash-basis or local GAAP
- **Gap:** IFRS adoption is incomplete — many accountants still work with Ethiopian GAAP + IFRS hybrid

**What This Means for ReconET:**
- Our explainability engine must support **both IFRS references AND local Ethiopian accounting terms**
- Amharic explanations are not a nice-to-have — they're essential for many users
- Accountants may not understand IFRS terminology — we need plain-language explanations

### 💰 Tax & Fee Structure

**VAT on Bank Fees:**
- Ethiopia charges **15% VAT** on most financial services
- Bank fees are subject to **Withholding Tax (WHT)** at 2% for companies
- The ETB 25 fee + ETB 15 tax pattern we see in statements = ETB 25 bank charge + ETB 15 (which is 15% of some base, possibly the transaction amount, not the fee itself)

**Customs (ERCA):**
- Customs duty calculations are complex (different rates for different goods)
- Not directly relevant to bank reconciliation, but **import-related bank payments** need customs reference matching
- ERCA has digital systems for duty payment — could be a future integration

### 📊 NBE Directives Relevant to ReconET

| Directive | Topic | Impact |
|---|---|---|
| FXD/01/2024 + amendments | Foreign exchange | FX transactions need reconciliation |
| Interest Rate directives | Rate caps | Affects interest calculations |
| SBB/99/2026 | Bank branches in SEZ | New corporate customers coming |
| Payment System directives | Digital payments | More electronic transactions |

---

## PART 2: What We Can Learn From Other Markets

### 🇮🇳 India — The Closest Parallel

**Why India is the best reference:**
- Similar developing economy challenges
- Complex tax system (GST = like Ethiopia's VAT)
- Banks embed fees in transactions (like CBE)
- Large accounting profession (Chartered Accountants)

**What Indian CAs Use:**
- **ClearTax GST** — reconciliation, invoicing, e-invoice readiness
- **Tally Prime** — dominant ERP for SMEs, has bank reconciliation
- **Zoho Books** — cloud accounting with AI OCR
- **Vyapar** — mobile-first for small businesses

**What We Can Learn:**
1. **GST reconciliation** is a massive pain point in India — they match invoice-by-invoice
2. **ClearTax** succeeded by focusing on ONE problem (GST filing) then expanding
3. **Tally** dominates because it's offline-first (important for Ethiopia where internet is unreliable)
4. Indian CAs use **AI OCR** for bank statement extraction — exactly what we're building

**Key Lesson:** Start with the hardest problem (fee-aware matching), nail it, then expand.

### 🇰🇪 Kenya — Mobile-First Market

**Why Kenya matters:**
- M-Pesa changed everything — most transactions are mobile
- SMEs reconcile M-Pesa + bank + cash weekly
- Pesapal, Flutterwave are payment processors with reconciliation

**What We Can Learn:**
1. **M-Pesa reconciliation** is a solved problem in Kenya — they match mobile money to bank
2. Kenyan SMEs reconcile **weekly**, not monthly — faster cycle = more automation value
3. **Pesapal** started as a payment processor, added reconciliation as a feature
4. Kenya's fintech ecosystem is 5-10 years ahead of Ethiopia

**Key Lesson:** When Ethiopia's mobile money (Telebirr) matures for corporate use, we'll need to reconcile those too.

### 🇦🇪 UAE — Enterprise Grade

**Why UAE matters:**
- Ethiopian diaspora businesses operate in both countries
- UAE has mature banking infrastructure
- Many Ethiopian businesses use UAE banks for trade finance

**What We Can Learn:**
1. UAE banks offer **API-based statement download** (CSV, JSON) — not just PDF
2. Enterprise reconciliation uses **SAP/Oracle** with bank feed integration
3. **Cloud accounting** (Xero, Zoho) dominates — bank feeds are automated
4. UAE's corporate banking is what Ethiopia will look like in 5-10 years

**Key Lesson:** Build for PDF now, but design the architecture so API integration is easy later.

### 🇬🇧 England — The Gold Standard

**Why England matters:**
- IFRS was essentially created here (IASB is London-based)
- UK accounting software (Sage, Xero) sets global standards
- Open Banking API regulations force banks to share data

**What We Can Learn:**
1. **Sage** dominates UK SME accounting — it has robust bank reconciliation
2. **Open Banking** means UK apps can directly access bank data — no PDF parsing needed
3. UK accountants expect **real-time reconciliation**, not month-end batch
4. **Making Tax Digital (MTD)** forced all UK businesses to use digital records

**Key Lesson:** Ethiopia will eventually move toward digital-first. Our PDF parser is a bridge, not the destination.

### 🇿🇦 South Africa — Most Similar to Ethiopia

**Why South Africa matters:**
- Most similar banking structure to Ethiopia
- Sage dominates (same as what Ethiopian accountants use)
- Complex tax system (VAT + customs + payroll tax)

**What We Can Learn:**
1. **Sage Evolution/Pastel** is widely used — has built-in reconciliation
2. South African accountants still do **manual matching** despite having Sage
3. **Bank statement import** (CSV/OFX) is standard — but many still use PDF
4. Compliance with SARS (tax authority) drives software adoption

**Key Lesson:** Even with existing software, reconciliation is still painful. There's room for a specialized tool.

---

## PART 3: Expert Audit — Is ReconET Built Like a Professional Product?

### 🔍 Audit Checklist

We're building a treasury reconciliation platform. Let's ask: **would a team of experts in each field build it this way?**

#### 1. Banking & Treasury Expert

| Aspect | Current State | Expert Verdict |
|---|---|---|
| Bank statement parsing | ✅ CMap extractor for CBE | ✅ Good — handles real format |
| Fee extraction | ✅ 4 patterns built | ⚠️ Need to validate with real accountant |
| Multi-bank support | ⚠️ Only CBE built | ⚠️ Need Dashen/Awash samples |
| Foreign exchange | ❌ Not built | ❌ Needed — FX transactions exist |
| Cheque tracking | ✅ Built | ✅ Good — Ethiopian businesses use cheques |
| Balance verification | ✅ Hard gate | ✅ Good — prevents bad data |

**Gap:** No FX reconciliation. Ethiopian businesses import goods — those payments involve FX.

#### 2. Accounting & IFRS Expert

| Aspect | Current State | Expert Verdict |
|---|---|---|
| IFRS references | ✅ Explainer engine | ✅ Good — but need local GAAP too |
| Amharic support | ✅ Built | ✅ Essential for Ethiopian users |
| GL account mapping | ❌ Not built | ❌ Critical — need to map bank fees to GL accounts |
| Journal entry generation | ❌ Not built | ❌ Nice-to-have — auto-create journal entries |
| Period closing | ❌ Not built | ⚠️ Need period lock functionality |
| Audit trail | ✅ Database schema | ✅ Good |

**Gap:** No GL account mapping. When we extract a fee, we need to know which GL account to debit.

#### 3. Tax & Compliance Expert

| Aspect | Current State | Expert Verdict |
|---|---|---|
| VAT on bank fees | ✅ 15% VAT extracted | ✅ Good |
| Withholding tax | ❌ Not built | ⚠️ 2% WHT on fees — should track |
| Customs references | ❌ Not built | ⚠️ Import payments need customs matching |
| ERCA integration | ❌ Not built | ❌ Future — auto-file tax returns |
| Transfer pricing | ❌ Not built | ❌ Not needed for MVP |

**Gap:** WHT on bank fees is not tracked. This matters for tax compliance.

#### 4. Audit & Assurance Expert

| Aspect | Current State | Expert Verdict |
|---|---|---|
| Audit trail | ✅ Schema built | ✅ Good |
| Match confidence scores | ✅ 90-95% exact, 73-82% date-shifted | ✅ Good — auditors need this |
| Exception reporting | ⚠️ Basic | ⚠️ Need detailed exception reports |
| Supporting evidence | ❌ Not built | ❌ Need to attach bank statements to matches |
| Period lock | ❌ Not built | ⚠️ Prevents backdating |

**Gap:** No supporting evidence attachment. Auditors need to trace every match back to source.

#### 5. Software Engineering Expert

| Aspect | Current State | Expert Verdict |
|---|---|---|
| Architecture | ✅ Clean separation (adapter/engine/API) | ✅ Good |
| Error handling | ⚠️ Basic | ⚠️ Need comprehensive error handling |
| Testing | ⚠️ Only manual | ❌ Need automated tests |
| Security | ✅ CORS, file limits, logging | ⚠️ Need JWT auth, rate limiting |
| Performance | ❌ Not tested | ⚠️ Need load testing with real data |
| Documentation | ✅ Good docs | ✅ Good |

**Gap:** No automated tests. For a financial product, this is a risk.

#### 6. UX/Product Expert

| Aspect | Current State | Expert Verdict |
|---|---|---|
| Upload flow | ✅ Built | ✅ Good |
| Match review UI | ⚠️ Basic | ⚠️ Need drag-and-drop matching |
| Dashboard | ❌ Not built | ❌ Need executive dashboard |
| Mobile support | ❌ Not built | ⚠️ Ethiopian managers use phones |
| Export (Excel) | ❌ Not built | ❌ Critical — accountants live in Excel |
| User roles | ❌ Not built | ⚠️ Need clerk vs CFO vs auditor views |

**Gap:** No Excel export. This alone could kill adoption.

---

## PART 4: Critical Gaps Summary

### 🔴 Must-Fix Before Pilot (P0)

1. **Excel export** — Accountants will reject without this
2. **GL account mapping** — Connect bank fees to GL accounts
3. **Automated tests** — Financial product needs test coverage
4. **JWT authentication** — Can't deploy without auth

### 🟡 Should-Fix Before Launch (P1)

5. **Dashen/Awash adapters** — Multi-bank support
6. **WHT tracking** — Tax compliance
7. **Exception reports** — Auditors need these
8. **Period lock** — Prevent backdating

### 🟢 Nice-to-Have (P2)

9. **FX reconciliation** — For import businesses
10. **Mobile dashboard** — For managers on the go
11. **API integration** — Future-proofing
12. **ERCA integration** — Auto-file tax returns

---

## PART 5: Key People & Organizations to Engage

### In Ethiopia

| Who | Why | How to Reach |
|---|---|---|
| **AABE** (Accounting & Auditing Board) | IFRS adoption guidance, accountant network | aabe.gov.et |
| **ESCPA** (Ethiopian Society of Certified Public Accountants) | Accountant community, training | LinkedIn, events |
| **CBE Corporate Banking Division** | Statement format, API access | CBE branches |
| **Dashen Bank Treasury** | Statement samples, partnership | Bank contacts |
| **Awash Bank IT** | Digital transformation, integration | Bank contacts |
| **Ethiopian Chamber of Commerce** | Business network, events | eacci.org |
| **Addis Ababa University (Accounting Dept)** | Academic research, student interns | Direct contact |

### Internationally

| Who | Why |
|---|---|
| **IFRS Foundation** | IFRS for SMEs implementation guidance |
| **World Bank (Ethiopia office)** | Financial inclusion programs, funding |
| **IMF (Ethiopia office)** | Macro-economic context, reform timeline |
| **Kenya fintech community** | Learn from M-Pesa reconciliation |
| **Indian CA community** | Learn from GST reconciliation tools |

---

## PART 6: Competitive Landscape

### Direct Competitors in Ethiopia
**None.** No Ethiopian-built bank reconciliation tool exists.

### Indirect Competitors

| Tool | Used By | Strength | Weakness | Our Advantage |
|---|---|---|---|---|
| **Excel** | Everyone | Flexible, free | Manual, error-prone | Automation |
| **Sage** | Medium+ companies | Full ERP | Expensive, no fee matching | Fee-aware matching |
| **Peachtree** | Small companies | Cheap | No bank integration | PDF parsing |
| **ERPNext** | Tech companies | Free, open source | Generic, no Ethiopian bank support | CBE-specific |
| **Tally** | Indian diaspora | Strong accounting | Not adapted for Ethiopia | Local focus |
| **NYLOS** | Ethiopian ERP | Local | Limited, no reconciliation | Specialized tool |

### International Benchmarks

| Tool | Market | What They Do Well | What We Can Learn |
|---|---|---|---|
| **ClearTax** | India | GST reconciliation, AI OCR | Focus on one pain point |
| **Xero** | Global | Bank feeds, cloud-first | API-first architecture |
| **Sage** | UK/SA | Full ERP, compliance | Enterprise features |
| **Tally** | India | Offline-first, SME focus | Reliability |
| **Pesapal** | Kenya | Payment + reconciliation | Integration approach |

---

## PART 7: The Honest Assessment

### What We're Doing Well
1. **Real data-driven** — We analyzed actual CBE statements, not assumptions
2. **Fee-aware matching** — No competitor does this
3. **CMap extraction** — Solved a real technical problem
4. **Clean architecture** — Separation of concerns is good
5. **Ethiopian calendar** — Built-in, not bolted-on

### What's Missing (Honest)
1. **No accountant on the team** — We're guessing about GL accounts, WHT, period closing
2. **No auditor on the team** — We don't know what auditors actually need
3. **No tax expert** — We're assuming 15% VAT is the only fee tax
4. **No UX designer** — The UI is functional, not delightful
5. **No automated tests** — A financial product without tests is risky
6. **Only 1 bank** — CBE is 1 of 36 Ethiopian banks

### What Would a Professional Team Have?

A team building this properly would include:
- **1 Treasury/Banking expert** — Knows bank operations, fee structures
- **1 CPA/Accountant** — Knows IFRS, GL mapping, period closing
- **1 Tax specialist** — Knows VAT, WHT, customs
- **1 Auditor** — Knows what audit evidence looks like
- **1 Backend engineer** — Builds the engine
- **1 Frontend engineer** — Builds the UI
- **1 UX designer** — Makes it usable
- **1 QA engineer** — Tests everything

**We have:** 1 AI assistant doing all of this. That's both amazing and a risk.

---

## PART 8: Recommended Next Steps

### This Week
1. ✅ CMap extractor — DONE
2. ✅ Accountant questions — DONE
3. ⬜ Get Dashen/Awash statement samples
4. ⬜ Add Excel export (P0)
5. ⬜ Add basic automated tests

### Next Week
6. ⬜ Run accountant interviews (use the questions)
7. ⬜ Add GL account mapping
8. ⬜ Add JWT authentication
9. ⬜ Add WHT tracking

### Month 2
10. ⬜ Dashen/Awash adapters
11. ⬜ Exception reporting
12. ⬜ Period lock
13. ⬜ Pilot with 1-2 companies

---

*"The best product is built by listening to users, not by guessing what they need."*
