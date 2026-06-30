"""
Bank Auto-Detector — ReconET

Automatically detects which bank a PDF statement is from
based on content analysis. Routes to the correct adapter.

Supported banks:
- CBE (Commercial Bank of Ethiopia) — fully implemented
- Dashen Bank — stub
- Awash Bank — stub

Usage:
    from app.adapters.bank_detector import detect_and_parse
    
    result = detect_and_parse("statement.pdf")
    if result["status"] == "success":
        for txn in result["transactions"]:
            print(txn)
"""
from typing import Dict, Optional
import io


def detect_bank_from_text(text: str) -> str:
    """
    Detect bank from PDF text content.
    
    Returns: bank identifier string
    """
    text_upper = text.upper()
    
    # CBE indicators
    cbe_keywords = [
        "COMMERCIAL BANK OF ETHIOPIA",
        "CBE",
        "DEVEXP+",  # CBE's custom font
        "CBE-BIRR",
    ]
    if any(kw in text_upper for kw in cbe_keywords):
        return "cbe"
    
    # Dashen indicators
    dashen_keywords = [
        "DASHEN BANK",
        "DASHEN BANK S.C",
        "DASHEN BANK SHARE COMPANY",
    ]
    if any(kw in text_upper for kw in dashen_keywords):
        return "dashen"
    
    # Awash indicators
    awash_keywords = [
        "AWASH BANK",
        "AWASH BANK S.C",
        "AWASH INTERNATIONAL BANK",
    ]
    if any(kw in text_upper for kw in awash_keywords):
        return "awash"
    
    # Default to CBE (most common)
    return "cbe"


def detect_and_parse(pdf_source, filename: str = "") -> Dict:
    """
    Auto-detect bank and parse PDF statement.
    
    Args:
        pdf_source: File path, bytes, or file-like object
        filename: Original filename
    
    Returns:
        Dict with parsed transactions, verification, etc.
    """
    from app.adapters.cbe_pdf import CBEPDFAdapter
    
    # Try CMap extraction first to get text for bank detection
    try:
        from app.engine.cmap_extractor import CMapPDFExtractor
        cmap = CMapPDFExtractor()
        
        if isinstance(pdf_source, str):
            with open(pdf_source, 'rb') as f:
                data = f.read()
        elif hasattr(pdf_source, 'read'):
            data = pdf_source.read()
            if hasattr(pdf_source, 'seek'):
                pdf_source.seek(0)
        else:
            data = pdf_source
        
        cmap_result = cmap.extract(data)
        text = cmap_result.full_text if cmap_result.success else ""
    except Exception:
        text = ""
    
    # If no text from CMap, try pdfplumber
    if not text.strip():
        try:
            import pdfplumber
            if isinstance(pdf_source, str):
                with pdfplumber.open(pdf_source) as pdf:
                    text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            else:
                with pdfplumber.open(io.BytesIO(data)) as pdf:
                    text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception:
            pass
    
    # Detect bank
    bank = detect_bank_from_text(text)
    
    # Route to appropriate adapter
    if bank == "cbe":
        adapter = CBEPDFAdapter()
        result = adapter.parse(io.BytesIO(data) if not isinstance(pdf_source, str) else pdf_source, filename)
        return {
            "bank": "cbe",
            "bank_name": "Commercial Bank of Ethiopia",
            "status": "success" if result.transactions else "failed",
            "account_type": result.account_type.value,
            "account_number": result.account_number,
            "account_name": result.account_name,
            "statement_period": result.statement_period,
            "opening_balance": result.opening_balance,
            "closing_balance": result.closing_balance,
            "transactions": [t.to_dict() for t in result.transactions],
            "verification": {
                "status": result.verification.status.value,
                "message": result.verification.message,
            },
            "extraction_details": result.extraction_details,
            "errors": result.errors,
            "warnings": result.warnings,
        }
    elif bank == "dashen":
        from app.adapters.dashen_pdf import DashenPDFAdapter
        adapter = DashenPDFAdapter()
        result = adapter.parse(pdf_source, filename)
        return {
            "bank": "dashen",
            "bank_name": "Dashen Bank",
            "status": result.status,
            "errors": result.errors,
            "warnings": result.warnings,
            "transactions": [],
        }
    elif bank == "awash":
        from app.adapters.awash_pdf import AwashPDFAdapter
        adapter = AwashPDFAdapter()
        result = adapter.parse(pdf_source, filename)
        return {
            "bank": "awash",
            "bank_name": "Awash Bank",
            "status": result.status,
            "errors": result.errors,
            "warnings": result.warnings,
            "transactions": [],
        }
    else:
        return {
            "bank": "unknown",
            "bank_name": "Unknown Bank",
            "status": "failed",
            "errors": ["Could not detect bank from PDF content"],
            "transactions": [],
        }
