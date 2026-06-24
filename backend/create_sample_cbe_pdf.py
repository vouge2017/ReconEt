"""
Generate a sample CBE PDF statement for testing.

This creates a realistic CBE-style PDF with:
- Statement header with account info
- Transaction table with CBE column layout
- Opening/closing balances
- Various transaction types (FT, CHQ, CD, CPO, ECS)
- Fee-bearing transactions

Usage:
    python create_sample_cbe_pdf.py
"""

import os

try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm, cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

if not HAS_REPORTLAB:
    # Fallback: create a simple text-based "PDF" using fpdf2
    try:
        from fpdf import FPDF
        HAS_FPDF = True
    except ImportError:
        HAS_FPDF = False


def create_sample_pdf_with_reportlab(output_path: str):
    """Create sample CBE PDF using reportlab"""
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=1*cm,
        leftMargin=1*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm,
    )
    
    styles = getSampleStyleSheet()
    elements = []
    
    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        alignment=TA_CENTER,
        fontSize=14,
        spaceAfter=6,
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        alignment=TA_CENTER,
        fontSize=11,
        spaceAfter=4,
    )
    
    normal_style = styles['Normal']
    
    # Header
    elements.append(Paragraph("Commercial Bank of Ethiopia", title_style))
    elements.append(Paragraph("Account Statement", subtitle_style))
    elements.append(Spacer(1, 4*mm))
    
    # Account info
    account_info = [
        ["Account Name:", "Ethiopian Trading Corp", "Account No:", "1000123456789"],
        ["Account Type:", "Current Account", "Currency:", "ETB"],
        ["Period From:", "01/06/2026", "Period To:", "30/06/2026"],
    ]
    
    info_table = Table(account_info, colWidths=[80, 150, 80, 150])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 4*mm))
    
    # Opening balance
    elements.append(Paragraph("<b>Opening Balance:</b> 2,550,000.00", normal_style))
    elements.append(Spacer(1, 4*mm))
    
    # Transaction table - Current Account layout
    # Columns: Date | Particulars | Reference | Narrative | Value Date | Debit | Credit | Balances
    headers = ["Date", "Particulars", "Reference", "Narrative", "Value Date", "Debit", "Credit", "Balances"]
    
    transactions = [
        ["15/06/2026", "TRANSFER", "FT-2026-001", "TRANSFER TO ABC TRADING FEE 25 TAX 15", "15/06/2026", "100,040.00", "", "2,449,960.00"],
        ["16/06/2026", "SALARY", "ECS-2026-001", "SALARY PAYMENT TO STAFF ACCOUNT 1001 FEE 10 TAX 1.50", "16/06/2026", "50,011.50", "", "2,399,948.50"],
        ["16/06/2026", "DEPOSIT", "CD-2026-001", "CASH DEPOSIT FROM CUSTOMER", "16/06/2026", "", "250,000.00", "2,649,948.50"],
        ["17/06/2026", "TRANSFER", "FT-2026-002", "TRANSFER TO DASHEN BANK FEE 25 TAX 3.75", "17/06/2026", "75,028.75", "", "2,574,919.75"],
        ["17/06/2026", "CHEQUE", "CHQ-001234", "CHEQUE PAYMENT TO SUPPLIER XYZ", "17/06/2026", "200,000.00", "", "2,374,919.75"],
        ["18/06/2026", "STANDING ORDER", "SO-001", "STANDING ORDER RENT PAYMENT FEE 15 TAX 2.25", "18/06/2026", "15,017.25", "", "2,359,902.50"],
        ["18/06/2026", "TRANSFER", "FT-2026-003", "TRANSFER TO ECOBANK ACCOUNT 2001", "18/06/2026", "300,000.00", "", "2,059,902.50"],
        ["19/06/2026", "DRAFT", "CPO-2026-001", "DRAFT ISSUANCE FEE 50 TAX 7.50", "19/06/2026", "50,050.00", "", "2,009,852.50"],
        ["19/06/2026", "RECEIPT", "CD-2026-002", "RECEIPT FROM CUSTOMER ABC", "19/06/2026", "", "100,000.00", "2,109,852.50"],
        ["20/06/2026", "CERTIFICATE", "FT-2026-004", "BALANCE CERTIFICATE FEE 100 TAX 15", "20/06/2026", "100,115.00", "", "2,009,737.50"],
    ]
    
    data = [headers] + transactions
    
    # Create table
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        # Header style
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a365d')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        
        # Data rows
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ALIGN', (5, 1), (7, -1), 'RIGHT'),  # Amounts right-aligned
        ('ALIGN', (0, 1), (4, -1), 'LEFT'),
        
        # Alternating row colors
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#f7fafc')),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#f7fafc')),
        ('BACKGROUND', (0, 5), (-1, 5), colors.HexColor('#f7fafc')),
        ('BACKGROUND', (0, 7), (-1, 7), colors.HexColor('#f7fafc')),
        ('BACKGROUND', (0, 9), (-1, 9), colors.HexColor('#f7fafc')),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 4*mm))
    
    # Closing balance
    elements.append(Paragraph("<b>Closing Balance:</b> 2,009,737.50", normal_style))
    elements.append(Spacer(1, 2*mm))
    elements.append(Paragraph("<b>Total Credits:</b> 350,000.00 &nbsp;&nbsp;&nbsp; <b>Total Debits:</b> 890,262.50", normal_style))
    
    # Build PDF
    doc.build(elements)
    print(f"✅ Sample CBE PDF created: {output_path}")


