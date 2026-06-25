"""
CMap-Based PDF Text Extractor

Extracts text from PDFs that use custom font encodings (like CBE's DEVEXP+ fonts).
These PDFs are text-based but use Identity-H encoding with ToUnicode CMaps,
making standard extractors (pdfplumber, Tesseract) fail or produce garbage.

This extractor:
1. Parses all PDF objects
2. Finds font objects with ToUnicode CMaps
3. Decompresses and parses CMap bfchar/bfrange mappings
4. For each page, decodes hex-encoded text using the CMaps
5. Reconstructs text lines from PDF text operators

Used by: CBE PDF adapter (primary extraction method)
Other banks (Dashen, Awash) may also use similar encoding — check first.
"""

import re
import zlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple


@dataclass
class CMapFont:
    """A font with its CMap character mapping"""
    obj_id: int
    base_name: str        # e.g. "DEVEXP+Arial,Bold"
    resource_name: str    # e.g. "F1", "F2"
    char_map: Dict[int, str] = field(default_factory=dict)


@dataclass
class CMapPage:
    """Text extracted from a single page via CMap decoding"""
    page_number: int
    text_lines: List[str]
    full_text: str


@dataclass
class CMapExtractionResult:
    """Result of CMap-based PDF extraction"""
    pages: List[CMapPage]
    full_text: str
    fonts_decoded: int
    total_pages: int
    success: bool
    errors: List[str] = field(default_factory=list)


