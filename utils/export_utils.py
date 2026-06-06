"""
utils/export_utils.py
Centralized, reusable export utilities for RAB, RAP, Opname, etc.
Professional implementation with multi-level hierarchy support,
consistent styling, and both Excel & PDF output.
"""

from io import BytesIO
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any, Optional, Callable

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import cm


# ==================== STYLING CONSTANTS ====================
HEADER_FILL = PatternFill(start_color="0d6efd", end_color="0d6efd", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)

SECTION_FILL = PatternFill(start_color="28a745", end_color="28a745", fill_type="solid")
SECTION_FONT = Font(bold=True, color="FFFFFF", size=11)

SUBTOTAL_FILL = PatternFill(start_color="fff3cd", end_color="fff3cd", fill_type="solid")
SUBTOTAL_FONT = Font(bold=True, size=10)

GRAND_FILL = PatternFill(start_color="d4edda", end_color="d4edda", fill_type="solid")
GRAND_FONT = Font(bold=True, size=11)

THIN_BORDER = Border(
    left=Side(style='thin'), right=Side(style='thin'),
    top=Side(style='thin'), bottom=Side(style='thin')
)


def _build_children_map(items: List[Dict]) -> Dict[Optional[int], List[Dict]]:
    """Build parent_id -> children mapping and sort each level."""
    children_map: Dict[Optional[int], List[Dict]] = defaultdict(list)
    for item in items:
        children_map[item.get('parent_id')].append(item)
    
    for pid in children_map:
        children_map[pid] = sorted(
            children_map[pid], 
            key=lambda x: (x.get('sort_order', 0), x.get('id', 0))
        )
    return children_map


def _get_root_items(items: List[Dict]) -> List[Dict]:
    """Identify root items (no parent or parent not in dataset)."""
    all_ids = {item['id'] for item in items if item.get('id')}
    roots = [
        item for item in items 
        if item.get('parent_id') is None or item.get('parent_id') not in all_ids
    ]
    return sorted(roots, key=lambda x: (x.get('sort_order', 0), x.get('id', 0)))


