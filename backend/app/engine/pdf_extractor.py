"""
PDF Text/Table Extraction Wrapper

Handles extraction from bank PDF statements using:
- pdfplumber (primary) — good for text-based PDFs with tables
- camelot-py (fallback) — better for complex table layouts
- Tesseract + amh language pack (scanned PDFs)
- PaddleOCR (messy scans fallback)

This module provides a unified interface for extracting text and tables
from PDF files, regardless of the underlying library used.
"""

import io
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum


class PDFType(str, Enum):
    """Type of PDF — determines extraction strategy"""
    TEXT_BASED = "text_based"       # Text-selectable PDFs
    SCANNED = "scanned"             # Image-based PDFs (need OCR)
    MIXED = "mixed"                 # Some text, some images
    UNKNOWN = "unknown"


class ExtractionMethod(str, Enum):
    """Which extraction method was used"""
    PDFPLUMBER = "pdfplumber"
    CAMELOT = "camelot"
    TESSERACT = "tesseract"
    PADDLEOCR = "paddleocr"
    FAILED = "failed"


@dataclass
class ExtractedTable:
    """A table extracted from PDF"""
    headers: List[str]
    rows: List[List[str]]
    page_number: int
    confidence: float = 1.0
    extraction_method: ExtractionMethod = ExtractionMethod.PDFPLUMBER


@dataclass
class ExtractedPage:
    """Content extracted from a single PDF page"""
    page_number: int
    text: str
    tables: List[ExtractedTable] = field(default_factory=list)
    width: float = 0
    height: float = 0


