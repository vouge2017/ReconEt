# ReconET Explainability Engine — Deep Design Plan

**Version:** 1.0
**Date:** June 23, 2026
**Purpose:** Build an explainability engine that speaks the language of Ethiopian finance professionals, auditors, and CFOs — grounded in IFRS, EFRS, AABE standards, and real-world accounting practice.

---

## 1. WHY EXPLAINABILITY IS THE #1 MOAT

### The Trust Problem
Ethiopian CFOs don't trust black-box matching. When a tool says "95% match," they ask:
- "WHY is it 95%?"
- "What if it's wrong?"
- "Can I defend this to the auditor?"
- "Can I explain this to the tax authority?"

### The Competitive Gap
No Chinese, Indian, or African reconciliation tool explains **WHY** transactions matched. They show confidence scores. That's it.

### ReconET's Answer
Every match gets a **plain-language explanation sentence** that:
- A CFO can read and understand in 5 seconds
- An auditor can use as working paper evidence
- A tax officer can accept as documentation
- Supports both English and Amharic

---

## 2. ACCOUNTING STANDARDS FRAMEWORK

### 2.1 IFRS Standards Relevant to Reconciliation

| Standard | Relevance to ReconET | Explainability Impact |
|----------|---------------------|----------------------|
| **IFRS 9** Financial Instruments | Classification of bank transactions, expected credit loss | Explain how loan auto-debits are treated |
| **IFRS 10** Consolidated Financial Statements | Intercompany elimination requirements | Explain why intercompany pairs are excluded from P&L |
| **IAS 21** Effects of Changes in Foreign Exchange Rates | FX transaction treatment, NBE rates | Explain cross-currency matches using NBE rates |
| **IAS 7** Statement of Cash Flows | Operating/financing/investing classification | Explain cash flow impact of matched transactions |
| **IAS 39** Financial Instruments: Recognition | Recognition timing, derecognition | Explain date-shifted matches |
| **IFRS 15** Revenue from Contracts | Revenue recognition timing | Explain revenue-related bank transactions |
| **IAS 1** Presentation of Financial Statements | Disclosure requirements | Explain what needs disclosure vs. auto-post |

### 2.2 Ethiopian-Specific Standards (AABE / EFRS)

**Ethiopia's Accounting Framework:**
- AABE (Accounting and Auditing Board of Ethiopia) mandates IFRS adoption
- EFRS = Ethiopian Financial Reporting Standards (IFRS-based with local modifications)
- SMEs can use IFRS for SMEs (simplified)

**Key Ethiopian Compliance Points:**
| Requirement | Source | Explainability Impact |
|-------------|--------|----------------------|
| NBE reporting | National Bank of Ethiopia | FX transactions must reference NBE daily rate |
| VAT reconciliation | Ethiopian Revenue Authority | VAT-bearing transactions need tax explanation |
| Withholding tax | Income Tax Proclamation | Withholding deductions need documentation |
| Period-end deadlines | Ethiopian fiscal year (Jul 7 - Jul 6) | Period lock explanations |
| Audit trail | AABE audit requirements | Every match must be traceable |

### 2.3 Audit Documentation Standards

**What Auditors Need (ISA 230 / PCAOB AS 2201):**
1. **Nature** — What was matched
2. **Timing** — When the transactions occurred
3. **Extent** — How many transactions, what amount
4. **Evidence** — Source documents referenced
5. **Reasoning** — Why the match is valid

**ReconET must generate audit-ready explanations that satisfy these requirements.**

---

## 3. EXPLAINABILITY ENGINE ARCHITECTURE

### 3.1 Core Components

