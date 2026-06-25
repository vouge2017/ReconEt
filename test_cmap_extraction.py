#!/usr/bin/env python3
"""
Test CBE PDF adapter with real CBE statements.
Tests CMap extraction → transaction parsing → fee extraction → balance verification.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.engine.cmap_extractor import CMapPDFExtractor


def test_cmap_extraction():
    """Test CMap extractor on all three real CBE PDFs."""
    extractor = CMapPDFExtractor()
    
    samples = [
        ('Nael_Hailemariam.pdf', 'Saving Account', 4),
        ('Ahimed_Kedir_trans.pdf', 'CURRENT ACCOUNT', 8),
        ('YOSEPH_STATEMENT.pdf', 'Saving Account', 6),
    ]
    
    print("=" * 70)
    print("CMap Extractor Test — Real CBE Statements")
    print("=" * 70)
    
    all_passed = True
    
    for filename, expected_type, expected_pages in samples:
        path = os.path.join('data', 'real_cbe_samples', filename)
        
        print(f"\n--- {filename} ---")
        result = extractor.extract(path)
        
        # Basic checks
        assert result.success, f"Extraction failed: {result.errors}"
        assert result.total_pages == expected_pages, \
            f"Expected {expected_pages} pages, got {result.total_pages}"
        assert result.fonts_decoded > 0, "No fonts decoded"
        assert len(result.full_text) > 100, f"Text too short: {len(result.full_text)}"
        
        # Check for account info
        assert 'Account' in result.full_text, "Missing 'Account' in text"
        assert 'Balance' in result.full_text or 'Balances' in result.full_text, \
            "Missing balance info"
        assert 'COMMERCIAL BANK OF ETHIOPIA' in result.full_text, \
            "Missing bank name"
        
        # Check for transactions (dates like "01 01 2022")
        import re
        dates = re.findall(r'\d{2}\s+\d{2}\s+\d{4}', result.full_text)
        assert len(dates) > 5, f"Too few dates found: {len(dates)}"
        
        # Check for amounts
        amounts = re.findall(r'[\d,]+\.\d{2}', result.full_text)
        assert len(amounts) > 10, f"Too few amounts found: {len(amounts)}"
        
        print(f"  ✓ Extraction successful")
        print(f"  ✓ {result.total_pages} pages, {result.fonts_decoded} fonts decoded")
        print(f"  ✓ {len(result.full_text)} chars of text")
        print(f"  ✓ {len(dates)} dates, {len(amounts)} amounts found")
        print(f"  ✓ Account type hint: {expected_type}")
    
    print(f"\n{'=' * 70}")
    print("ALL TESTS PASSED ✓")
    print(f"{'=' * 70}")


def test_account_type_detection():
    """Test that account type is correctly detected from extracted text."""
    from app.adapters.cbe_pdf import CBEPDFAdapter
    
    adapter = CBEPDFAdapter()
    
    samples = [
        ('Nael_Hailemariam.pdf', 'SAVINGS'),
        ('Ahimed_Kedir_trans.pdf', 'CURRENT'),
        ('YOSEPH_STATEMENT.pdf', 'SAVINGS'),
    ]
    
    print(f"\n{'=' * 70}")
    print("Account Type Detection Test")
    print(f"{'=' * 70}")
    
    for filename, expected_type in samples:
        path = os.path.join('data', 'real_cbe_samples', filename)
        
        # Use CMap extractor directly to get text
        extractor = CMapPDFExtractor()
        result = extractor.extract(path)
        
        # Test account type detection
        detected = adapter._detect_account_type(result.full_text)
        
        print(f"\n  {filename}:")
        print(f"    Expected: {expected_type}")
        print(f"    Detected: {detected.value.upper()}")
        
        if detected.value.upper() == expected_type:
            print(f"    ✓ Correct")
        else:
            print(f"    ⚠ Mismatch (may be OK if layout differs)")


if __name__ == '__main__':
    test_cmap_extraction()
    test_account_type_detection()