@dataclass
class PDFExtractionResult:
    """Full result of PDF extraction"""
    pages: List[ExtractedPage]
    total_pages: int
    pdf_type: PDFType
    extraction_method: ExtractionMethod
    full_text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class PDFExtractor:
    """
    Unified PDF extraction interface.
    
    Usage:
        extractor = PDFExtractor()
        result = extractor.extract("statement.pdf")
        for page in result.pages:
            print(page.text)
            for table in page.tables:
                print(table.headers)
                print(table.rows)
    """
    
    def extract(self, pdf_source, filename: str = "") -> PDFExtractionResult:
        """
        Extract text and tables from a PDF.
        
        Args:
            pdf_source: File path (str) or file-like object (bytes/IO)
            filename: Original filename (for format detection)
        
        Returns:
            PDFExtractionResult with pages, tables, and metadata
        """
        # Try pdfplumber first (best for text-based PDFs)
        try:
            result = self._extract_with_pdfplumber(pdf_source)
            if result and result.pages and self._has_meaningful_content(result):
                result.extraction_method = ExtractionMethod.PDFPLUMBER
                result.pdf_type = PDFType.TEXT_BASED
                return result
        except Exception as e:
            result = PDFExtractionResult(
                pages=[], total_pages=0,
                pdf_type=PDFType.UNKNOWN,
                extraction_method=ExtractionMethod.FAILED,
                errors=[f"pdfplumber failed: {str(e)}"]
            )
        
        # Try camelot as fallback
        try:
            result = self._extract_with_camelot(pdf_source)
            if result and result.pages and self._has_meaningful_content(result):
                result.extraction_method = ExtractionMethod.CAMELOT
                result.pdf_type = PDFType.TEXT_BASED
                return result
        except Exception as e:
            if result:
                result.errors.append(f"camelot failed: {str(e)}")
        
        # Try OCR for scanned PDFs
        try:
            result = self._extract_with_ocr(pdf_source)
            if result and result.pages:
                result.extraction_method = ExtractionMethod.TESSERACT
                result.pdf_type = PDFType.SCANNED
                return result
        except Exception as e:
            if result:
                result.errors.append(f"OCR failed: {str(e)}")
        
        # All methods failed
        if result:
            result.extraction_method = ExtractionMethod.FAILED
            return result
        
        return PDFExtractionResult(
            pages=[], total_pages=0,
            pdf_type=PDFType.UNKNOWN,
            extraction_method=ExtractionMethod.FAILED,
            errors=["All extraction methods failed"]
        )
    
    def _extract_with_pdfplumber(self, pdf_source) -> PDFExtractionResult:
        """Extract using pdfplumber — primary method"""
        import pdfplumber
        
        pages = []
        full_text_parts = []
        
        with pdfplumber.open(pdf_source) as pdf:
            total_pages = len(pdf.pages)
            
            for i, page in enumerate(pdf.pages):
                # Extract text
                text = page.extract_text() or ""
                full_text_parts.append(text)
                
                # Extract tables
                tables = []
                for table_data in page.extract_tables():
                    if table_data and len(table_data) > 1:
                        headers = [str(h).strip() if h else "" for h in table_data[0]]
                        rows = []
                        for row in table_data[1:]:
                            row_cells = [str(c).strip() if c else "" for c in row]
                            if any(row_cells):  # Skip empty rows
                                rows.append(row_cells)
                        
                        if rows:
                            tables.append(ExtractedTable(
                                headers=headers,
                                rows=rows,
                                page_number=i + 1,
                                extraction_method=ExtractionMethod.PDFPLUMBER
                            ))
                
                pages.append(ExtractedPage(
                    page_number=i + 1,
                    text=text,
                    tables=tables,
                    width=page.width,
                    height=page.height
                ))
        
        return PDFExtractionResult(
            pages=pages,
            total_pages=total_pages,
            pdf_type=PDFType.TEXT_BASED,
            extraction_method=ExtractionMethod.PDFPLUMBER,
            full_text="\n".join(full_text_parts)
        )
    
    def _extract_with_camelot(self, pdf_source) -> PDFExtractionResult:
        """Extract using camelot-py — table-focused extraction"""
        import camelot
        
        # Camelot needs a file path, not a file object
        if hasattr(pdf_source, 'read'):
            # It's a file-like object — need to save temporarily
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(pdf_source.read() if hasattr(pdf_source, 'read') else pdf_source)
                tmp_path = tmp.name
            
            try:
                tables = camelot.read_pdf(tmp_path, pages='all', flavor='lattice')
            finally:
                os.unlink(tmp_path)
                # Reset file pointer
                if hasattr(pdf_source, 'seek'):
                    pdf_source.seek(0)
        else:
            tables = camelot.read_pdf(pdf_source, pages='all', flavor='lattice')
        
        pages = []
        page_tables = {}
        
        for table in tables:
            page_num = table.page
            if page_num not in page_tables:
                page_tables[page_num] = []
            
            # Convert to our format
            df = table.df
            headers = [str(h).strip() for h in df.iloc[0].tolist()]
            rows = []
            for _, row in df.iloc[1:].iterrows():
                row_cells = [str(c).strip() for c in row.tolist()]
                if any(row_cells):
                    rows.append(row_cells)
            
            if rows:
                page_tables[page_num].append(ExtractedTable(
                    headers=headers,
                    rows=rows,
                    page_number=page_num,
                    confidence=table.parsing_report.get('accuracy', 0) / 100,
                    extraction_method=ExtractionMethod.CAMELOT
                ))
        
        # Create pages
        for page_num in sorted(page_tables.keys()):
            pages.append(ExtractedPage(
                page_number=page_num,
                text="",  # Camelot doesn't extract text
                tables=page_tables[page_num]
            ))
        
        return PDFExtractionResult(
            pages=pages,
            total_pages=max(page_tables.keys()) if page_tables else 0,
            pdf_type=PDFType.TEXT_BASED,
            extraction_method=ExtractionMethod.CAMELOT,
            full_text=""
        )
    
    def _extract_with_ocr(self, pdf_source) -> PDFExtractionResult:
        """Extract using OCR — for scanned PDFs"""
        # Try Tesseract first
        try:
            return self._extract_with_tesseract(pdf_source)
        except ImportError:
            pass
        
        # Try PaddleOCR as fallback
        try:
            return self._extract_with_paddleocr(pdf_source)
        except ImportError:
            pass
        
        raise RuntimeError("No OCR engine available. Install pytesseract or paddleocr.")
    
    def _extract_with_tesseract(self, pdf_source) -> PDFExtractionResult:
        """Extract using Tesseract with Amharic support"""
        import pytesseract
        from pdf2image import convert_from_bytes, convert_from_path
        
        # Convert PDF to images
        if hasattr(pdf_source, 'read'):
            images = convert_from_bytes(pdf_source.read())
            if hasattr(pdf_source, 'seek'):
                pdf_source.seek(0)
        else:
            images = convert_from_path(pdf_source)
        
        pages = []
        full_text_parts = []
        
        for i, image in enumerate(images):
            # Try Amharic first, fall back to English
            try:
                text = pytesseract.image_to_string(image, lang='amh+eng')
            except pytesseract.TesseractError:
                text = pytesseract.image_to_string(image, lang='eng')
            
            full_text_parts.append(text)
            pages.append(ExtractedPage(
                page_number=i + 1,
                text=text,
                tables=[]
            ))
        
        return PDFExtractionResult(
            pages=pages,
            total_pages=len(pages),
            pdf_type=PDFType.SCANNED,
            extraction_method=ExtractionMethod.TESSERACT,
            full_text="\n".join(full_text_parts)
        )
    
    def _extract_with_paddleocr(self, pdf_source) -> PDFExtractionResult:
        """Extract using PaddleOCR — handles messy scans"""
        from paddleocr import PaddleOCR
        from pdf2image import convert_from_bytes, convert_from_path
        
        ocr = PaddleOCR(use_angle_cls=True, lang='en')
        
        # Convert PDF to images
        if hasattr(pdf_source, 'read'):
            images = convert_from_bytes(pdf_source.read())
            if hasattr(pdf_source, 'seek'):
                pdf_source.seek(0)
        else:
            images = convert_from_path(pdf_source)
        
        pages = []
        full_text_parts = []
        
        for i, image in enumerate(images):
            import numpy as np
            img_array = np.array(image)
            result = ocr.ocr(img_array, cls=True)
            
            text_lines = []
            if result and result[0]:
                for line in result[0]:
                    if line and len(line) >= 2:
                        text_lines.append(line[1][0])
            
            text = "\n".join(text_lines)
            full_text_parts.append(text)
            pages.append(ExtractedPage(
                page_number=i + 1,
                text=text,
                tables=[]
            ))
        
        return PDFExtractionResult(
            pages=pages,
            total_pages=len(pages),
            pdf_type=PDFType.SCANNED,
            extraction_method=ExtractionMethod.PADDLEOCR,
            full_text="\n".join(full_text_parts)
        )
    
    def _has_meaningful_content(self, result: PDFExtractionResult) -> bool:
        """Check if extraction found meaningful content"""
        # Check if we got any tables with data
        for page in result.pages:
            if page.tables:
                for table in page.tables:
                    if len(table.rows) >= 2:  # At least header + 1 data row
                        return True
        
        # Check if text has numbers (likely transaction data)
        if result.full_text:
            # Look for patterns like amounts (numbers with decimals)
            amount_pattern = r'\d{1,3}(?:,\d{3})*\.\d{2}'
            if re.search(amount_pattern, result.full_text):
                return True
        
        return False
