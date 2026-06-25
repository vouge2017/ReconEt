"""
Reconciliation API — Fee-Aware Matching with PDF + CSV Support

POST /api/reconciliation/run — Run matching with fee extraction (PDF or CSV)
GET  /api/reconciliation/summary — Get fee summary report
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime
import uuid
import csv
import io
import re

from app.database import get_db
from app.models import BankTransaction, GLEntry, Match, BankAccount
from app.engine.matching import MatchingEngine, Transaction, MatchResult
from app.engine.fee_extractor import FeeExtractor
from app.engine.explainer import generate_explanation, ExplainabilityEngine
from app.engine.balance_verifier import BalanceVerifier, VerificationStatus

router = APIRouter(prefix="/api/reconciliation", tags=["reconciliation"])


def detect_file_type(filename: str, content: bytes) -> str:
    """Detect if uploaded file is PDF or CSV"""
    filename_lower = filename.lower()
    
    if filename_lower.endswith('.pdf'):
        return 'pdf'
    elif filename_lower.endswith('.csv'):
        return 'csv'
    
    # Check magic bytes
    if content[:4] == b'%PDF':
        return 'pdf'
    
    # Default to CSV
    return 'csv'


def extract_fees_from_description(description: str, amount: float) -> dict:
    """Extract fees from transaction description"""
    extractor = FeeExtractor()
    result = extractor.extract_from_text(description, amount)
    return {
        "fee_amount": result.total_fees,
        "bank_charge": result.bank_charge,
        "gov_tax": result.gov_tax,
        "gross_amount": result.gross_amount,
        "net_amount": result.net_amount,
        "extraction_method": result.extraction_method,
        "confidence": result.confidence
    }


def parse_cbe_csv(content: str) -> List[dict]:
    """Parse CBE CSV with Amharic columns"""
    reader = csv.DictReader(io.StringIO(content))
    transactions = []
    
    for i, row in enumerate(reader):
        # Map Amharic columns
        date_str = row.get("ቀን", row.get("Date", "")).strip()
        debit_str = row.get("ክፍያ", row.get("Debit", "")).strip().replace(",", "")
        credit_str = row.get("ገቢ", row.get("Credit", "")).strip().replace(",", "")
        ref = row.get("ማጣቀሻ", row.get("Reference", "")).strip()
        desc = row.get("መግለጫ", row.get("Description", row.get("Narration", ""))).strip()
        balance_str = row.get("ቀሪ ሂሳብ", row.get("Balance", "")).strip().replace(",", "")
        
        # Parse amount
        try:
            debit = float(debit_str) if debit_str else 0.0
        except ValueError:
            debit = 0.0
        try:
            credit = float(credit_str) if credit_str else 0.0
        except ValueError:
            credit = 0.0
        
        amount = debit if debit > 0 else -credit
        
        # Extract fees from description
        fee_info = extract_fees_from_description(desc, abs(amount))
        
        transactions.append({
            "row": i + 1,
            "date": date_str,
            "reference": ref,
            "description": desc,
            "amount": amount,
            "balance": balance_str,
            **fee_info
        })
    
    return transactions


def parse_cbe_pdf(content: bytes, filename: str) -> dict:
    """
    Parse CBE PDF statement.
    
    Returns dict with:
        - transactions: List of parsed transactions
        - verification: Balance verification result
        - account_info: Account metadata
        - errors: Any parsing errors
    """
    from app.adapters.cbe_pdf import CBEPDFAdapter
    
    adapter = CBEPDFAdapter()
    result = adapter.parse(io.BytesIO(content), filename)
    
    # Convert to dict format compatible with the matching engine
    transactions = []
    for txn in result.transactions:
        # Determine amount (debit is negative, credit is positive)
        amount = -txn.debit if txn.debit > 0 else txn.credit
        
        transactions.append({
            "row": txn.row_index,
            "date": str(txn.date),
            "reference": txn.reference,
            "description": txn.narrative or txn.particulars,
            "amount": amount,
            "balance": str(txn.balance) if txn.balance else "",
            "fee_amount": txn.fee_amount,
            "bank_charge": txn.bank_charge,
            "gov_tax": txn.gov_tax,
            "gross_amount": txn.gross_amount,
            "net_amount": txn.net_amount,
            "reference_code": txn.reference_code,
            "transaction_type": txn.transaction_type,
            "cheque_number": txn.cheque_number,
            "value_date": str(txn.value_date) if txn.value_date else None,
        })
    
    return {
        "transactions": transactions,
        "verification": {
            "status": result.verification.status.value,
            "message": result.verification.message,
            "opening_balance": result.verification.opening_balance,
            "closing_balance": result.verification.closing_balance,
            "calculated_closing": result.verification.calculated_closing,
            "total_credits": result.verification.total_credits,
            "total_debits": result.verification.total_debits,
            "difference": result.verification.difference,
        },
        "account_info": {
            "account_type": result.account_type.value,
            "account_number": result.account_number,
            "account_name": result.account_name,
            "statement_period": result.statement_period,
        },
        "extraction_details": result.extraction_details,
        "errors": result.errors,
        "warnings": result.warnings,
    }


def parse_gl_csv(content: str) -> List[Transaction]:
    """Parse GL CSV export (from Peachtree or generic format)"""
    reader = csv.DictReader(io.StringIO(content))
    entries = []

    # Try common column name variations
    col_maps = [
        {"date": ["Date", "Entry Date", "Transaction Date", "ቀን"],
         "debit": ["Debit", "Debit Amount", "Debit ETB", "ድ nợ"],
         "credit": ["Credit", "Credit Amount", "Credit ETB", "እዳ"],
         "reference": ["Reference", "Ref", "Memo", "ማጣቀሻ"],
         "description": ["Description", "Narration", "Details", "መግለጫ"],
         "account_code": ["Account", "Account Code", "GL Account", "Acct #"],
         "account_name": ["Account Name", "Account Description"],
         "journal": ["Journal", "Journal #", "JE Number", "Batch"]}
    ]

    for i, row in enumerate(reader):
        normalized = {k.strip().upper(): v.strip() for k, v in row.items()}

        def find_val(keys):
            for k in keys:
                for nk, nv in normalized.items():
                    if k.upper() in nk:
                        return nv
            return ""

        col_map = col_maps[0]
        date_str = find_val(col_map["date"])
        debit_str = find_val(col_map["debit"]).replace(",", "").replace('"', '')
        credit_str = find_val(col_map["credit"]).replace(",", "").replace('"', '')
        ref = find_val(col_map["reference"])
        desc = find_val(col_map["description"])

        try:
            debit = float(debit_str) if debit_str else 0.0
        except ValueError:
            debit = 0.0
        try:
            credit = float(credit_str) if credit_str else 0.0
        except ValueError:
            credit = 0.0

        if debit == 0 and credit == 0:
            continue

        txn_date = _parse_date(date_str)
        if txn_date is None:
            continue

        entries.append(Transaction(
            id=f"gl-{i+1}",
            date=txn_date,
            amount=debit if debit > 0 else -credit,
            reference=ref,
            description=desc,
        ))

    return entries


def _parse_date(date_str: str) -> Optional[date]:
    """Try multiple date formats"""
    if not date_str:
        return None
    formats = [
        "%d/%m/%Y",   # CBE format: 15/06/2026
        "%Y-%m-%d",   # ISO: 2026-06-15
        "%m/%d/%Y",   # US: 06/15/2026
        "%d-%m-%Y",   # EU: 15-06-2026
        "%d.%m.%Y",   # Dotted: 15.06.2026
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


@router.post("/run")
async def run_reconciliation(
    bank_file: UploadFile = File(...),
    gl_csv: Optional[UploadFile] = None,
    company_id: str = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
    db: Session = Depends(get_db)
):
    """
    Run reconciliation with fee extraction.
    
    Accepts bank statement as PDF or CSV (auto-detected).
    Accepts GL CSV (optional). If not provided, uses mock entries.
    
    Returns matches with fee breakdown, explanations, and balance verification.
    """
    # File size limit: 50MB
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    # Read file content
    content = await bank_file.read()
    
    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is 50MB."
        )
    
    filename = bank_file.filename or "statement"
    
    # Detect file type
    file_type = detect_file_type(filename, content)
    
    pdf_info = None
    balance_verification = None
    
    if file_type == 'pdf':
        # Parse PDF
        pdf_result = parse_cbe_pdf(content, filename)
        
        # Check balance verification FIRST — this is a hard gate
        if pdf_result["verification"]["status"] == "failed":
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "balance_verification_failed",
                    "message": pdf_result["verification"]["message"],
                    "verification": pdf_result["verification"],
                    "extraction_errors": pdf_result["errors"],
                }
            )
        
        parsed_txns = pdf_result["transactions"]
        pdf_info = {
            "account_info": pdf_result["account_info"],
            "extraction_details": pdf_result["extraction_details"],
            "warnings": pdf_result["warnings"],
        }
        balance_verification = pdf_result["verification"]
        
    else:
        # Parse CSV (existing logic)
        content_str = content.decode("utf-8-sig")
        
        if "ቀን" in content_str or "ክፍያ" in content_str:
            parsed_txns = parse_cbe_csv(content_str)
        else:
            parsed_txns = parse_cbe_csv(content_str)
    
    if not parsed_txns:
        raise HTTPException(
            status_code=422,
            detail={"error": "no_transactions", "message": "No transactions found in file."}
        )
    
    # Convert to engine Transaction objects
    bank_transactions = []
    for txn in parsed_txns:
        # Parse date
        if "/" in str(txn["date"]):
            date_parts = str(txn["date"]).split("/")
            txn_date = date(int(date_parts[2]), int(date_parts[1]), int(date_parts[0]))
        elif "-" in str(txn["date"]):
            txn_date = datetime.strptime(str(txn["date"]), "%Y-%m-%d").date()
        else:
            txn_date = _parse_date(str(txn["date"]))
        
        if txn_date is None:
            continue
        
        bank_transactions.append(Transaction(
            id=f"bank-{txn['row']}",
            date=txn_date,
            amount=txn["amount"],
            reference=txn.get("reference", ""),
            description=txn.get("description", ""),
            fee_amount=txn.get("fee_amount", 0),
            bank_charge=txn.get("bank_charge", 0),
            gov_tax=txn.get("gov_tax", 0),
            gross_amount=txn.get("gross_amount", 0),
            net_amount=txn.get("net_amount", 0),
        ))
    
    # Parse GL CSV or use mock
    if gl_csv:
        gl_content = await gl_csv.read()
        gl_str = gl_content.decode("utf-8-sig")
        gl_entries = parse_gl_csv(gl_str)
    else:
        # Mock GL entries for demo
        gl_entries = [
            Transaction(id="gl-1", date=date(2026, 6, 15), amount=100040.00,
                        reference="INV-2026-0089", description="Payment to ABC Trading"),
            Transaction(id="gl-2", date=date(2026, 6, 16), amount=50011.50,
                        reference="SALARY-JUN", description="Salary payment"),
            Transaction(id="gl-3", date=date(2026, 6, 17), amount=75028.75,
                        reference="TRANSFER-FEE-001", description="Transfer to Dashen"),
            Transaction(id="gl-4", date=date(2026, 6, 18), amount=15017.25,
                        reference="SO-001", description="Standing order rent"),
            Transaction(id="gl-5", date=date(2026, 6, 20), amount=100115.00,
                        reference="CERT-001", description="Balance certificate"),
        ]
    
    # Run matching engine
    engine = MatchingEngine()
    matches = engine.run(bank_transactions, gl_entries)
    
    # Build explainability engine
    explainer = ExplainabilityEngine()
    all_bank_dicts = [
        {"id": t.id, "date": str(t.date), "amount": t.amount, "reference": t.reference, "description": t.description}
        for t in bank_transactions
    ]
    
    # Format response
    results = []
    for match in matches:
        bt_id = match.bank_transaction_ids[0]
        bt = next((t for t in bank_transactions if t.id == bt_id), None)
        gl_id = match.gl_entry_ids[0] if match.gl_entry_ids else None
        gl = next((t for t in gl_entries if t.id == gl_id), None) if gl_id else None
        
        bt_dict = {"id": bt.id, "date": str(bt.date), "amount": bt.amount, "reference": bt.reference, "description": bt.description} if bt else {}
        gl_dict = {"id": gl.id, "date": str(gl.date), "amount": gl.amount, "reference": gl.reference, "description": gl.description} if gl else None
        
        rich_explanation = generate_explanation(
            match_type=match.match_type,
            confidence=match.confidence,
            bank_txn=bt_dict,
            gl_entry=gl_dict,
            gl_entries=None,
            fee_breakdown=match.fee_breakdown,
        )
        
        anomalies = explainer.detect_anomalies(bt_dict, all_bank_dicts)
        rich_explanation["anomaly_flags"] = anomalies
        
        result = {
            "match_id": str(uuid.uuid4()),
            "match_type": match.match_type,
            "confidence": match.confidence,
            "explanation": match.explanation,
            "rich_explanation": rich_explanation,
            "status": match.status,
            "amount_strategy": match.amount_strategy,
            "bank_transaction": {
                "id": bt.id if bt else None,
                "date": str(bt.date) if bt else None,
                "amount": bt.amount if bt else None,
                "reference": bt.reference if bt else None,
                "description": bt.description[:50] if bt else None,
            },
            "gl_entry_ids": match.gl_entry_ids,
            "fee_breakdown": match.fee_breakdown,
            "anomaly_flags": anomalies,
        }
        results.append(result)
    
    # Calculate summary
    total_bank = len(bank_transactions)
    total_matched = len(matches)
    total_fees = sum(t.fee_amount for t in bank_transactions)
    total_bank_charges = sum(t.bank_charge for t in bank_transactions)
    total_gov_tax = sum(t.gov_tax for t in bank_transactions)
    
    response = {
        "summary": {
            "total_bank_transactions": total_bank,
            "total_matched": total_matched,
            "total_unmatched": total_bank - total_matched,
            "match_rate": f"{(total_matched/total_bank*100):.1f}%" if total_bank > 0 else "0%",
            "fee_summary": {
                "total_fees_extracted": total_fees,
                "total_bank_charges": total_bank_charges,
                "total_gov_tax": total_gov_tax,
                "transactions_with_fees": sum(1 for t in bank_transactions if t.fee_amount > 0)
            }
        },
        "matches": results,
        "source": {
            "file_type": file_type,
            "filename": filename,
        }
    }
    
    # Add PDF-specific info
    if pdf_info:
        response["pdf_info"] = pdf_info
    if balance_verification:
        response["balance_verification"] = balance_verification
    
    return response


@router.get("/summary/{company_id}")
async def get_fee_summary(company_id: str, db: Session = Depends(get_db)):
    """Get fee summary report for a company"""
    
    txns = db.query(BankTransaction).join(BankAccount).filter(
        BankAccount.company_id == company_id
    ).all()
    
    total_fees = sum(t.fee_amount or 0 for t in txns)
    total_charges = sum(t.bank_charge or 0 for t in txns)
    total_tax = sum(t.gov_tax or 0 for t in txns)
    
    by_type = {}
    for t in txns:
        fee_type = t.fee_type or "none"
        if fee_type not in by_type:
            by_type[fee_type] = {"count": 0, "total": 0}
        by_type[fee_type]["count"] += 1
        by_type[fee_type]["total"] += t.fee_amount or 0
    
    return {
        "company_id": company_id,
        "total_transactions": len(txns),
        "fee_summary": {
            "total_fees": total_fees,
            "bank_charges": total_charges,
            "gov_tax": total_tax,
            "fee_percentage": (total_fees / sum(abs(t.amount) for t in txns) * 100) if txns else 0
        },
        "by_fee_type": by_type
    }


@router.get("/export/{run_id}")
async def export_reconciliation_excel(
    run_id: str,
    company_name: str = "",
    account_number: str = "",
    period: str = "",
    db: Session = Depends(get_db)
):
    """
    Export reconciliation results to Excel.
    
    Returns .xlsx file with:
    - Summary statistics
    - All bank transactions (with fee breakdown)
    - Matched transactions
    - Unmatched transactions
    - Exception categories
    """
    from fastapi.responses import StreamingResponse
    from app.engine.excel_exporter import ExcelExporter, ExportConfig
    
    # Get transactions for this run
    txns = db.query(BankTransaction).filter(
        BankTransaction.upload_batch_id == run_id
    ).all()
    
    if not txns:
        raise HTTPException(status_code=404, detail="No transactions found for this run")
    
    # Get matches
    matches = db.query(Match).filter(
        Match.company_id == run_id  # simplified
    ).all()
    
    # Convert to export format
    from dataclasses import dataclass
    from typing import Optional
    
    @dataclass
    class ExportTransaction:
        row_index: int = 0
        date: str = ""
        value_date: str = ""
        particulars: str = ""
        reference: str = ""
        narrative: str = ""
        debit: float = 0.0
        credit: float = 0.0
        balance: float = 0.0
        fee_amount: float = 0.0
        bank_charge: float = 0.0
        gov_tax: float = 0.0
        reference_code: str = ""
        transaction_type: str = ""
        cheque_number: str = ""
        is_matched: bool = False
        gross_amount: float = 0.0
        net_amount: float = 0.0
    
    export_txns = []
    for i, t in enumerate(txns, 1):
        export_txns.append(ExportTransaction(
            row_index=i,
            date=str(t.transaction_date or ""),
            value_date=str(t.value_date or ""),
            particulars=t.description or "",
            reference=t.reference or "",
            narrative=t.description or "",
            debit=float(t.amount or 0) if (t.amount or 0) < 0 else 0,
            credit=float(t.amount or 0) if (t.amount or 0) > 0 else 0,
            balance=float(t.balance_after or 0),
            fee_amount=float(t.fee_amount or 0),
            bank_charge=float(t.bank_charge or 0),
            gov_tax=float(t.gov_tax or 0),
            reference_code="",
            transaction_type="",
            cheque_number="",
            is_matched=bool(t.is_matched),
            gross_amount=float(t.gross_amount or 0),
            net_amount=float(t.net_amount or 0),
        ))
    
    config = ExportConfig(
        company_name=company_name or "Ethiopian Company",
        account_number=account_number or "N/A",
        period=period or "N/A",
    )
    
    exporter = ExcelExporter()
    buffer = exporter.export(
        transactions=export_txns,
        config=config,
    )
    
    filename = f"reconciliation_{run_id[:8]}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.post("/export/pdf")
async def export_reconciliation_pdf(
    run_id: str,
    company_name: str = "",
    account_number: str = "",
    period: str = "",
):
    """
    Export reconciliation results to PDF report.
    (Placeholder — PDF generation coming in Phase 3)
    """
    return {"status": "not_implemented", "message": "PDF export coming in Phase 3"}
