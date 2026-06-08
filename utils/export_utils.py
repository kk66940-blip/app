"""
utils/export_utils.py
Versi yang sudah diperbaiki untuk mendukung hierarchy RAP
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


# ==================== STYLING ====================
HEADER_FILL = PatternFill(start_color="0d6efd", end_color="0d6efd", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
SECTION_FILL = PatternFill(start_color="28a745", end_color="28a745", fill_type="solid")
SECTION_FONT = Font(bold=True, color="FFFFFF", size=11)
SUBTOTAL_FILL = PatternFill(start_color="fff3cd", end_color="fff3cd", fill_type="solid")
SUBTOTAL_FONT = Font(bold=True, size=10)
GRAND_FILL = PatternFill(start_color="d4edda", end_color="d4edda", fill_type="solid")
GRAND_FONT = Font(bold=True, size=11)
THIN_BORDER = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))


def _build_children_map(items: List[Dict], id_key: str = "id", parent_key: str = "parent_id") -> Dict:
    children_map = defaultdict(list)
    for item in items:
        parent = item.get(parent_key)
        children_map[parent].append(item)
    
    for pid in children_map:
        children_map[pid] = sorted(children_map[pid], key=lambda x: (x.get('sort_order', 0), x.get(id_key, 0)))
    return children_map


def _get_root_items(items: List[Dict], id_key: str = "id", parent_key: str = "parent_id") -> List[Dict]:
    all_ids = {item.get(id_key) for item in items if item.get(id_key)}
    roots = [item for item in items if item.get(parent_key) is None or item.get(parent_key) not in all_ids]
    return sorted(roots, key=lambda x: (x.get('sort_order', 0), x.get(id_key, 0)))


# ==================== PDF EXPORT (DIPERBAIKI) ====================
def export_hierarchical_pdf(
    items: List[Dict],
    project_name: str,
    title: str = "RENCANA ANGGARAN PELAKSANAAN (RAP)",
    filename_prefix: str = "RAP",
    get_total_func: Optional[Callable[[Dict], float]] = None,
    id_key: str = "id",
    parent_key: str = "parent_id"
) -> BytesIO:
    if not items:
        raise ValueError("No data to export")

    children_map = _build_children_map(items, id_key=id_key, parent_key=parent_key)
    root_items = _get_root_items(items, id_key=id_key, parent_key=parent_key)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.2*cm, leftMargin=1.2*cm, topMargin=1.2*cm, bottomMargin=1.2*cm)

    styles = getSampleStyleSheet()
    normal = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=8, leading=10)

    elements = []
    elements.append(Paragraph(f"<b>{title}</b>", ParagraphStyle('Title', fontSize=14, fontName='Helvetica-Bold', textColor=colors.HexColor('#0d6efd'))))
    elements.append(Paragraph(f"<b>Proyek:</b> {project_name}", normal))
    elements.append(Paragraph(f"<b>Tanggal:</b> {datetime.now().strftime('%d %B %Y')}", normal))
    elements.append(Spacer(1, 0.3*cm))

    table_data = [["No", "Uraian Pekerjaan", "Sat", "Vol", "Harga (Rp)", "Jumlah (Rp)"]]
    header_row_indices, subtotal_row_indices = [], []
    grand_total = 0
    current_row = 1

    def add_to_pdf(node: Dict, path: List[int]) -> float:
        nonlocal grand_total, current_row
        node_id = node.get(id_key)
        children = children_map.get(node_id, [])
        has_children = len(children) > 0
        current_no = ".".join(map(str, path))

        if has_children:
            header_row_indices.append(current_row)
            table_data.append(["", Paragraph(f"▶ {node.get('description', '')}", 
                               ParagraphStyle('Header', fontSize=9, fontName='Helvetica-Bold', textColor=colors.white)), "", "", "", ""])
            current_row += 1

            sub_total = 0
            for idx, child in enumerate(children, 1):
                sub_total += add_to_pdf(child, path + [idx])
            
            subtotal_row_indices.append(current_row)
            table_data.append(["", Paragraph("<b>SUBTOTAL</b>", normal), "", "", "", Paragraph(f"<b>{sub_total:,.0f}</b>", normal)])
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
    table_data.append(["", Paragraph("<b>GRAND TOTAL</b>", normal), "", "", "", Paragraph(f"<b>{grand_total:,.0f}</b>", normal)])

    col_widths = [1.0*cm, 8.0*cm, 1.1*cm, 1.7*cm, 2.6*cm, 2.8*cm]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)

    style_commands = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('FONTSIZE', (0, 1), (-1, -1), 7.5),
        ('ALIGN', (3, 1), (5, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
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

    # Grand Total row
    grand_row = len(table_data) - 1
    style_commands.append(('BACKGROUND', (0, grand_row), (-1, grand_row), colors.HexColor('#d4edda')))
    style_commands.append(('FONTNAME', (0, grand_row), (-1, grand_row), 'Helvetica-Bold'))
    style_commands.append(('FONTSIZE', (0, grand_row), (-1, grand_row), 9))

    t.setStyle(TableStyle(style_commands))
    elements.append(t)

    doc.build(elements)
    buffer.seek(0)
    return buffer