def create_sample_pdf_with_fpdf(output_path: str):
    """Create sample CBE PDF using fpdf2 (lighter alternative)"""
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    # Title
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, 'Commercial Bank of Ethiopia', 0, 1, 'C')
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 8, 'Account Statement', 0, 1, 'C')
    pdf.ln(4)
    
    # Account info
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(40, 6, 'Account Name:', 0, 0)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(60, 6, 'Ethiopian Trading Corp', 0, 0)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(40, 6, 'Account No:', 0, 0)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(60, 6, '1000123456789', 0, 1)
    
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(40, 6, 'Account Type:', 0, 0)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(60, 6, 'Current Account', 0, 0)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(40, 6, 'Currency:', 0, 0)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(60, 6, 'ETB', 0, 1)
    
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(40, 6, 'Period From:', 0, 0)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(60, 6, '01/06/2026', 0, 0)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(40, 6, 'Period To:', 0, 0)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(60, 6, '30/06/2026', 0, 1)
    
    pdf.ln(4)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(40, 6, 'Opening Balance:', 0, 0)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(60, 6, '2,550,000.00', 0, 1)
    pdf.ln(4)
    
    # Table header
    headers = ["Date", "Particulars", "Reference", "Narrative", "Value Date", "Debit", "Credit", "Balances"]
    col_widths = [22, 25, 28, 90, 22, 30, 30, 30]
    
    pdf.set_font('Helvetica', 'B', 7)
    pdf.set_fill_color(26, 54, 93)
    pdf.set_text_color(255, 255, 255)
    
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 6, header, 1, 0, 'C', True)
    pdf.ln()
    
    # Transaction data
    transactions = [
        ["15/06/2026", "TRANSFER", "FT-2026-001", "TRANSFER TO ABC TRADING FEE 25 TAX 15", "15/06/2026", "100,040.00", "", "2,449,960.00"],
        ["16/06/2026", "SALARY", "ECS-2026-001", "SALARY PAYMENT TO STAFF ACCOUNT 1001 FEE 10 TAX 1.50", "16/06/2026", "50,011.50", "", "2,399,948.50"],
        ["16/06/2026", "DEPOSIT", "CD-2026-001", "CASH DEPOSIT FROM CUSTOMER", "16/06/2026", "", "250,000.00", "2,649,948.50"],
        ["17/06/2026", "TRANSFER", "FT-2026-002", "TRANSFER TO DASHEN BANK FEE 25 TAX 3.75", "17/06/2026", "75,028.75", "", "2,574,919.75"],
        ["17/06/2026", "CHEQUE", "CHQ-001234", "CHEQUE PAYMENT TO SUPPLIER XYZ", "17/06/2026", "200,000.00", "", "2,374,919.75"],
        ["18/06/2026", "STANDING ORDER", "SO-001", "STANDING ORDER RENT PAYMENT FEE 15 TAX 2.25", "18/06/2026", "15,017.25", "", "2,359,902.50"],
        ["18/06/2026", "TRANSFER", "FT-2026-003", "TRANSFER TO ECOBANK ACCOUNT 2001", "18/06/2026", "300,000.00", "", "2,059,902.50"],
        ["19/06/2026", "DRAFT", "CPO-2026-001", "DRAFT ISSUANCE FEE 50 TAX 7.50", "19/06/2026", "50,050.00", "", "2,009,852.50"],
        ["19/06/2026", "RECEIPT", "CD-2026-002", "RECEIPT FROM CUSTOMER ABC", "19/06/2026", "", "100,000.00", "2,109,852.50"],
        ["20/06/2026", "CERTIFICATE", "FT-2026-004", "BALANCE CERTIFICATE FEE 100 TAX 15", "20/06/2026", "100,115.00", "", "2,009,737.50"],
    ]
    
    pdf.set_font('Helvetica', '', 7)
    pdf.set_text_color(0, 0, 0)
    
    for row_idx, row in enumerate(transactions):
        if row_idx % 2 == 0:
            pdf.set_fill_color(247, 250, 252)
        else:
            pdf.set_fill_color(255, 255, 255)
        
        for i, cell in enumerate(row):
            align = 'R' if i >= 5 else 'L'
            pdf.cell(col_widths[i], 5, cell, 1, 0, align, True)
        pdf.ln()
    
    pdf.ln(4)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(40, 6, 'Closing Balance:', 0, 0)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(60, 6, '2,009,737.50', 0, 1)
    
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(40, 6, 'Total Credits:', 0, 0)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(60, 6, '350,000.00', 0, 0)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(40, 6, 'Total Debits:', 0, 0)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(60, 6, '890,262.50', 0, 1)
    
    pdf.output(output_path)
    print(f"✅ Sample CBE PDF created: {output_path}")


def main():
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, "sample_cbe_statement.pdf")
    
    if HAS_REPORTLAB:
        create_sample_pdf_with_reportlab(output_path)
    elif HAS_FPDF:
        create_sample_pdf_with_fpdf(output_path)
    else:
        print("❌ Neither reportlab nor fpdf2 is installed.")
        print("Install one of them:")
        print("  pip install reportlab")
        print("  pip install fpdf2")
        return
    
    print(f"\nFile size: {os.path.getsize(output_path):,} bytes")
    print(f"Location: {output_path}")


if __name__ == "__main__":
    main()
