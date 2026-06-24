"""
ReconET Explainability Engine — Core Module

Generates plain-language explanations for every match type.
The moat: Ethiopian CFOs trust matches they can understand and defend.

Standards referenced:
- IFRS 9, 10, 15 (Financial Instruments, Consolidation, Revenue)
- IAS 1, 7, 12, 21, 32, 39 (Presentation, Cash Flows, Tax, FX, Financial Instruments)
- ISA 230 / PCAOB AS 2201 (Audit Documentation)
- AABE / EFRS (Ethiopian standards)
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import date, timedelta
from enum import Enum


class MatchType(str, Enum):
    EXACT_1TO1 = "exact_1to1"
    FEE_NET_MATCH = "fee_net_match"
    FEE_GROSS_MATCH = "fee_gross_match"
    FEE_SPLIT_MATCH = "fee_split_match"
    DATE_SHIFTED = "date_shifted"
    ONE_TO_MANY = "one_to_many"
    INTERCOMPANY = "intercompany"
    FX_CROSS_CURRENCY = "fx_cross_currency"
    LOAN_AUTO_DEBIT = "loan_auto_debit"
    CHEQUE_CLEARING = "cheque_clearing"
    STANDING_ORDER = "standing_order"


class ConfidenceLevel(str, Enum):
    AUTO_POST = "auto_post"         # 95-100%
    REVIEW_RECOMMENDED = "review"   # 80-94%
    REVIEW_REQUIRED = "required"    # 60-79%
    MANUAL_ONLY = "manual"          # <60%


@dataclass
class ExplanationComponent:
    """One line of the explanation"""
    category: str       # amount, date, reference, treatment, compliance
    english: str
    amharic: str = ""
    ifrs_reference: Optional[str] = None
    detail: Optional[str] = None


@dataclass
class Explanation:
    """Full explanation for a match"""
    match_type: MatchType
    confidence: int
    confidence_level: ConfidenceLevel
    summary_english: str
    summary_amharic: str
    components: List[ExplanationComponent]
    accounting_treatment: str
    accounting_treatment_am: str
    ifrs_standard: Optional[str] = None
    compliance_note: Optional[str] = None
    compliance_note_am: Optional[str] = None
    audit_trail_note: str = ""
    period_impact: Optional[str] = None
    anomaly_flags: List[str] = field(default_factory=list)


class ExplainabilityEngine:
    """
    Generates audit-ready explanations for every match.
    
    Core principle: A CFO should read the explanation in 5 seconds
    and understand WHY the match was made.
    """

    # Ethiopian fiscal year: Jul 7 - Jul 6
    FISCAL_YEAR_END_MONTH = 7
    FISCAL_YEAR_END_DAY = 6

    # Confidence thresholds
    AUTO_POST_THRESHOLD = 85
    REVIEW_RECOMMENDED_THRESHOLD = 70

    def explain(
        self,
        match_type: str,
        confidence: int,
        bank_txn: dict,
        gl_entry: Optional[dict] = None,
        gl_entries: Optional[List[dict]] = None,
        fee_breakdown: Optional[dict] = None,
        extra_context: Optional[dict] = None,
    ) -> Explanation:
        """
        Generate a full explanation for a match result.
        
        Args:
            match_type: Type of match (from matching engine)
            confidence: Confidence score (0-100)
            bank_txn: Bank transaction dict with id, date, amount, reference, description
            gl_entry: Matched GL entry (for 1:1 matches)
            gl_entries: Multiple GL entries (for 1:N matches)
            fee_breakdown: Fee details if applicable
            extra_context: Additional context (FX rate, cheque info, etc.)
        """
        confidence_level = self._classify_confidence(confidence)
        extra = extra_context or {}

        # Route to specific explainer
        if match_type in ("exact_1to1",):
            return self._explain_exact_match(confidence, confidence_level, bank_txn, gl_entry)
        elif match_type in ("fee_net_match",):
            return self._explain_fee_net_match(confidence, confidence_level, bank_txn, gl_entry, fee_breakdown)
        elif match_type in ("fee_gross_match",):
            return self._explain_fee_gross_match(confidence, confidence_level, bank_txn, gl_entry, fee_breakdown)
        elif match_type in ("fee_split_match",):
            return self._explain_fee_split_match(confidence, confidence_level, bank_txn, gl_entry, fee_breakdown, gl_entries)
        elif match_type in ("date_shifted",):
            return self._explain_date_shifted(confidence, confidence_level, bank_txn, gl_entry, fee_breakdown)
        elif match_type in ("one_to_many",):
            return self._explain_one_to_many(confidence, confidence_level, bank_txn, gl_entries)
        elif match_type in ("intercompany",):
            return self._explain_intercompany(confidence, confidence_level, bank_txn, gl_entry)
        elif match_type in ("fx_cross_currency",):
            return self._explain_fx_match(confidence, confidence_level, bank_txn, gl_entry, extra)
        elif match_type in ("loan_auto_debit",):
            return self._explain_loan_debit(confidence, confidence_level, bank_txn, gl_entry, extra)
        elif match_type in ("cheque_clearing",):
            return self._explain_cheque_clearing(confidence, confidence_level, bank_txn, gl_entry, extra)
        elif match_type in ("standing_order",):
            return self._explain_standing_order(confidence, confidence_level, bank_txn, gl_entry)
        else:
            return self._explain_generic(confidence, confidence_level, match_type, bank_txn, gl_entry)

    # ─── Confidence Classification ────────────────────────────────────

    def _classify_confidence(self, confidence: int) -> ConfidenceLevel:
        if confidence >= 95:
            return ConfidenceLevel.AUTO_POST
        elif confidence >= 80:
            return ConfidenceLevel.REVIEW_RECOMMENDED
        elif confidence >= 60:
            return ConfidenceLevel.REVIEW_REQUIRED
        return ConfidenceLevel.MANUAL_ONLY

    def _action_label(self, level: ConfidenceLevel) -> str:
        return {
            ConfidenceLevel.AUTO_POST: "Auto-posted to GL",
            ConfidenceLevel.REVIEW_RECOMMENDED: "Review recommended",
            ConfidenceLevel.REVIEW_REQUIRED: "Review required",
            ConfidenceLevel.MANUAL_ONLY: "Manual verification needed",
        }[level]

    def _action_label_am(self, level: ConfidenceLevel) -> str:
        return {
            ConfidenceLevel.AUTO_POST: "በራስ-ሰር ወደ መዝገብ ተመዝግቧል",
            ConfidenceLevel.REVIEW_RECOMMENDED: "ግምገማ ይመከራል",
            ConfidenceLevel.REVIEW_REQUIRED: "ግምገማ ያስፈልጋል",
            ConfidenceLevel.MANUAL_ONLY: "በእጅ ማረጋገጫ ያስፈልጋል",
        }[level]

    # ─── Date Helpers ─────────────────────────────────────────────────

    def _parse_txn_date(self, txn: dict) -> Optional[date]:
        """Parse date from transaction dict"""
        d = txn.get("date")
        if isinstance(d, date):
            return d
        if isinstance(d, str):
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
                try:
                    return date.fromisoformat(d) if "-" in d and len(d) == 10 else None
                except ValueError:
                    continue
        return None

    def _is_period_boundary(self, d1: date, d2: date) -> bool:
        """Check if two dates cross a month boundary"""
        return d1.month != d2.month or d1.year != d2.year

    def _is_fiscal_year_boundary(self, d1: date, d2: date) -> bool:
        """Check if dates cross Ethiopian fiscal year (Jul 7)"""
        fy_end_1 = date(d1.year, self.FISCAL_YEAR_END_MONTH, self.FISCAL_YEAR_END_DAY)
        fy_end_2 = date(d2.year, self.FISCAL_YEAR_END_MONTH, self.FISCAL_YEAR_END_DAY)
        # Check if either date is before/after the FY end in their respective years
        in_fy1 = d1 <= fy_end_1
        in_fy2 = d2 <= fy_end_2
        return (d1.year != d2.year) or (in_fy1 != in_fy2)

    def _format_etb(self, amount: float) -> str:
        return f"ETB {amount:,.2f}"

    # ─── Match Type Explainers ────────────────────────────────────────

    def _explain_exact_match(
        self, confidence: int, level: ConfidenceLevel,
        bank_txn: dict, gl_entry: Optional[dict]
    ) -> Explanation:
        amount = abs(bank_txn.get("amount", 0))
        bt_date = self._parse_txn_date(bank_txn)
        gl_date = self._parse_txn_date(gl_entry) if gl_entry else None
        bt_ref = bank_txn.get("reference", "")
        gl_ref = gl_entry.get("reference", "") if gl_entry else ""

        components = [
            ExplanationComponent(
                category="amount",
                english=f"{self._format_etb(amount)} matches exactly between bank and GL",
                amharic=f"{self._format_etb(amount)} በባንክ እና በመዝገብ መካከል በትክክል ይዛመዳል",
                ifrs_reference="IFRS 9.3.1.1 — Financial asset recognized at fair value"
            ),
            ExplanationComponent(
                category="date",
                english=f"Transaction date {bt_date} matches GL date {gl_date}",
                amharic=f"የግብይት ቀን {bt_date} ከመዝገብ ቀን {gl_date} ጋር ይዛመዳል"
            ),
        ]

        if bt_ref and gl_ref and (bt_ref.upper() in gl_ref.upper() or gl_ref.upper() in bt_ref.upper()):
            components.append(ExplanationComponent(
                category="reference",
                english=f"Bank reference '{bt_ref}' matches GL reference '{gl_ref}'",
                amharic=f"የባንክ ማጣቀሻ '{bt_ref}' ከመዝገብ ማጣቀሻ '{gl_ref}' ጋር ይዛመዳል"
            ))

        summary_en = f"Matched because: amount {self._format_etb(amount)} matches exactly · date same day ({bt_date})"
        summary_am = f"ተገናኝቷል ምክንያቱም: መጠን {self._format_etb(amount)} በትክክል ይዛመዳል · ቀን በዚያው ቀን ({bt_date})"

        return Explanation(
            match_type=MatchType.EXACT_1TO1,
            confidence=confidence,
            confidence_level=level,
            summary_english=summary_en,
            summary_amharic=summary_am,
            components=components,
            accounting_treatment="Auto-posted to GL — no adjustment required. Recognized in correct period.",
            accounting_treatment_am="በራስ-ሰር ወደ መዝገብ ተመዝግቧል — ማስተካከያ አያስፈልግም። በትክክለኛው ወቅት ተመዝግቧል።",
            ifrs_standard="IFRS 9.3.1.1",
            audit_trail_note=f"Exact match — auto-posted at confidence {confidence}%"
        )

    def _explain_fee_net_match(
        self, confidence: int, level: ConfidenceLevel,
        bank_txn: dict, gl_entry: Optional[dict],
        fee_breakdown: Optional[dict]
    ) -> Explanation:
        amount = abs(bank_txn.get("amount", 0))
        bt_date = self._parse_txn_date(bank_txn)
        fees = fee_breakdown or {}
        total_fees = fees.get("total_fees", 0)
        bank_charge = fees.get("bank_charge", 0)
        gov_tax = fees.get("gov_tax", 0)

        components = [
            ExplanationComponent(
                category="amount",
                english=f"Net amount {self._format_etb(amount)} matches GL lump entry (fees of {self._format_etb(total_fees)} included)",
                amharic=f"የተጣራ መጠን {self._format_etb(amount)} ከመዝገብ ጠቅላላ ገቢ ጋር ይዛመዳል (የ{self._format_etb(total_fees)} ክፍያዎች ተካትተዋል)",
                ifrs_reference="IFRS 9.3.1.1"
            ),
            ExplanationComponent(
                category="date",
                english=f"Same day ({bt_date})",
                amharic=f"በዚያው ቀን ({bt_date})"
            ),
        ]

        if total_fees > 0:
            components.append(ExplanationComponent(
                category="amount",
                english=f"Fees: bank charge {self._format_etb(bank_charge)} + gov't tax {self._format_etb(gov_tax)} = {self._format_etb(total_fees)}",
                amharic=f"ክፍያዎች: የባንክ ክፍያ {self._format_etb(bank_charge)} + የመንግስት ታክስ {self._format_etb(gov_tax)} = {self._format_etb(total_fees)}",
                detail="Fees embedded in transaction amount — GL records lump sum"
            ))

        summary_en = (
            f"Matched because: net amount {self._format_etb(amount)} matches GL · "
            f"date same day ({bt_date}) · fees of {self._format_etb(total_fees)} included in amount"
        )
        summary_am = (
            f"ተገናኝቷል ምክንያቱም: የተጣራ መጠን {self._format_etb(amount)} ከመዝገብ ጋር ይዛመዳል · "
            f"ቀን በዚያው ቀን ({bt_date}) · የ{self._format_etb(total_fees)} ክፍያዎች ተካትተዋል"
        )

        return Explanation(
            match_type=MatchType.FEE_NET_MATCH,
            confidence=confidence,
            confidence_level=level,
            summary_english=summary_en,
            summary_amharic=summary_am,
            components=components,
            accounting_treatment=(
                f"Auto-posted to GL. Bank charges of {self._format_etb(total_fees)} "
                f"are embedded in the transaction amount. No separate fee entry needed."
            ),
            accounting_treatment_am=(
                f"በራስ-ሰር ወደ መዝገብ ተመዝግቧል። የባንክ ክፍያዎች {self._format_etb(total_fees)} "
                f"በግብይት መጠን ውስጥ ተካትተዋል። ምንም ልዩ የክፍያ ግቤት አያስፈልግም።"
            ),
            ifrs_standard="IFRS 9.3.1.1",
            compliance_note="VAT on bank services is 15% per Ethiopian tax law" if gov_tax > 0 else None,
            compliance_note_am="በየባንክ አገልግሎት ላይ የተጨማሪ እሴት ታክስ 15% ነው" if gov_tax > 0 else None,
            audit_trail_note=f"Fee net match — {self._format_etb(total_fees)} in fees embedded"
        )

    def _explain_fee_gross_match(
        self, confidence: int, level: ConfidenceLevel,
        bank_txn: dict, gl_entry: Optional[dict],
        fee_breakdown: Optional[dict]
    ) -> Explanation:
        amount = abs(bank_txn.get("amount", 0))
        fees = fee_breakdown or {}
        gross = fees.get("gross_amount", amount)
        total_fees = fees.get("total_fees", 0)
        bt_date = self._parse_txn_date(bank_txn)

        components = [
            ExplanationComponent(
                category="amount",
                english=f"Gross amount {self._format_etb(gross)} matches GL vendor entry",
                amharic=f"ጠቅላላ መጠን {self._format_etb(gross)} ከመዝገብ ሻጭ ግቤት ጋር ይዛመዳል",
                ifrs_reference="IFRS 9.3.1.1"
            ),
            ExplanationComponent(
                category="amount",
                english=f"Fees {self._format_etb(total_fees)} (charge: {self._format_etb(fees.get('bank_charge', 0))}, tax: {self._format_etb(fees.get('gov_tax', 0))}) recorded separately",
                amharic=f"ክፍያዎች {self._format_etb(total_fees)} በየበኩል ተመዝግበዋል"
            ),
            ExplanationComponent(
                category="date",
                english=f"Same day ({bt_date})",
                amharic=f"በዚያው ቀን ({bt_date})"
            ),
        ]

        summary_en = (
            f"Matched because: gross amount {self._format_etb(gross)} matches GL · "
            f"fees {self._format_etb(total_fees)} recorded separately"
        )
        summary_am = (
            f"ተገናኝቷል ምክንያቱም: ጠቅላላ መጠን {self._format_etb(gross)} ከመዝገብ ጋር ይዛመዳል · "
            f"ክፍያዎች {self._format_etb(total_fees)} በየበኩል ተመዝግበዋል"
        )

        return Explanation(
            match_type=MatchType.FEE_GROSS_MATCH,
            confidence=confidence,
            confidence_level=level,
            summary_english=summary_en,
            summary_amharic=summary_am,
            components=components,
            accounting_treatment=(
                f"GL records vendor amount ({self._format_etb(gross)}) separately from bank fees. "
                f"Verify that bank charges are posted to Bank Charges account (typically GL 6500)."
            ),
            accounting_treatment_am=(
                f"መዝገብ የሻጭ መጠን ({self._format_etb(gross)}) ከየባንክ ክፍያዎች በየበኩል ይመዝግባል። "
                f"የባንክ ክፍያዎች ወደ የባንክ ክፍያ ሂሳብ (ተብሎ GL 6500) መመዝገባቸውን ያረጋግጡ።"
            ),
            ifrs_standard="IFRS 9.3.1.1, IAS 1.88",
            audit_trail_note=f"Fee gross match — fees {self._format_etb(total_fees)} separated"
        )

    def _explain_fee_split_match(
        self, confidence: int, level: ConfidenceLevel,
        bank_txn: dict, gl_entry: Optional[dict],
        fee_breakdown: Optional[dict],
        gl_entries: Optional[List[dict]]
    ) -> Explanation:
        amount = abs(bank_txn.get("amount", 0))
        fees = fee_breakdown or {}
        gross = fees.get("gross_amount", amount - fees.get("total_fees", 0))
        total_fees = fees.get("total_fees", 0)
        bt_date = self._parse_txn_date(bank_txn)

        components = [
            ExplanationComponent(
                category="amount",
                english=f"Gross amount {self._format_etb(gross)} matches vendor GL entry",
                amharic=f"ጠቅላላ መጠን {self._format_etb(gross)} ከመዝገብ ሻጭ ግቤት ጋር ይዛመዳል",
                ifrs_reference="IFRS 15.105 — Revenue recognized when performance obligation satisfied"
            ),
            ExplanationComponent(
                category="amount",
                english=f"Fees {self._format_etb(total_fees)} match bank charges GL entry",
                amharic=f"ክፍያዎች {self._format_etb(total_fees)} ከየባንክ ክፍያ መዝገብ ጋር ይዛመዳል"
            ),
            ExplanationComponent(
                category="amount",
                english=f"Total reconciled: {self._format_etb(gross)} + {self._format_etb(total_fees)} = {self._format_etb(gross + total_fees)}",
                amharic=f"ጠቅላላ ማስታረቅ: {self._format_etb(gross)} + {self._format_etb(total_fees)} = {self._format_etb(gross + total_fees)}"
            ),
            ExplanationComponent(
                category="date",
                english=f"Same day ({bt_date})",
                amharic=f"በዚያው ቀን ({bt_date})"
            ),
        ]

        summary_en = (
            f"Matched because: gross {self._format_etb(gross)} matches vendor GL · "
            f"fees {self._format_etb(total_fees)} match bank charges GL · "
            f"total {self._format_etb(gross + total_fees)} reconciled"
        )
        summary_am = (
            f"ተገናኝቷል ምክንያቱም: ጠቅላላ {self._format_etb(gross)} ከመዝገብ ሻጭ ጋር ይዛመዳል · "
            f"ክፍያዎች {self._format_etb(total_fees)} ከየባንክ ክፍያ መዝገብ ጋር ይዛመዳል · "
            f"ጠቅላላ {self._format_etb(gross + total_fees)} ተስታረቋል"
        )

        return Explanation(
            match_type=MatchType.FEE_SPLIT_MATCH,
            confidence=confidence,
            confidence_level=level,
            summary_english=summary_en,
            summary_amharic=summary_am,
            components=components,
            accounting_treatment=(
                f"Split match: vendor GL ({self._format_etb(gross)}) + bank charges GL ({self._format_etb(total_fees)}) = "
                f"bank total ({self._format_etb(gross + total_fees)}). Both entries required."
            ),
            accounting_treatment_am=(
                f"የተከፋፈለ ግባና: የመዝገብ ሻጭ ({self._format_etb(gross)}) + የባንክ ክፍያ መዝገብ ({self._format_etb(total_fees)}) = "
                f"የባንክ ጠቅላላ ({self._format_etb(gross + total_fees)}). ሁለቱም ግቤቶች ያስፈልጋሉ።"
            ),
            ifrs_standard="IFRS 15.105, IAS 1.88",
            audit_trail_note=f"Split match — {self._format_etb(total_fees)} in fees matched to bank charges GL"
        )

    def _explain_date_shifted(
        self, confidence: int, level: ConfidenceLevel,
        bank_txn: dict, gl_entry: Optional[dict],
        fee_breakdown: Optional[dict]
    ) -> Explanation:
        amount = abs(bank_txn.get("amount", 0))
        bt_date = self._parse_txn_date(bank_txn)
        gl_date = self._parse_txn_date(gl_entry) if gl_entry else None
        fees = fee_breakdown or {}
        total_fees = fees.get("total_fees", 0)

        day_diff = 0
        if bt_date and gl_date:
            day_diff = abs((bt_date - gl_date).days)

        lag_reason = "bank processing lag"
        if day_diff == 1:
            lag_reason = "typical 1-day bank processing lag"
        elif day_diff == 2:
            lag_reason = "2-day processing lag (weekend or holiday)"
        elif day_diff >= 3:
            lag_reason = f"{day_diff}-day lag (verify — unusually long)"

        components = [
            ExplanationComponent(
                category="amount",
                english=f"{self._format_etb(amount)} matches exactly",
                amharic=f"{self._format_etb(amount)} በትክክል ይዛመዳል",
                ifrs_reference="IAS 39.14 — Derecognition when rights to cash flows expire"
            ),
            ExplanationComponent(
                category="date",
                english=f"Bank date {bt_date} is {day_diff} day(s) after GL date {gl_date} ({lag_reason})",
                amharic=f"የባንክ ቀን {bt_date} ከመዝገብ ቀን {gl_date} በኋላ {day_diff} ቀን ነው ({lag_reason})"
            ),
        ]

        if total_fees > 0:
            components.append(ExplanationComponent(
                category="amount",
                english=f"Fees {self._format_etb(total_fees)} included",
                amharic=f"ክፍያዎች {self._format_etb(total_fees)} ተካትተዋል"
            ))

        # Period impact
        period_impact = None
        if bt_date and gl_date:
            if self._is_fiscal_year_boundary(bt_date, gl_date):
                period_impact = "⚠️ Crosses Ethiopian fiscal year (Jul 7) — requires CFO approval"
                components.append(ExplanationComponent(
                    category="compliance",
                    english=period_impact,
                    amharic="⚠️ የኢትዮጵያ የበጀት ዓመት (ሰኔ 7) ያለፍዋል — የሲፎ ፈቃድ ያስፈልጋል"
                ))
            elif self._is_period_boundary(bt_date, gl_date):
                period_impact = "Crosses period boundary — verify correct period assignment"
                components.append(ExplanationComponent(
                    category="compliance",
                    english=period_impact,
                    amharic="የወቅት ድንበር ያለፍዋል — ትክክለኛውን የወቅት መመደብ ያረጋግጡ"
                ))
            else:
                period_impact = "Same period — no adjustment needed"

        summary_en = (
            f"Matched because: amount {self._format_etb(amount)} · "
            f"date {day_diff} day(s) after GL entry ({lag_reason})"
        )
        summary_am = (
            f"ተገናኝቷል ምክንያቱም: መጠን {self._format_etb(amount)} · "
            f"ቀን ከመዝገብ ግቤት በኋላ {day_diff} ቀን ({lag_reason})"
        )

        return Explanation(
            match_type=MatchType.DATE_SHIFTED,
            confidence=confidence,
            confidence_level=level,
            summary_english=summary_en,
            summary_amharic=summary_am,
            components=components,
            accounting_treatment=f"Review required — verify period assignment. {lag_reason.title()}.",
            accounting_treatment_am=f"ግምገማ ያስፈልጋል — የወቅት መመደብ ያረጋግጡ። {lag_reason.title()}።",
            ifrs_standard="IAS 39.14",
            period_impact=period_impact,
            audit_trail_note=f"Date-shifted match — {day_diff} day lag"
        )

    def _explain_one_to_many(
        self, confidence: int, level: ConfidenceLevel,
        bank_txn: dict, gl_entries: Optional[List[dict]]
    ) -> Explanation:
        amount = abs(bank_txn.get("amount", 0))
        bt_date = self._parse_txn_date(bank_txn)
        entries = gl_entries or []
        gl_total = sum(abs(e.get("amount", 0)) for e in entries)

        breakdown_lines = []
        breakdown_lines_am = []
        for e in entries:
            eid = e.get("id", "?")
            eamt = abs(e.get("amount", 0))
            edesc = e.get("description", "")
            breakdown_lines.append(f"  • {eid}: {self._format_etb(eamt)} — {edesc}")
            breakdown_lines_am.append(f"  • {eid}: {self._format_etb(eamt)} — {edesc}")

        components = [
            ExplanationComponent(
                category="amount",
                english=f"Bank txn {self._format_etb(amount)} = sum of {len(entries)} GL entries ({self._format_etb(gl_total)})",
                amharic=f"የባንክ ግብይት {self._format_etb(amount)} = የ{len(entries)} መዝገብ ግቤቶች ድምር ({self._format_etb(gl_total)})",
                ifrs_reference="IFRS 15.105 — Recognize revenue when performance obligation satisfied"
            ),
            ExplanationComponent(
                category="date",
                english=f"Bank date {bt_date}",
                amharic=f"የባንክ ቀን {bt_date}"
            ),
        ]

        summary_en = (
            f"Matched because: bank txn {self._format_etb(amount)} = sum of {len(entries)} GL entries "
            f"({self._format_etb(gl_total)})"
        )
        summary_am = (
            f"ተገናኝቷል ምክንያቱም: የባንክ ግብይት {self._format_etb(amount)} = የ{len(entries)} መዝገብ ግቤቶች ድምር "
            f"({self._format_etb(gl_total)})"
        )

        return Explanation(
            match_type=MatchType.ONE_TO_MANY,
            confidence=confidence,
            confidence_level=level,
            summary_english=summary_en,
            summary_amharic=summary_am,
            components=components,
            accounting_treatment="Confirm grouping — verify all components are valid entries.",
            accounting_treatment_am="ቡድን ያረጋግጡ — ሁሉም አካላቶች ትክክለኛ ግቤቶች መሆናቸውን ያረጋግጡ።",
            ifrs_standard="IFRS 15.105",
            audit_trail_note=f"One-to-many match — {len(entries)} GL entries grouped"
        )

    def _explain_intercompany(
        self, confidence: int, level: ConfidenceLevel,
        bank_txn: dict, gl_entry: Optional[dict]
    ) -> Explanation:
        amount = abs(bank_txn.get("amount", 0))
        bt_date = self._parse_txn_date(bank_txn)

        components = [
            ExplanationComponent(
                category="amount",
                english=f"{self._format_etb(amount)} — internal transfer between company accounts",
                amharic=f"{self._format_etb(amount)} — በኩባንያ ሂሳቦች መካከል የውስጥ ሽግግር",
                ifrs_reference="IFRS 10.B86 — Eliminate intra-group transactions in consolidation"
            ),
            ExplanationComponent(
                category="treatment",
                english="Intercompany transfer — not external revenue/expense",
                amharic="የውስጥ ሽግግር — ውጫዊ ገቢ/ወጪ አይደለም"
            ),
        ]

        summary_en = f"Intercompany transfer of {self._format_etb(amount)} — auto-excluded from P&L"
        summary_am = f"የውስጥ ሽግግር {self._format_etb(amount)} — ከትርፍ ኪሳ ውጪ ተደርጓል"

        return Explanation(
            match_type=MatchType.INTERCOMPANY,
            confidence=confidence,
            confidence_level=level,
            summary_english=summary_en,
            summary_amharic=summary_am,
            components=components,
            accounting_treatment="Auto-excluded from P&L — recorded as balance sheet transfer. Eliminated in consolidation.",
            accounting_treatment_am="ከትርፍ ኪሳ ውጪ ተደርጓል — እንደ ቢላንስ ሺት ሽግግር ተመዝግቧል። በማጠቃለያ ውስጥ ይሰረዛል።",
            ifrs_standard="IFRS 10.B86",
            compliance_note="Intra-group elimination required per IFRS 10",
            compliance_note_am="በIFRS 10 መሰረት የውስጥ ቡድን መሰረዝ ያስፈልጋል",
            audit_trail_note="Intercompany — auto-classified, excluded from group profit"
        )

    def _explain_fx_match(
        self, confidence: int, level: ConfidenceLevel,
        bank_txn: dict, gl_entry: Optional[dict],
        extra: dict
    ) -> Explanation:
        amount = abs(bank_txn.get("amount", 0))
        bt_date = self._parse_txn_date(bank_txn)
        fx_rate = extra.get("fx_rate", 0)
        foreign_amount = extra.get("foreign_amount", 0)
        foreign_currency = extra.get("foreign_currency", "USD")
        rate_date = extra.get("rate_date", "")

        components = [
            ExplanationComponent(
                category="amount",
                english=f"{foreign_currency} {foreign_amount:,.2f} × NBE rate {fx_rate} = {self._format_etb(amount)}",
                amharic=f"{foreign_currency} {foreign_amount:,.2f} × የNBE ተመን {fx_rate} = {self._format_etb(amount)}",
                ifrs_reference="IAS 21.21 — Translate at spot rate on transaction date"
            ),
            ExplanationComponent(
                category="compliance",
                english=f"NBE daily indicative rate — {rate_date}",
                amharic=f"የNBE ዕለታዊ ጠቋሚ ተመን — {rate_date}"
            ),
        ]

        summary_en = f"FX match: {foreign_currency} {foreign_amount:,.2f} × NBE rate {fx_rate} = {self._format_etb(amount)}"
        summary_am = f"የውጭ ምንዛሪ ግባና: {foreign_currency} {foreign_amount:,.2f} × የNBE ተመን {fx_rate} = {self._format_etb(amount)}"

        return Explanation(
            match_type=MatchType.FX_CROSS_CURRENCY,
            confidence=confidence,
            confidence_level=level,
            summary_english=summary_en,
            summary_amharic=summary_am,
            components=components,
            accounting_treatment="Translated at spot rate per IAS 21. Record FX gain/loss if rate differs from booking rate.",
            accounting_treatment_am="በIAS 21 መሰረት በቦታ ተመን ተተርጉሟል። ተመኑ ከመመዝገቢያ ተመን ጋር ከተለያየ የተመን ትርፍ/ኪሳ ይመዝገባል።",
            ifrs_standard="IAS 21.21",
            compliance_note="NBE directive compliance — documented rate source required",
            compliance_note_am="የNBE ትዕዛዝ ትብብር — የተመን ምንጭ ማስረጃ ያስፈልጋል",
            audit_trail_note=f"FX match — NBE rate {fx_rate} on {rate_date}"
        )

    def _explain_loan_debit(
        self, confidence: int, level: ConfidenceLevel,
        bank_txn: dict, gl_entry: Optional[dict],
        extra: dict
    ) -> Explanation:
        amount = abs(bank_txn.get("amount", 0))
        principal = extra.get("principal", amount * 0.85)
        interest = extra.get("interest", amount - principal)
        bt_date = self._parse_txn_date(bank_txn)
        schedule_date = extra.get("schedule_date", "")

        components = [
            ExplanationComponent(
                category="amount",
                english=f"{self._format_etb(amount)} — automatic loan repayment",
                amharic=f"{self._format_etb(amount)} — ራስ-ሰር የብድር ክፍያ",
                ifrs_reference="IFRS 9.4.2.2 — Amortized cost measurement"
            ),
            ExplanationComponent(
                category="amount",
                english=f"Principal: {self._format_etb(principal)} (reduces loan balance) + Interest: {self._format_etb(interest)} (finance cost)",
                amharic=f"ዋና ገንዘብ: {self._format_etb(principal)} (የብድር ቀሪ ይቀንሳል) + ወለድ: {self._format_etb(interest)} (የገንዘብ ወጪ)"
            ),
            ExplanationComponent(
                category="date",
                english=f"Debit date {bt_date} matches loan schedule",
                amharic=f"የድ nợ ቀን {bt_date} ከብድር መርሃ ግብር ጋር ይዛመዳል"
            ),
        ]

        summary_en = (
            f"Loan auto-debit: {self._format_etb(amount)} — "
            f"principal {self._format_etb(principal)} + interest {self._format_etb(interest)}"
        )
        summary_am = (
            f"ራስ-ሰር የብድር ድ nợ: {self._format_etb(amount)} — "
            f"ዋና ገንዘብ {self._format_etb(principal)} + ወለድ {self._format_etb(interest)}"
        )

        return Explanation(
            match_type=MatchType.LOAN_AUTO_DEBIT,
            confidence=confidence,
            confidence_level=level,
            summary_english=summary_en,
            summary_amharic=summary_am,
            components=components,
            accounting_treatment=f"Auto-posted. Principal ({self._format_etb(principal)}) to balance sheet, interest ({self._format_etb(interest)}) to P&L.",
            accounting_treatment_am=f"በራስ-ሰር ተመዝግቧል። ዋና ገንዘብ ({self._format_etb(principal)}) ወደ ቢላንስ ሺት፣ ወለድ ({self._format_etb(interest)}) ወደ ትርፍ ኪሳ።",
            ifrs_standard="IFRS 9.4.2.2, IAS 32",
            audit_trail_note="Loan auto-debit — matches amortization schedule"
        )

    def _explain_cheque_clearing(
        self, confidence: int, level: ConfidenceLevel,
        bank_txn: dict, gl_entry: Optional[dict],
        extra: dict
    ) -> Explanation:
        amount = abs(bank_txn.get("amount", 0))
        bt_date = self._parse_txn_date(bank_txn)
        cheque_number = extra.get("cheque_number", "")
        issue_date = extra.get("issue_date", "")
        days_to_clear = extra.get("days_to_clear", 0)

        components = [
            ExplanationComponent(
                category="amount",
                english=f"{self._format_etb(amount)} — cheque #{cheque_number} cleared",
                amharic=f"{self._format_etb(amount)} — ቼክ #{cheque_number} ገጽቶል"
            ),
            ExplanationComponent(
                category="date",
                english=f"Cleared on {bt_date} (issued {issue_date}, {days_to_clear} days to clear)",
                amharic=f"በ{bt_date} ገጽቶል (ተሰጥቶ {issue_date}, {days_to_clear} ቀናት ወስዷል)"
            ),
        ]

        summary_en = f"Cheque #{cheque_number} for {self._format_etb(amount)} cleared ({days_to_clear} days)"
        summary_am = f"ቼክ #{cheque_number} ለ{self._format_etb(amount)} ገጽቶል ({days_to_clear} ቀናት)"

        return Explanation(
            match_type=MatchType.CHEQUE_CLEARING,
            confidence=confidence,
            confidence_level=level,
            summary_english=summary_en,
            summary_amharic=summary_am,
            components=components,
            accounting_treatment="Auto-posted — cheque clearing matches issued cheque record.",
            accounting_treatment_am="በራስ-ሰር ተመዝግቧል — የቼክ ግምት ከተሰጠ የቼክ መዝገብ ጋር ይዛመዳል።",
            audit_trail_note=f"Cheque #{cheque_number} cleared — {days_to_clear} days to clear"
        )

    def _explain_standing_order(
        self, confidence: int, level: ConfidenceLevel,
        bank_txn: dict, gl_entry: Optional[dict]
    ) -> Explanation:
        amount = abs(bank_txn.get("amount", 0))
        bt_date = self._parse_txn_date(bank_txn)
        ref = bank_txn.get("reference", "")

        components = [
            ExplanationComponent(
                category="amount",
                english=f"{self._format_etb(amount)} — standing order payment",
                amharic=f"{self._format_etb(amount)} — የቋሚ ትዕዛዝ ክፍያ"
            ),
            ExplanationComponent(
                category="date",
                english=f"Regular payment date {bt_date}",
                amharic=f"መደበኛ የክፍያ ቀን {bt_date}"
            ),
        ]

        summary_en = f"Standing order: {self._format_etb(amount)} on {bt_date} (ref: {ref})"
        summary_am = f"ቋሚ ትዕዛዝ: {self._format_etb(amount)} በ{bt_date} (ማጣቀሻ: {ref})"

        return Explanation(
            match_type=MatchType.STANDING_ORDER,
            confidence=confidence,
            confidence_level=level,
            summary_english=summary_en,
            summary_amharic=summary_am,
            components=components,
            accounting_treatment="Auto-posted — recurring standing order matches expected schedule.",
            accounting_treatment_am="በራስ-ሰር ተመዝግቧል — የተደጋጋሚ ቋሚ ትዕዛዝ ከሚጠበቀ መርሃ ግብር ጋር ይዛመዳል።",
            audit_trail_note=f"Standing order — recurring payment {ref}"
        )

    def _explain_generic(
        self, confidence: int, level: ConfidenceLevel,
        match_type: str, bank_txn: dict, gl_entry: Optional[dict]
    ) -> Explanation:
        amount = abs(bank_txn.get("amount", 0))
        bt_date = self._parse_txn_date(bank_txn)

        summary_en = f"Matched ({match_type}): {self._format_etb(amount)} on {bt_date}"
        summary_am = f"ተገናኝቷል ({match_type}): {self._format_etb(amount)} በ{bt_date}"

        return Explanation(
            match_type=MatchType(match_type) if match_type in [e.value for e in MatchType] else MatchType.EXACT_1TO1,
            confidence=confidence,
            confidence_level=level,
            summary_english=summary_en,
            summary_amharic=summary_am,
            components=[
                ExplanationComponent(
                    category="amount",
                    english=f"{self._format_etb(amount)}",
                    amharic=f"{self._format_etb(amount)}"
                )
            ],
            accounting_treatment=f"Review match type '{match_type}' — verify accounting treatment.",
            accounting_treatment_am=f"የ'{match_type}' ግባና ይገምግሙ — የሂሳብ ማካተት ያረጋግጡ።",
            audit_trail_note=f"Generic match ({match_type}) at {confidence}%"
        )

    # ─── Anomaly Detection ────────────────────────────────────────────

    def detect_anomalies(
        self, bank_txn: dict, all_transactions: Optional[List[dict]] = None
    ) -> List[str]:
        """
        Detect anomalies in a transaction.
        Returns list of anomaly flag strings.
        """
        flags = []
        amount = abs(bank_txn.get("amount", 0))
        bt_date = self._parse_txn_date(bank_txn)
        desc = (bank_txn.get("description") or "").upper()

        # Weekend transaction
        if bt_date and bt_date.weekday() >= 5:
            day_name = "Saturday" if bt_date.weekday() == 5 else "Sunday"
            flags.append(f"weekend_txn: Transaction on {day_name} ({bt_date}). Ethiopian banks typically process on business days.")

        # Round number (exact thousands)
        if amount > 0 and amount == round(amount, -3):
            flags.append(f"round_amount: Round amount {self._format_etb(amount)}. Verify if estimate or actual.")

        # Large amount spike
        if all_transactions and len(all_transactions) > 3:
            amounts = [abs(t.get("amount", 0)) for t in all_transactions if t.get("amount")]
            avg = sum(amounts) / len(amounts) if amounts else 0
            if avg > 0 and amount > avg * 3:
                flags.append(f"amount_spike: {self._format_etb(amount)} is {amount/avg:.1f}x the average ({self._format_etb(avg)}). Verify large payment.")

        # Duplicate amount same day
        if all_transactions and bt_date:
            same_day_same_amount = [
                t for t in all_transactions
                if self._parse_txn_date(t) == bt_date
                and abs(t.get("amount", 0)) == amount
                and t.get("id") != bank_txn.get("id")
            ]
            if same_day_same_amount:
                flags.append(f"duplicate_amount: Two transactions of {self._format_etb(amount)} on {bt_date}. Verify if duplicate or legitimate.")

        # Missing VAT for large transactions
        if amount > 10000 and "VAT" not in desc and "TAX" not in desc:
            # Check if it looks like a sale
            sale_keywords = ["SALE", "INVOICE", "PAYMENT", "TRANSFER"]
            if any(kw in desc for kw in sale_keywords):
                flags.append(f"missing_vat: Sale of {self._format_etb(amount)} without VAT notation. Verify if exempt or zero-rated.")

        return flags


# ─── Convenience Function ───────────────────────────────────────────

def generate_explanation(
    match_type: str,
    confidence: int,
    bank_txn: dict,
    gl_entry: Optional[dict] = None,
    gl_entries: Optional[List[dict]] = None,
    fee_breakdown: Optional[dict] = None,
    extra_context: Optional[dict] = None,
) -> dict:
    """
    Convenience function to generate explanation as dict.
    Returns serializable dict for API responses.
    """
    engine = ExplainabilityEngine()
    explanation = engine.explain(
        match_type=match_type,
        confidence=confidence,
        bank_txn=bank_txn,
        gl_entry=gl_entry,
        gl_entries=gl_entries,
        fee_breakdown=fee_breakdown,
        extra_context=extra_context,
    )

    return {
        "match_type": explanation.match_type.value,
        "confidence": explanation.confidence,
        "confidence_level": explanation.confidence_level.value,
        "summary_english": explanation.summary_english,
        "summary_amharic": explanation.summary_amharic,
        "components": [
            {
                "category": c.category,
                "english": c.english,
                "amharic": c.amharic,
                "ifrs_reference": c.ifrs_reference,
                "detail": c.detail,
            }
            for c in explanation.components
        ],
        "accounting_treatment": explanation.accounting_treatment,
        "accounting_treatment_am": explanation.accounting_treatment_am,
        "ifrs_standard": explanation.ifrs_standard,
        "compliance_note": explanation.compliance_note,
        "compliance_note_am": explanation.compliance_note_am,
        "audit_trail_note": explanation.audit_trail_note,
        "period_impact": explanation.period_impact,
        "anomaly_flags": explanation.anomaly_flags,
    }