# ==================== EXCEL EXPORT ====================
def export_hierarchical_excel(
    items: List[Dict],
    project_name: str,
    title: str = "RENCANA ANGGARAN BIAYA (RAB)",
    filename_prefix: str = "RAB",
    columns: Optional[List[str]] = None,
    value_columns: Optional[List[str]] = None,
    get_total_func: Optional[Callable[[Dict], float]] = None
) -> BytesIO:
    """
    Generic hierarchical Excel exporter.
    Supports Main → Sub → Sub-Sub structure with colored headers and subtotals.
    
    Args:
        items: Flat list of dicts with 'id', 'parent_id', 'level', 'sort_order', etc.
        project_name: Name of the project.
        title: Document title.
        filename_prefix: For download button naming.
        columns: Custom column headers (default: standard RAB columns).
        value_columns: Which fields to treat as monetary (for formatting).
        get_total_func: Custom function to calculate row total if needed.
    """
    if not items:
        raise ValueError("No data to export")

    children_map = _build_children_map(items)
    root_items = _get_root_items(items)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = filename_prefix[:31]  # Excel sheet name limit

    # Title
    ws.merge_cells('A1:F1')
    ws['A1'] = f"{title} - {project_name}"
    ws['A1'].font = Font(bold=True, size=14, color="0d6efd")
    ws['A1'].alignment = Alignment(horizontal='center')

    ws.merge_cells('A2:F2')
    ws['A2'] = f"Tanggal Export: {datetime.now().strftime('%d %B %Y')}"
    ws['A2'].font = Font(italic=True, size=10)

    # Headers
    default_headers = ["No", "Uraian Pekerjaan", "Satuan", "Volume", "Harga Satuan (Rp)", "Jumlah (Rp)"]
    headers = columns or default_headers
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal='center')
        cell.border = THIN_BORDER

    # Process tree
    row_num = 5
    grand_total = 0

    def process_node(node: Dict, path: List[int]) -> float:
        nonlocal row_num, grand_total
        node_id = node['id']
        children = children_map.get(node_id, [])
        has_children = len(children) > 0
        current_no = ".".join(map(str, path))

        if has_children:
            # Section Header (Green)
            ws.merge_cells(start_row=row_num, start_column=1, end_row=row_num, end_column=len(headers))
            cell = ws.cell(row=row_num, column=1, value=f"▶ {node.get('description', '')}")
            cell.font = SECTION_FONT
            cell.fill = SECTION_FILL
            for c in range(1, len(headers) + 1):
                ws.cell(row=row_num, column=c).border = THIN_BORDER
                ws.cell(row=row_num, column=c).fill = SECTION_FILL
            row_num += 1

            sub_total = 0
            for idx, child in enumerate(children, 1):
                sub_total += process_node(child, path + [idx])
            
            # Subtotal
            ws.cell(row=row_num, column=2, value="SUBTOTAL").font = SUBTOTAL_FONT
            ws.cell(row=row_num, column=len(headers), value=sub_total).font = SUBTOTAL_FONT
            ws.cell(row=row_num, column=len(headers)).number_format = '#,##0'
            for c in range(1, len(headers) + 1):
                ws.cell(row=row_num, column=c).border = THIN_BORDER
                ws.cell(row=row_num, column=c).fill = SUBTOTAL_FILL
            row_num += 1
            return sub_total
        else:
            # Leaf item
            vol = node.get('volume', 0) or 0
            price = node.get('unit_price', 0) or node.get('execution_price', 0) or 0
            total = get_total_func(node) if get_total_func else (vol * price)
            grand_total += total

            ws.cell(row=row_num, column=1, value=current_no).border = THIN_BORDER
            ws.cell(row=row_num, column=2, value=f"    {node.get('description', '')}").border = THIN_BORDER
            ws.cell(row=row_num, column=3, value=node.get('unit', '')).border = THIN_BORDER
            ws.cell(row=row_num, column=4, value=vol).border = THIN_BORDER
            ws.cell(row=row_num, column=5, value=price).border = THIN_BORDER
            ws.cell(row=row_num, column=6, value=total).border = THIN_BORDER

            ws.cell(row=row_num, column=4).number_format = '#,##0.00'
            ws.cell(row=row_num, column=5).number_format = '#,##0'
            ws.cell(row=row_num, column=6).number_format = '#,##0'

            row_num += 1
            return total

    for idx, root in enumerate(root_items, 1):
        process_node(root, [idx])

    # Grand Total
    row_num += 1
    ws.merge_cells(start_row=row_num, start_column=2, end_row=row_num, end_column=5)
    ws.cell(row=row_num, column=2, value="GRAND TOTAL").font = GRAND_FONT
    ws.cell(row=row_num, column=2).fill = GRAND_FILL
    ws.cell(row=row_num, column=2).alignment = Alignment(horizontal='right')

    ws.cell(row=row_num, column=6, value=grand_total).font = GRAND_FONT
    ws.cell(row=row_num, column=6).fill = GRAND_FILL
    ws.cell(row=row_num, column=6).number_format = '#,##0'
    for c in range(2, 7):
        ws.cell(row=row_num, column=c).border = THIN_BORDER
        ws.cell(row=row_num, column=c).fill = GRAND_FILL

    # Column widths (reasonable defaults)
    ws.column_dimensions['A'].width = 8
    ws.column_dimensions['B'].width = 55
    ws.column_dimensions['C'].width = 10
    ws.column_dimensions['D'].width = 12
    ws.column_dimensions['E'].width = 18
    ws.column_dimensions['F'].width = 18

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output


