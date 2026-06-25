# ReconET — Accountant Interview Questions

**Purpose:** Validate ReconET's assumptions against real-world accounting practices  
**Audience:** Accountants / CFOs who reconcile CBE bank statements  
**Date:** June 2026

---

## 🔍 Section 1: How They Currently Reconcile

**1. Walk me through your month-end reconciliation process. What are the exact steps?**
- _Goal: Understand the manual workflow we're replacing_

**2. How long does reconciliation take you each month? How many hours per person?**
- _Goal: Quantify the time savings we can offer_

**3. What's the hardest part of reconciliation? What takes the most time?**
- _Goal: Identify the real pain point (is it fees? volume? matching?)_

**4. How many bank accounts do you reconcile? Which banks?**
- _Goal: Confirm CBE is primary, understand multi-bank scope_

**5. What software do you use today? Excel? Peachtree? Something else?**
- _Goal: Know what we're competing against_

---

## 💰 Section 2: Fee Handling (The Critical Feature)

**6. When you pay a vendor ETB 100,000 and the bank charges ETB 25 fee + ETB 15 tax — how do you record this in your books?**
- _Option A: One entry for ETB 100,040 (lump sum)_
- _Option B: Three entries — Vendor 100,000 + Bank Charges 25 + Tax 15_
- _Option C: Two entries — Vendor 100,000 + Bank Charges 40_
- _Goal: Know which matching strategy (NET/GROSS/SPLIT) to use_

**7. Do you have a "Bank Charges" or "Bank Fees" GL account? What's the account number?**
- _Goal: Map fee extraction to actual GL accounts_

**8. How do you handle ATM withdrawal fees? The bank deducts ETB 2-12 per withdrawal — do you track these separately?**
- _Goal: Validate fee patterns found in real statements (1,002 = 1,000 + 2)_

**9. Have bank fees ever changed without notice? How did you discover it?**
- _Goal: Understand if tariff DB needs to be user-configurable_

**10. Do you reconcile fees as part of the main transaction, or separately at month-end?**
- _Goal: Know if fee matching should be inline or batch_

---

## 📄 Section 3: Bank Statement Format

**11. How do you get your CBE statement? Corporate portal? Branch printout? Email?**
- _Goal: Confirm PDF is the primary format (not CSV)_

**12. Does the corporate portal offer CSV/Excel export? Have you ever used it?**
- _Goal: If CSV exists, we should support it too_

**13. Your statement has 8 columns: Date, Particulars, Reference, Narrative, Value Date, Debit, Credit, Balance — does this match what you see?**
- _Goal: Validate our format assumption_

**14. What do the reference codes mean to you? FT, TT, CHQ, CD — do you use these to classify transactions?**
- _Goal: Validate reference code handling_

**15. Do you use Ethiopian fiscal year (Meskerem–Pagume) or Gregorian (Jan–Dec)?**
- _Goal: Configure calendar handling_

---

## 📊 Section 4: Matching & Exceptions

**16. What percentage of your transactions match automatically today? What's left unmatched?**
- _Goal: Set our >90% match rate target against reality_

**17. When a transaction doesn't match, what's usually the reason?**
- _Options: Fees / Date lag / Amount difference / Missing entry / Duplicate_
- _Goal: Prioritize matching engine improvements_

**18. How do you handle cheques? How many per month? How long until they clear?**
- _Goal: Validate cheque tracking feature priority_

**19. Have you ever had a stale cheque (uncleared for 90+ days)? What happened?**
- _Goal: Validate stale cheque detection threshold_

**20. Do you have intercompany transfers between your own accounts? How do you handle these?**
- _Goal: Know if we need intercompany matching logic_

---

## 🔧 Section 5: GL Data & ERP

**21. What ERP/accounting system do you use? Peachtree? NYLOS? Something else?**
- _Goal: Know which GL export formats to support_

**22. Can your ERP export GL data? What format? CSV? Excel?**
- _Goal: Build the right GL import path_

**23. What fields does your GL export include? Date, account code, description, debit, credit, reference?**
- _Goal: Map GL columns to our schema_

**24. How many GL entries do you have per month? (Rough count)**
- _Goal: Size the matching engine performance requirements_

---

## 🎯 Section 6: Value & Willingness to Pay

**25. If a tool could cut your reconciliation time by 80%, what would that be worth to you?**
- _Goal: Validate pricing / willingness to pay_

**26. Who would approve purchasing such a tool? You? Your CFO? IT?**
- _Goal: Know the decision maker_

**27. Would you be willing to pilot this tool with your next month-end close?**
- _Goal: Get a pilot commitment_

**28. Can I watch you reconcile next month-end? (Screen share or in person)**
- _Goal: Get observational access for UX design_

---

## 🚀 Section 7: Quick Validation (Yes/No Rapid Fire)

| # | Question | Answer |
|---|----------|--------|
| 29 | You reconcile monthly, not weekly? | |
| 30 | You have >50 transactions per month? | |
| 31 | You've had at least one reconciliation error this year? | |
| 32 | You use CBE as your primary bank? | |
| 33 | You've heard of NYLOS ERP? | |
| 34 | You'd pay ETB 5,000/month for this tool? | |

---

## 📝 Post-Interview Notes Template

```
Interviewee: _______________
Company: _______________
Role: _______________
Date: _______________

Key Findings:
1. _______________
2. _______________
3. _______________

Surprises:
- _______________

Follow-up needed:
- _______________
```

---

## 🎤 How to Run the Interview

1. **Start with Section 1** (5 min) — warm up, understand their world
2. **Spend most time on Section 2** (15 min) — this is our differentiator
3. **Quick pass on Sections 3-4** (10 min) — validate assumptions
5. **Section 5** (5 min) — know what ERP to integrate
6. **End with Section 6** (5 min) — gauge willingness to pay
7. **Rapid fire Section 7** (2 min) — quick stats

**Total: ~40 minutes**

**Recording:** Ask permission to record. If no, take detailed notes.
**Demo:** Have a working demo ready to show if they're interested.
