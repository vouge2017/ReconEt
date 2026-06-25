"""
Tests for CMap PDF Extractor

Tests against real CBE bank statements to ensure:
- All pages extracted
- All fonts decoded
- Text content is meaningful
- Account info is present
- Transaction data is extractable
"""

import os
import re
import pytest

# Add backend to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.engine.cmap_extractor import CMapPDFExtractor, CMapExtractionResult


# Test data paths
SAMPLES_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'real_cbe_samples')
NAEL_PDF = os.path.join(SAMPLES_DIR, 'Nael_Hailemariam.pdf')
AHIMED_PDF = os.path.join(SAMPLES_DIR, 'Ahimed_Kedir_trans.pdf')
YOSEPH_PDF = os.path.join(SAMPLES_DIR, 'YOSEPH_STATEMENT.pdf')


@pytest.fixture
def extractor():
    return CMapPDFExtractor()


class TestCMapExtractor:
    """Test CMap extraction on real CBE PDFs"""
    
    def test_nael_hailemariam(self, extractor):
        """Test extraction of Nael Hailemariam savings statement"""
        result = extractor.extract(NAEL_PDF)
        
        assert result.success is True
        assert result.total_pages == 4
        assert result.fonts_decoded == 6
        assert len(result.full_text) > 5000
        
        # Check for account info
        assert 'Account' in result.full_text
        assert '1000066001079' in result.full_text
        assert 'NAEL HAILEMARIAM' in result.full_text
        assert 'COMMERCIAL BANK OF ETHIOPIA' in result.full_text
        
        # Check for transaction data
        dates = re.findall(r'\d{2}\s+\d{2}\s+\d{4}', result.full_text)
        assert len(dates) > 50  # Should have many transactions
        
        amounts = re.findall(r'[\d,]+\.\d{2}', result.full_text)
        assert len(amounts) > 50
    
    def test_ahimed_kedir(self, extractor):
        """Test extraction of Ahimed Kedir current account statement"""
        result = extractor.extract(AHIMED_PDF)
        
        assert result.success is True
        assert result.total_pages == 8
        assert result.fonts_decoded == 6
        assert len(result.full_text) > 15000
        
        # Check for account info
        assert '1000357122717' in result.full_text
        assert 'AHIMED KEDIR' in result.full_text
        assert 'CURRENT ACCOUNT' in result.full_text
        
        # Check for business transactions
        assert 'Transfer' in result.full_text or 'TRANSFER' in result.full_text
        assert 'CHQ' in result.full_text  # Cheque transactions
    
    def test_yoseph_statement(self, extractor):
        """Test extraction of Yoseph/Sara Birmeka savings statement"""
        result = extractor.extract(YOSEPH_PDF)
        
        assert result.success is True
        assert result.total_pages == 6
        assert result.fonts_decoded == 6
        assert len(result.full_text) > 8000
        
        # Check for account info
        assert '1000009464658' in result.full_text
        assert 'SARA BIRMEKA' in result.full_text
    
    def test_page_count_accuracy(self, extractor):
        """Verify page counts match actual PDF pages"""
        for pdf, expected_pages in [
            (NAEL_PDF, 4),
            (AHIMED_PDF, 8),
            (YOSEPH_PDF, 6),
        ]:
            result = extractor.extract(pdf)
            assert result.total_pages == expected_pages, \
                f"{pdf}: expected {expected_pages} pages, got {result.total_pages}"
    
    def test_font_decoding(self, extractor):
        """Verify all fonts are decoded for each PDF"""
        for pdf in [NAEL_PDF, AHIMED_PDF, YOSEPH_PDF]:
            result = extractor.extract(pdf)
            assert result.fonts_decoded == 6, \
                f"{pdf}: expected 6 fonts, got {result.fonts_decoded}"
    
    def test_text_not_empty(self, extractor):
        """Verify extracted text is not empty"""
        for pdf in [NAEL_PDF, AHIMED_PDF, YOSEPH_PDF]:
            result = extractor.extract(pdf)
            assert result.full_text.strip(), f"{pdf}: extracted text is empty"
    
    def test_contains_bank_name(self, extractor):
        """Verify CBE bank name is in extracted text"""
        for pdf in [NAEL_PDF, AHIMED_PDF, YOSEPH_PDF]:
            result = extractor.extract(pdf)
            assert 'COMMERCIAL BANK OF ETHIOPIA' in result.full_text, \
                f"{pdf}: missing bank name"
    
    def test_contains_balance_info(self, extractor):
        """Verify balance information is present"""
        for pdf in [NAEL_PDF, AHIMED_PDF, YOSEPH_PDF]:
            result = extractor.extract(pdf)
            text_upper = result.full_text.upper()
            assert 'BALANCE' in text_upper or 'BALANCES' in text_upper, \
                f"{pdf}: missing balance info"
    
    def test_contains_dates(self, extractor):
        """Verify dates are present in extracted text"""
        for pdf in [NAEL_PDF, AHIMED_PDF, YOSEPH_PDF]:
            result = extractor.extract(pdf)
            dates = re.findall(r'\d{2}\s+\d{2}\s+\d{4}', result.full_text)
            assert len(dates) > 10, f"{pdf}: too few dates found ({len(dates)})"
    
    def test_contains_amounts(self, extractor):
        """Verify monetary amounts are present"""
        for pdf in [NAEL_PDF, AHIMED_PDF, YOSEPH_PDF]:
            result = extractor.extract(pdf)
            amounts = re.findall(r'[\d,]+\.\d{2}', result.full_text)
            assert len(amounts) > 20, f"{pdf}: too few amounts found ({len(amounts)})"
    
    def test_each_page_has_content(self, extractor):
        """Verify each page has meaningful content"""
        for pdf in [NAEL_PDF, AHIMED_PDF, YOSEPH_PDF]:
            result = extractor.extract(pdf)
            for i, page in enumerate(result.pages):
                assert page.full_text.strip(), \
                    f"{pdf} page {i+1}: empty content"
                assert len(page.full_text) > 100, \
                    f"{pdf} page {i+1}: too short ({len(page.full_text)} chars)"


class TestCMapExtractorEdgeCases:
    """Test edge cases"""
    
    def test_nonexistent_file(self, extractor):
        """Test with non-existent file"""
        result = extractor.extract('/nonexistent/file.pdf')
        assert result.success is False
        assert len(result.errors) > 0
    
    def test_invalid_bytes(self, extractor):
        """Test with invalid bytes"""
        result = extractor.extract(b'not a pdf')
        assert result.success is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