# ==================== PDF EXPORT (similar structure) ====================
def export_hierarchical_pdf(
    items: List[Dict],
    project_name: str,
    title: str = "RENCANA ANGGARAN BIAYA (RAB)",
    filename_prefix: str = "RAB",
    get_total_func: Optional[Callable[[Dict], float]] = None
) -> BytesIO:
    """Professional PDF export with hierarchy (matching Excel quality)."""
    if not items:
        raise ValueError("No data to export")

    children_map = _build_children_map(items)
    root_items = _get_root_items(items)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=1.2*cm, leftMargin=1.2*cm,
        topMargin=1.2*cm, bottomMargin=1.2*cm
    )

    styles = getSampleStyleSheet()
    normal = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=8, leading=10)
    title_style = ParagraphStyle('Title', parent=styles['Normal'], fontSize=14, 
                                  fontName='Helvetica-Bold', textColor=colors.HexColor('#0d6efd'))

    elements = []
    elements.append(Paragraph(title, title_style))
    elements.append(Paragraph(f"<b>Proyek:</b> {project_name}", normal))
    elements.append(Paragraph(f"<b>Tanggal:</b> {datetime.now().strftime('%d %B %Y')}", normal))
    elements.append(Spacer(1, 0.25*cm))

    table_data = [["No", "Uraian Pekerjaan", "Sat", "Vol", "Harga (Rp)", "Jumlah (Rp)"]]
    header_row_indices = []
    subtotal_row_indices = []
    grand_total_row_index = None
    grand_total = 0
    current_row = 1

    def add_to_pdf(node: Dict, path: List[int]) -> float:
        nonlocal grand_total, current_row
        node_id = node['id']
        children = children_map.get(node_id, [])
        has_children = len(children) > 0
        current_no = ".".join(map(str, path))

        if has_children:
            header_row_indices.append(current_row)
            table_data.append(["", Paragraph(f"▶ {node.get('description', '')}", 
                               ParagraphStyle('Header', parent=styles['Normal'], 
                                              fontSize=9, fontName='Helvetica-Bold', 
                                              textColor=colors.white)), "", "", "", ""])
            current_row += 1

            sub_total = 0
            for idx, child in enumerate(children, 1):
                sub_total += add_to_pdf(child, path + [idx])
            
            subtotal_row_indices.append(current_row)
            table_data.append([
                "", Paragraph("<b>SUBTOTAL</b>", normal), "", "", "", 
                Paragraph(f"<b>{sub_total:,.0f}</b>", normal)
            ])
            current_row += 1
            return sub_total
        else:
            vol = node.get('volume', 0) or 0
            price = node.get('unit_price', 0) or node.get('execution_price', 0) or 0
            total = get_total_func(node) if get_total_func else (vol * price)
            grand_total += total

            table_data.append([
                current_no,
                Paragraph(f"    {node.get('description', '')}", normal),
                node.get('unit', ''),
                f"{vol:,.2f}",
                f"{price:,.0f}",
                f"{total:,.0f}"
            ])
            current_row += 1
            return total

    for idx, root in enumerate(root_items, 1):
        add_to_pdf(root, [idx])

    # Grand Total
    grand_total_row_index = current_row
    table_data.append([
        "", Paragraph("<b>GRAND TOTAL</b>", normal), "", "", "", 
        Paragraph(f"<b>{grand_total:,.0f}</b>", normal)
    ])

    col_widths = [1.0*cm, 8.0*cm, 1.1*cm, 1.7*cm, 2.6*cm, 2.8*cm]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)

    style_commands = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('FONTSIZE', (0, 1), (-1, -1), 7.5),
        ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
        ('ALIGN', (4, 1), (5, -1), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]

    for row_idx in header_row_indices:
        style_commands.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor('#28a745')))
        style_commands.append(('TEXTCOLOR', (0, row_idx), (-1, row_idx), colors.white))
        style_commands.append(('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold'))

    for row_idx in subtotal_row_indices:
        style_commands.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor('#fff3cd')))
        style_commands.append(('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold'))

    if grand_total_row_index:
        style_commands.append(('BACKGROUND', (0, grand_total_row_index), (-1, grand_total_row_index), colors.HexColor('#d4edda')))
        style_commands.append(('FONTNAME', (0, grand_total_row_index), (-1, grand_total_row_index), 'Helvetica-Bold'))
        style_commands.append(('FONTSIZE', (0, grand_total_row_index), (-1, grand_total_row_index), 9))

    t.setStyle(TableStyle(style_commands))
    elements.append(t)

    doc.build(elements)
    buffer.seek(0)
    return buffer


# Convenience wrappers for common use cases
def export_rab_excel(items: List[Dict], project_name: str) -> BytesIO:
    return export_hierarchical_excel(items, project_name, 
                                     title="RENCANA ANGGARAN BIAYA (RAB)", 
                                     filename_prefix="RAB")

def export_rab_pdf(items: List[Dict], project_name: str) -> BytesIO:
    return export_hierarchical_pdf(items, project_name,
                                   title="RENCANA ANGGARAN BIAYA (RAB)",
                                   filename_prefix="RAB")


def export_rap_excel(items: List[Dict], project_name: str) -> BytesIO:
    """Example for RAP - can be extended with more columns if needed."""
    return export_hierarchical_excel(
        items, project_name,
        title="RENCANA ANGGARAN PELAKSANAAN (RAP)",
        filename_prefix="RAP"
    )