def export_expenses_to_excel(expenses, project_name):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Laporan Pengeluaran"

    # Styling
    header_fill = PatternFill(start_color="0d6efd", end_color="0d6efd", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    category_fill = PatternFill(start_color="28a745", end_color="28a745", fill_type="solid")
    category_font = Font(bold=True, color="FFFFFF", size=11)
    subtotal_fill = PatternFill(start_color="fff3cd", end_color="fff3cd", fill_type="solid")
    total_fill = PatternFill(start_color="d4edda", end_color="d4edda", fill_type="solid")
    title_font = Font(bold=True, size=14, color="0d6efd")
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    # Judul
    ws.merge_cells('A1:F1')
    ws['A1'] = f"LAPORAN PENGELUARAN PROYEK - {project_name}"
    ws['A1'].font = title_font
    ws['A1'].alignment = Alignment(horizontal='center')

    ws.merge_cells('A2:F2')
    ws['A2'] = f"Tanggal Export: {datetime.now().strftime('%d %B %Y')}"
    ws['A2'].font = Font(italic=True, size=10)

    # Header
    headers = ["No", "Tanggal", "Kategori", "Uraian", "Dibayar Oleh", "Jumlah (Rp)"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        cell.border = thin_border

    # Grouping berdasarkan Kategori
    from collections import defaultdict
    grouped = defaultdict(list)
    for exp in expenses:
        grouped[exp['category']].append(exp)

    current_row = 5
    item_no = 1
    grand_total = 0

    for category, items in grouped.items():
        # Header Kategori
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=6)
        cell = ws.cell(row=current_row, column=1, value=f"▶ {category}")
        cell.font = category_font
        cell.fill = category_fill
        for col in range(1, 7):
            ws.cell(row=current_row, column=col).fill = category_fill
            ws.cell(row=current_row, column=col).border = thin_border
        current_row += 1

        category_total = 0

        # Isi data per kategori
        for exp in items:
            ws.cell(row=current_row, column=1, value=item_no).border = thin_border
            ws.cell(row=current_row, column=2, value=exp['expense_date']).border = thin_border
            ws.cell(row=current_row, column=3, value=exp['category']).border = thin_border
            ws.cell(row=current_row, column=4, value=exp.get('description', '')).border = thin_border
            ws.cell(row=current_row, column=5, value=exp.get('paid_by', '')).border = thin_border
            ws.cell(row=current_row, column=6, value=exp.get('amount', 0)).border = thin_border
            ws.cell(row=current_row, column=6).number_format = '#,##0'

            category_total += exp.get('amount', 0)
            grand_total += exp.get('amount', 0)
            item_no += 1
            current_row += 1

        # Subtotal per Kategori
        ws.cell(row=current_row, column=5, value="SUBTOTAL").font = Font(bold=True)
        ws.cell(row=current_row, column=5).fill = subtotal_fill
        ws.cell(row=current_row, column=6, value=category_total).font = Font(bold=True)
        ws.cell(row=current_row, column=6).fill = subtotal_fill
        ws.cell(row=current_row, column=6).number_format = '#,##0'
        for col in range(1, 7):
            ws.cell(row=current_row, column=col).border = thin_border
            ws.cell(row=current_row, column=col).fill = subtotal_fill
        current_row += 1

    # Grand Total
    current_row += 1
    ws.merge_cells(start_row=current_row, start_column=5, end_row=current_row, end_column=5)
    ws.cell(row=current_row, column=5, value="GRAND TOTAL").font = Font(bold=True, size=11)
    ws.cell(row=current_row, column=5).fill = total_fill
    ws.cell(row=current_row, column=5).alignment = Alignment(horizontal='right')

    ws.cell(row=current_row, column=6, value=grand_total).font = Font(bold=True, size=11)
    ws.cell(row=current_row, column=6).fill = total_fill
    ws.cell(row=current_row, column=6).number_format = '#,##0'

    for col in range(5, 7):
        ws.cell(row=current_row, column=col).border = thin_border
        ws.cell(row=current_row, column=col).fill = total_fill

    # Lebar Kolom
    ws.column_dimensions['A'].width = 6
    ws.column_dimensions['B'].width = 14
    ws.column_dimensions['C'].width = 22
    ws.column_dimensions['D'].width = 45
    ws.column_dimensions['E'].width = 20
    ws.column_dimensions['F'].width = 18

    # Simpan
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output