class CMapPDFExtractor:
    """
    Extract text from PDFs with custom font CMaps.
    
    Usage:
        extractor = CMapPDFExtractor()
        result = extractor.extract("cbe_statement.pdf")
        
        if result.success:
            for page in result.pages:
                for line in page.text_lines:
                    print(line)
    """
    
    def extract(self, pdf_source) -> CMapExtractionResult:
        """
        Extract text from a PDF using CMap decoding.
        
        Args:
            pdf_source: File path (str) or bytes
            
        Returns:
            CMapExtractionResult with decoded text
        """
        errors = []
        
        # Read PDF data
        if isinstance(pdf_source, bytes):
            data = pdf_source
        elif isinstance(pdf_source, str):
            try:
                with open(pdf_source, 'rb') as f:
                    data = f.read()
            except (FileNotFoundError, PermissionError, OSError) as e:
                return CMapExtractionResult(
                    pages=[], full_text="", fonts_decoded=0,
                    total_pages=0, success=False,
                    errors=[f"Cannot read file: {str(e)}"]
                )
        elif hasattr(pdf_source, 'read'):
            data = pdf_source.read()
            if hasattr(pdf_source, 'seek'):
                pdf_source.seek(0)
        else:
            return CMapExtractionResult(
                pages=[], full_text="", fonts_decoded=0,
                total_pages=0, success=False,
                errors=["Invalid pdf_source type"]
            )
        
        try:
            # Step 1: Parse all objects
            objs = self._find_objects(data)
            
            # Step 2: Parse CMaps from font objects
            font_cmaps = self._parse_cmaps(data, objs)
            
            # Step 3: Build font object ID -> char_map mapping
            font_obj_map = {}
            for obj_id, cmap in font_cmaps.items():
                font_obj_map[obj_id] = cmap
            
            # Step 4: Find page objects
            pages = self._find_pages(data, objs)
            
            # Step 5: Extract text from each page
            result_pages = []
            all_text = []
            
            for page_num, page_data in pages:
                page = self._extract_page_text(
                    data, objs, page_data, font_obj_map, page_num
                )
                if page:
                    result_pages.append(page)
                    all_text.append(page.full_text)
            
            full_text = "\n".join(all_text)
            
            return CMapExtractionResult(
                pages=result_pages,
                full_text=full_text,
                fonts_decoded=len(font_cmaps),
                total_pages=len(pages),
                success=len(result_pages) > 0,
                errors=errors
            )
            
        except Exception as e:
            errors.append(f"CMap extraction failed: {str(e)}")
            return CMapExtractionResult(
                pages=[], full_text="", fonts_decoded=0,
                total_pages=0, success=False, errors=errors
            )
    
    def _find_objects(self, data: bytes) -> List[Tuple[int, int]]:
        """Find all PDF objects and their positions. Returns (obj_num, position)."""
        objs = []
        for match in re.finditer(rb'(\d+)\s+(\d+)\s+obj', data):
            obj_num = int(match.group(1))
            objs.append((obj_num, match.start()))
        return objs
    
    def _parse_cmaps(
        self, data: bytes, objs: List[Tuple[int, int]]
    ) -> Dict[int, Dict[int, str]]:
        """
        Parse ToUnicode CMaps from font objects.
        Returns dict of obj_id -> char_map.
        """
        font_cmaps = {}
        
        for obj_num, pos in objs:
            end = data.find(b'endobj', pos)
            if end == -1:
                continue
            obj_data = data[pos:end]
            
            # Check if this is a font with ToUnicode
            if b'/Type /Font' not in obj_data and b'/Type/Font' not in obj_data:
                continue
            
            tounicode = re.search(rb'/ToUnicode\s+(\d+)\s+0\s+R', obj_data)
            if not tounicode:
                continue
            
            cmap_obj_num = int(tounicode.group(1))
            
            # Find the CMap object
            cmap_pos = None
            for o_num, o_pos in objs:
                if o_num == cmap_obj_num:
                    cmap_pos = o_pos
                    break
            
            if cmap_pos is None:
                continue
            
            cmap_end = data.find(b'endobj', cmap_pos)
            if cmap_end == -1:
                continue
            cmap_data = data[cmap_pos:cmap_end]
            
            # Extract stream
            stream_start = cmap_data.find(b'stream')
            if stream_start == -1:
                continue
            
            nl = cmap_data.find(b'\n', stream_start)
            if nl == -1:
                nl = cmap_data.find(b'\r\n', stream_start)
            if nl == -1:
                continue
            
            stream_data = cmap_data[nl + 1:]
            endstream = stream_data.find(b'endstream')
            if endstream != -1:
                stream_data = stream_data[:endstream].strip()
            
            try:
                decompressed = zlib.decompress(stream_data)
                cmap_text = decompressed.decode('latin-1')
                char_map = self._parse_cmap_text(cmap_text)
                if char_map:
                    font_cmaps[obj_num] = char_map
            except Exception:
                continue
        
        return font_cmaps
    
    def _parse_cmap_text(self, cmap_text: str) -> Dict[int, str]:
        """Parse a CMap text into a character mapping dict."""
        char_map = {}
        
        # Parse bfchar blocks (handle both \n and \r\n line endings)
        for _count, block in re.findall(
            r'(\d+)\s+beginbfchar\r?\n(.*?)\r?\nendbfchar', cmap_text, re.DOTALL
        ):
            for src, dst in re.findall(r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', block):
                char_map[int(src, 16)] = chr(int(dst, 16))
        
        # Parse bfrange blocks
        for _count, block in re.findall(
            r'(\d+)\s+beginbfrange\r?\n(.*?)\r?\nendbfrange', cmap_text, re.DOTALL
        ):
            for s_hex, e_hex, d_hex in re.findall(
                r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', block
            ):
                s, e, d = int(s_hex, 16), int(e_hex, 16), int(d_hex, 16)
                for off in range(e - s + 1):
                    char_map[s + off] = chr(d + off)
        
        return char_map
    
    def _find_pages(
        self, data: bytes, objs: List[Tuple[int, int]]
    ) -> List[Tuple[int, bytes]]:
        """Find page objects. Returns list of (page_number, page_data)."""
        pages = []
        
        for obj_num, pos in objs:
            end = data.find(b'endobj', pos)
            if end == -1:
                continue
            obj_data = data[pos:end]
            
            if b'/Type /Page' in obj_data and b'/Type /Pages' not in obj_data:
                pages.append((obj_num, obj_data))
        
        return pages
    
    def _extract_page_text(
        self,
        data: bytes,
        objs: List[Tuple[int, int]],
        page_data: bytes,
        font_obj_map: Dict[int, Dict[int, str]],
        page_obj_num: int
    ) -> Optional[CMapPage]:
        """Extract text from a single page using CMap decoding."""
        
        # Get content stream reference
        content_ref = re.search(rb'/Contents\s+(\d+)\s+0\s+R', page_data)
        if not content_ref:
            return None
        content_num = int(content_ref.group(1))
        
        # Get font resource mappings: /F1 11 0 R means resource "F1" -> font obj 11
        font_refs = re.findall(rb'/(\w+)\s+(\d+)\s+0\s+R', page_data)
        page_font_map = {}  # resource_name -> char_map
        for name, ref in font_refs:
            ref_num = int(ref)
            if ref_num in font_obj_map:
                page_font_map[name.decode()] = font_obj_map[ref_num]
        
        # Find and decompress content stream
        content_pos = None
        for o_num, o_pos in objs:
            if o_num == content_num:
                content_pos = o_pos
                break
        
        if content_pos is None:
            return None
        
        content_end = data.find(b'endobj', content_pos)
        if content_end == -1:
            return None
        content_data = data[content_pos:content_end]
        
        stream_start = content_data.find(b'stream')
        if stream_start == -1:
            return None
        
        nl = content_data.find(b'\n', stream_start)
        if nl == -1:
            nl = content_data.find(b'\r\n', stream_start)
        if nl == -1:
            return None
        
        stream_data = content_data[nl + 1:]
        endstream = stream_data.find(b'endstream')
        if endstream != -1:
            stream_data = stream_data[:endstream].strip()
        
        try:
            decompressed = zlib.decompress(stream_data)
            content_text = decompressed.decode('latin-1')
        except Exception:
            return None
        
        # Parse text operations
        current_cmap = None
        text_lines = []
        current_line = []
        
        for line in content_text.split('\n'):
            line = line.strip()
            
            # Font selection: /F1 10 Tf
            font_match = re.match(r'/(\w+)\s+[\d.]+\s+Tf', line)
            if font_match:
                fname = font_match.group(1)
                if fname in page_font_map:
                    current_cmap = page_font_map[fname]
                continue
            
            # Text showing operations
            if current_cmap and ('Tj' in line or 'TJ' in line):
                # Hex strings: <002400250026> Tj
                for hex_str in re.findall(r'<([0-9A-Fa-f]+)>', line):
                    chars = []
                    for j in range(0, len(hex_str), 4):
                        if j + 4 <= len(hex_str):
                            code = int(hex_str[j:j + 4], 16)
                            chars.append(current_cmap.get(code, '?'))
                    text = ''.join(chars)
                    if text.strip():
                        current_line.append(text)
            
            # Line break operators
            if 'T*' in line or 'Td' in line or 'TD' in line:
                if current_line:
                    joined = ' '.join(current_line)
                    if joined.strip():
                        text_lines.append(joined)
                    current_line = []
        
        # Flush remaining line
        if current_line:
            joined = ' '.join(current_line)
            if joined.strip():
                text_lines.append(joined)
        
        full_text = '\n'.join(text_lines)
        
        return CMapPage(
            page_number=page_obj_num,
            text_lines=text_lines,
            full_text=full_text
        )


def extract_cbe_text(pdf_source) -> CMapExtractionResult:
    """
    Convenience function: Extract text from a CBE PDF statement.
    
    This is the primary extraction method for CBE PDFs.
    Other banks may need different handling.
    
    Args:
        pdf_source: File path, bytes, or file-like object
        
    Returns:
        CMapExtractionResult with decoded text
    """
    extractor = CMapPDFExtractor()
    return extractor.extract(pdf_source)