```
┌─────────────────────────────────────────────────────────┐
│                 EXPLAINABILITY ENGINE                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  Match       │  │  Context    │  │  Language    │     │
│  │  Analyzer    │→ │  Enricher   │→ │  Generator   │     │
│  │             │  │             │  │             │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│         │               │               │               │
│         ▼               ▼               ▼               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  Confidence  │  │  Accounting │  │  Bilingual   │     │
│  │  Scorer      │  │  Treatment  │  │  Output      │     │
│  │             │  │  Classifier │  │  (EN/AM)     │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Explanation Sentence Structure

**Template Pattern:**
```
[TRANSACTION_ID] matched [TRANSACTION_ID] because:
1. [AMOUNT_REASON]
2. [DATE_REASON]
3. [REFERENCE_REASON]
4. [ACCOUNTING_TREATMENT]
5. [COMPLIANCE_NOTE] (if applicable)
```

**Example (English):**
```
Bank Txn CBE-2026-06-0045 matched GL Entry JE-2026-06-0123 because:
1. Amount: ETB 45,000.00 matches exactly
2. Date: Bank date Jun 15, GL date Jun 14 (1-day bank processing lag)
3. Reference: CBE ref "INV-2026-0089" matches GL description "Payment INV-2026-0089"
4. Treatment: Revenue recognition under IFRS 15 — recognized when payment received
5. Compliance: No VAT applicable (export revenue, zero-rated)
Confidence: 95%
```

**Example (Amharic):**
```
የባንክ ግብይት CBE-2026-06-0045 ከመዝገብ JE-2026-06-0123 ጋር ተገናኝቷል ምክንያቱም:
1. መጠን: ብር 45,000.00 በትክክል ይዛመዳል
2. ቀን: የባንክ ቀን ሰኔ 15፣ የመዝገብ ቀን ሰኔ 14 (የባንክ ማቀድ ቀን)
3. ማጣቀሻ: CBE "INV-2026-0089" ከመዝገብ "ክፍያ INV-2026-0089" ጋር ይዛመዳል
4. ማካተት: በIFRS 15 ረገድ ገቢ — ክፍያ በተቀበለ ጊዜ ይመዘገባል
5. ትብብር: የተጨማሪ እሴት ታክስ (VAT) አይተገበይም (ወጪ ገቢ፣ ዜሮ ተመን)
መረጃ: 95%
```

---

## 4. MATCH TYPE EXPLANATIONS — DEEP DESIGN

### 4.1 Exact 1:1 Match (99% Confidence)

**What It Is:** Amount, date, and reference all match exactly.

**Accounting Treatment:**
- Auto-post to GL
- No adjustment needed
- Recognized in correct period

**Explanation Components:**
```
{
  "matchType": "exact_1to1",
  "confidence": 99,
  "explanation": {
    "amount": "ETB {amount} matches exactly between bank and GL",
    "date": "Transaction date {bank_date} matches GL date {gl_date}",
    "reference": "Bank reference '{bank_ref}' matches GL description '{gl_desc}'",
    "treatment": "Auto-posted to GL — no adjustment required",
    "accounting_standard": "IFRS 9.3.1.1 — Financial asset recognized at fair value",
    "audit_trail": "Match ID {match_id} created at {timestamp} by {user}",
    "compliance": null
  }
}
```

**Ethiopian Context Additions:**
- If CBE: Note Amharic column normalization
- If NBE regulated: Reference NBE directive
- If fiscal year boundary: Note Jul 7 year-end rule

### 4.2 Date-Shifted Match (82% Confidence)

**What It Is:** Amount matches, but date differs by 1-3 days (bank processing lag).

**Accounting Treatment:**
- Review queue (not auto-posted)
- May need period adjustment if crosses month-end
- IFRS 9 recognition timing question

**Explanation Components:**
```
{
  "matchType": "date_shifted",
  "confidence": 82,
  "explanation": {
    "amount": "ETB {amount} matches exactly",
    "date": "Bank date {bank_date} is {days_diff} day(s) after GL date {gl_date}",
    "date_reason": "Typical bank processing lag for {bank_name}",
    "reference": "Bank ref '{bank_ref}' matches GL desc '{gl_desc}'",
    "treatment": "Review required — verify period assignment",
    "accounting_standard": "IAS 39.14 — Derecognition when rights to cash flows expire",
    "period_impact": "{period_status}",
    "audit_trail": "Pending review — Match ID {match_id}"
  }
}
```

**Period Impact Logic:**
- If same month: "Same period — no adjustment needed"
- If crosses month-end: "Crosses period boundary — verify correct period assignment"
- If crosses fiscal year: "⚠️ Crosses Ethiopian fiscal year (Jul 7) — requires CFO approval"

### 4.3 One-to-Many Match (74% Confidence)

**What It Is:** One bank transaction matches multiple GL entries (grouped deposits, batch payments).

**Accounting Treatment:**
- Always requires confirmation
- Verify sum equals
- Check all components are legitimate

**Explanation Components:**
```
{
  "matchType": "1_to_many",
  "confidence": 74,
  "explanation": {
    "amount": "Bank txn ETB {bank_amount} = sum of {count} GL entries (ETB {gl_total})",
    "breakdown": [
      {"gl_id": "JE-001", "amount": 15000, "desc": "Invoice INV-001"},
      {"gl_id": "JE-002", "amount": 20000, "desc": "Invoice INV-002"},
      {"gl_id": "JE-003", "amount": 10000, "desc": "Invoice INV-003"}
    ],
    "date": "Bank date {bank_date} vs GL dates {gl_dates}",
    "treatment": "Confirm grouping — verify all components are valid",
    "accounting_standard": "IFRS 15.105 — Recognize revenue when performance obligation satisfied",
    "audit_trail": "Requires manual confirmation — Match ID {match_id}"
  }
}
```

### 4.4 Intercompany Match (95% Confidence)

**What It Is:** Transfer between two accounts of the same company.

**Accounting Treatment:**
- Auto-exclude from P&L (IFRS 10 requirement)
- Record as intercompany transfer
- Eliminate in consolidation

**Explanation Components:**
```
{
  "matchType": "intercompany",
  "confidence": 95,
  "explanation": {
    "amount": "ETB {amount} — internal transfer between {from_account} and {to_account}",
    "type": "Intercompany transfer — not external revenue/expense",
    "treatment": "Auto-excluded from P&L — recorded as balance sheet transfer",
    "accounting_standard": "IFRS 10.B86 — Eliminate intra-group transactions in consolidation",
    "compliance": "Consolidation entry — does not affect group profit",
    "audit_trail": "Auto-classified as intercompany — Match ID {match_id}"
  }
}
```

**IFRS 10 Elimination Language:**
"In preparing consolidated financial statements, an entity must eliminate intra-group balances, transactions, income and expenses, and resulting unrealized gains/losses."

### 4.5 FX Cross-Currency Match (97% Confidence)

**What It Is:** Transaction in foreign currency matched using NBE exchange rate.

**Accounting Treatment:**
- Use NBE daily rate for translation
- Record FX gain/loss (IAS 21)
- Document rate source and date

**Explanation Components:**
```
{
  "matchType": "fx_cross_currency",
  "confidence": 97,
  "explanation": {
    "amount": "USD {foreign_amount} × NBE rate {rate} = ETB {local_amount}",
    "rate_source": "NBE daily indicative rate — {rate_date}",
    "date": "Transaction date {txn_date}, rate date {rate_date}",
    "fx_impact": "FX {gain_loss} of ETB {difference} recognized",
    "treatment": "Translated at spot rate per IAS 21",
    "accounting_standard": "IAS 21.21 — Translate at spot rate on transaction date",
    "compliance": "NBE directive compliance — documented rate source",
    "audit_trail": "FX match with NBE rate — Match ID {match_id}"
  }
}
```

**IAS 21 Requirements:**
- Initial recognition at spot rate on transaction date
- Subsequent measurement at closing rate for monetary items
- Exchange differences in profit or loss

### 4.6 Loan Auto-Debit Match (99% Confidence)

**What It Is:** Automatic loan repayment deducted by bank.

**Accounting Treatment:**
- Auto-post (matches loan schedule)
- Split: principal (balance sheet) + interest (P&L)
- Verify against amortization schedule

**Explanation Components:**
```
{
  "matchType": "loan_auto_debit",
  "confidence": 99,
  "explanation": {
    "amount": "ETB {amount} — automatic loan repayment",
    "breakdown": {
      "principal": "ETB {principal} — reduces loan balance (IAS 32)",
      "interest": "ETB {interest} — expense recognized (IFRS 9)",
      "total": "ETB {total} — matches loan schedule"
    },
    "date": "Debit date {debit_date} matches schedule date {schedule_date}",
    "treatment": "Auto-posted — principal to balance sheet, interest to P&L",
    "accounting_standard": "IFRS 9.4.2.2 — Amortized cost measurement",
    "audit_trail": "Loan schedule match — Match ID {match_id}"
  }
}
```

---

## 5. CONFIDENCE SCORING SYSTEM

### 5.1 Scoring Factors

| Factor | Weight | Scoring Logic |
|--------|--------|---------------|
| Amount match | 40% | Exact = 100, ±0.1% = 95, ±1% = 80, ±5% = 60 |
| Date match | 25% | Same day = 100, 1 day = 90, 2 days = 80, 3 days = 70 |
| Reference match | 20% | Exact = 100, partial = 70, fuzzy = 50, none = 0 |
| Pattern match | 15% | Known pattern = 100, similar = 70, new = 30 |

### 5.2 Confidence Thresholds

| Confidence | Action | Explanation Language |
|------------|--------|---------------------|
| 95-100% | Auto-post | "High confidence — auto-posted" |
| 80-94% | Review recommended | "Good match — review recommended" |
| 60-79% | Review required | "Possible match — review required" |
| Below 60% | Manual match only | "Low confidence — manual verification needed" |

### 5.3 Override Impact on Confidence

When a user overrides a match:
- Log the override reason
- Adjust future confidence for similar patterns
- Build pattern library for learning loop (Phase 2)

---

## 6. ACCOUNTING TREATMENT CLASSIFIER

### 6.1 Transaction Categories

| Category | GL Impact | IFRS Reference | Explanation |
|----------|-----------|----------------|-------------|
| Revenue | Credit P&L | IFRS 15 | "Revenue recognized when performance obligation satisfied" |
| Expense | Debit P&L | IAS 1.88 | "Expense recognized when incurred" |
| Loan Principal | Balance Sheet | IAS 32 | "Loan liability reduced" |
| Loan Interest | Debit P&L | IFRS 9 | "Finance cost recognized" |
| Intercompany | Balance Sheet | IFRS 10 | "Eliminated in consolidation" |
| FX Gain/Loss | P&L | IAS 21 | "Exchange difference recognized in profit or loss" |
| Tax Payment | Balance Sheet | IAS 12 | "Tax liability settled" |
| Capital | Balance Sheet | IAS 1 | "Capital contribution/withdrawal" |

### 6.2 Ethiopian-Specific Categories

| Category | Tax Treatment | Explanation |
|----------|--------------|-------------|
| VAT-bearing sale | 15% VAT | "VAT of ETB {vat_amount} applicable — {vat_rate}% standard rate" |
| Withholding tax | 2-10% WHT | "Withholding tax of ETB {wht_amount} — {wht_rate}% on {service_type}" |
| Export revenue | 0% VAT | "Zero-rated export — no VAT" |
| Import duty | Variable | "Import duty per Ethiopian Customs Commission" |
| NBE regulated | Compliance | "NBE directive {directive_number} applicable" |

---

## 7. BILINGUAL OUTPUT SYSTEM

### 7.1 Translation Framework

**Key Accounting Terms (English → Amharic):**

| English | Amharic | Transliteration |
|---------|---------|-----------------|
| Reconciliation | ማስታረቅ | Masitarik |
| Match | ግባና / መገናኛ | Gebana / Megnagna |
| Transaction | ግብይት | Gibrit |
| Balance | ቀሪ | Keri |
| Debit | ድ nợ | Dino |
| Credit | እዳ | Ida |
| Audit | ምርመራ | Mirmera |
| Period | ወቅት | Wekit |
| Amount | መጠን | Meten |
| Reference | ማጣቀሻ | Matakesha |
| Account | ሂሳብ | Hisab |
| Bank | ባንክ | Bank |
| Cash | ገንዘብ | Genzeb |
| Revenue | ገቢ | Gebi |
| Expense | ወጪ | Wechi |
| Profit | ትርፍ | Tirif |
| Loss | ኪሳ | Kisa |
| Tax | ታክስ | Taks |
| VAT | የተጨማሪ እሴት ታክስ | Yetechamari Iset Taks |
| Withholding | መቀበር | Mekeber |

### 7.2 Explanation Templates

**English Template:**
```
{bank_txn_id} matched {gl_entry_id} because:
• Amount: {amount_reason}
• Date: {date_reason}
• Reference: {reference_reason}
• Treatment: {accounting_treatment}
• Compliance: {compliance_note}
Confidence: {confidence}%
```

**Amharic Template:**
```
{bank_txn_id} ከ{gl_entry_id} ጋር ተገናኝቷል ምክንያቱም:
• መጠን: {amount_reason_am}
• ቀን: {date_reason_am}
• ማጣቀሻ: {reference_reason_am}
• ማካተት: {accounting_treatment_am}
• ትብብር: {compliance_note_am}
መረጃ: {confidence}%
```

---

## 8. AUDIT TRAIL INTEGRATION

### 8.1 What the Audit Trail Must Capture

Per ISA 230 and AABE requirements:

| Field | Purpose | Example |
|-------|---------|---------|
| Match ID | Unique identifier | MAT-2026-06-0045 |
| Timestamp | When match was made | 2026-06-15T14:30:00Z |
| User | Who made/confirmed the match | user:cfo@company.com |
| Match type | How it was matched | exact_1to1 |
| Confidence | Score at match time | 99 |
| Explanation | Full explanation text | "ETB 45,000 matches exactly..." |
| Override | If overridden, why | null or "Wrong period assignment" |
| Period | Accounting period | 2026-06 |
| Bank source | Which bank file | CBE_Jun2026.csv |
| GL source | Which GL file | Peachtree_GL_Jun2026.txt |

### 8.2 Export Format

Audit trail exports to Excel with columns:
```
| Match ID | Timestamp | User | Bank Txn | GL Entry | Amount | Type | Confidence | Explanation | Override Reason | Period |
```

---

## 9. ANOMALY EXPLANATIONS

### 9.1 Anomaly Types and Explanations

| Anomaly | Detection | Explanation |
|---------|-----------|-------------|
| Amount spike | >2x average | "ETB {amount} is {multiplier}x the average transaction of ETB {avg}. Verify large payment." |
| New account | Not in history | "Account {account} not previously used. Verify new vendor/customer." |
| Weekend transaction | Sat/Sun | "Transaction on {date} ({day_name}). Ethiopian banks typically process on business days." |
| Duplicate amount | Same amount, same day | "Two transactions of ETB {amount} on {date}. Verify if duplicate or legitimate." |
| Round number | Exact thousands | "Round amount ETB {amount}. Verify if estimate or actual." |

### 9.2 Compliance Anomalies

| Anomaly | Standard | Explanation |
|---------|----------|-------------|
| Missing VAT | Ethiopian tax law | "Sale of ETB {amount} without VAT. Verify if exempt or zero-rated." |
| WHT missing | Income Tax Proclamation | "Payment to vendor without withholding tax. Verify if exempt." |
| FX without NBE rate | NBE directive | "FX transaction without NBE rate reference. Document rate source." |

---

## 10. IMPLEMENTATION PLAN

### Phase 1: Core Explainability (Week 1-2)
- [ ] Implement explanation sentence generator for all 6 match types
- [ ] Build confidence scoring with weighted factors
- [ ] Create English explanation templates
- [ ] Integrate with existing matching engine

### Phase 2: Accounting Context (Week 3-4)
- [ ] Add accounting treatment classifier
- [ ] Implement IFRS standard references
- [ ] Add Ethiopian compliance notes (VAT, WHT, NBE)
- [ ] Build period impact analyzer

### Phase 3: Bilingual Output (Week 5-6)
- [ ] Create Amharic translation database
- [ ] Implement bilingual explanation generator
- [ ] Add Amharic accounting terminology
- [ ] Test with native speakers

### Phase 4: Audit Integration (Week 7-8)
- [ ] Build audit trail export with explanations
- [ ] Add anomaly explanations
- [ ] Create CFO summary report
- [ ] Implement explanation search/filter

---

## 11. SUCCESS METRICS

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Explanation clarity | >90% CFO approval | User testing with Ethiopian finance officers |
| Audit readiness | 100% traceable | External auditor review |
| Amharic accuracy | >95% correct | Native speaker review |
| Processing speed | <100ms per explanation | Performance testing |
| User trust | >85% auto-post acceptance | Usage analytics |

---

## 12. COMPETITIVE ADVANTAGE SUMMARY

| Feature | ReconET | BlackLine | Indian Tools | Chinese Tools |
|---------|---------|-----------|--------------|---------------|
| Plain-language explanation | ✅ Yes | ❌ No | ❌ No | ❌ No |
| Amharic support | ✅ Yes | ❌ No | ❌ No | ❌ No |
| Ethiopian compliance | ✅ Yes | ❌ No | ❌ No | ❌ No |
| IFRS standard references | ✅ Yes | ✅ Partial | ❌ No | ❌ No |
| Audit-ready documentation | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| Peachtree integration | ✅ Yes | ❌ No | ❌ No | ❌ No |

---

## 13. NEXT STEPS

1. **Review this plan** — Confirm direction
2. **Start Phase 1** — Build core explanation generator
3. **Test with sample data** — Use CBE, Dashen, Peachtree samples
4. **Get CFO feedback** — Show explanations to Ethiopian finance professionals
5. **Iterate** — Refine language based on feedback

---

*This plan ensures ReconET's Explainability Engine is not just a feature — it's the reason Ethiopian CFOs choose ReconET over any alternative.*
