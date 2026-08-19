import csv
import io
from datetime import datetime
from typing import List, Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_csv_report(data: List[Dict[str, Any]], fieldnames: List[str]) -> str:
    """Generate a CSV spreadsheet from list data."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in data:
        # Sanitize values to strings
        sanitized_row = {}
        for k, v in row.items():
            if isinstance(v, datetime):
                sanitized_row[k] = v.strftime("%Y-%m-%d %H:%M:%S")
            else:
                sanitized_row[k] = str(v) if v is not None else ""
        writer.writerow(sanitized_row)
    return output.getvalue()

def generate_pdf_report(
    report_title: str,
    metrics: Dict[str, Any],
    items: List[Dict[str, Any]],
    headers: List[str],
    keys: List[str]
) -> bytes:
    """Generate a styled PDF document using reportlab."""
    buffer = io.BytesIO()
    # Letter size page (612 x 792 pt). Margin 40pt leaves 532pt width
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    story = []
    
    # Custom Typography Style Sheets matching our editorial theme
    title_style = ParagraphStyle(
        name="ReportTitle",
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#2D5A27"),  # Forest brand green
        spaceAfter=8
    )
    
    subtitle_style = ParagraphStyle(
        name="ReportSubtitle",
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#A8A29E"),  # Stone accent grey
        spaceAfter=20
    )
    
    heading_style = ParagraphStyle(
        name="SectionHeading",
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#1C1C1C"),  # Charcoal text
        spaceAfter=10,
        spaceBefore=15
    )
    
    body_style = ParagraphStyle(
        name="ReportBody",
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1C1C1C")
    )
    
    header_style = ParagraphStyle(
        name="TableHeaderStyle",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.white
    )
    
    # 1. Document Title
    story.append(Paragraph(report_title, title_style))
    story.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC | Platform Impact Audit", subtitle_style))
    story.append(Spacer(1, 10))
    
    # 2. Metrics Grid Table
    story.append(Paragraph("Performance Metrics", heading_style))
    metric_data = []
    temp_row = []
    for label, val in metrics.items():
        temp_row.extend([
            Paragraph(f"<b>{label}:</b>", body_style),
            Paragraph(str(val), body_style)
        ])
        if len(temp_row) == 4:
            metric_data.append(temp_row)
            temp_row = []
            
    if temp_row:
        while len(temp_row) < 4:
            temp_row.append(Paragraph("", body_style))
        metric_data.append(temp_row)
        
    metric_table = Table(metric_data, colWidths=[120, 146, 120, 146])
    metric_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#FAF9F6")),  # Warm Ivory
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#E7E5E4")),  # Grey border
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E7E5E4")),
    ]))
    story.append(metric_table)
    story.append(Spacer(1, 15))
    
    # 3. Main Data Table
    story.append(Paragraph("Detailed Log Entries", heading_style))
    table_content = [[Paragraph(f"<b>{h}</b>", header_style) for h in headers]]
    
    for item in items:
        row = []
        for key in keys:
            val = item.get(key, "")
            if isinstance(val, datetime):
                val = val.strftime('%Y-%m-%d %H:%M')
            elif val is None:
                val = "-"
            row.append(Paragraph(str(val), body_style))
        table_content.append(row)
        
    # Standard column split
    col_width = 532.0 / len(headers)
    data_table = Table(table_content, colWidths=[col_width] * len(headers))
    data_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2D5A27")),  # Forest green header
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAF9F6")]),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#E7E5E4")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E7E5E4")),
    ]))
    story.append(data_table)
    
    # Build Document
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
