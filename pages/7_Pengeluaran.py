import streamlit as st
from utils.supabase_client import get_supabase
from datetime import datetime
from collections import defaultdict
from io import BytesIO
import uuid
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

supabase = get_supabase()
project_id = st.session_state.get("current_project_id")
project_name = st.session_state.get("selected_project_name", "Proyek")

st.header("💰 Pengeluaran Proyek")
st.subheader(f"Proyek: {project_name}")

if not project_id:
    st.warning("Pilih proyek di sidebar terlebih dahulu.")
    st.stop()

# ==================== EXPORT KE EXCEL ====================
def export_expenses_to_excel(expenses, project_name):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Laporan Pengeluaran"

    # Styling
    header_fill = PatternFill(start_color="0d6efd", end_color="0d6efd", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
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
    ws['A2'] = f"Tanggal Export: {datetime.now().strftime('%d %B %Y %H:%M')}"
    ws['A2'].font = Font(italic=True, size=10)

    # Header
    headers = ["No", "Tanggal", "Kategori", "Uraian", "Dibayar Oleh", "Jumlah (Rp)"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        cell.border = thin_border

    # Isi Data
    for idx, exp in enumerate(expenses, 1):
        row = idx + 4
        ws.cell(row=row, column=1, value=idx).border = thin_border
        ws.cell(row=row, column=2, value=exp['expense_date']).border = thin_border
        ws.cell(row=row, column=3, value=exp['category']).border = thin_border
        ws.cell(row=row, column=4, value=exp.get('description', '')).border = thin_border
        ws.cell(row=row, column=5, value=exp.get('paid_by', '')).border = thin_border
        ws.cell(row=row, column=6, value=exp.get('amount', 0)).border = thin_border
        ws.cell(row=row, column=6).number_format = '#,##0'

    # Total
    total_row = len(expenses) + 5
    ws.cell(row=total_row, column=5, value="TOTAL").font = Font(bold=True)
    ws.cell(row=total_row, column=6, value=sum(e.get('amount', 0) for e in expenses)).font = Font(bold=True)
    ws.cell(row=total_row, column=6).number_format = '#,##0'

    # Lebar Kolom
    ws.column_dimensions['A'].width = 6
    ws.column_dimensions['B'].width = 14
    ws.column_dimensions['C'].width = 22
    ws.column_dimensions['D'].width = 40
    ws.column_dimensions['E'].width = 20
    ws.column_dimensions['F'].width = 18

    # Simpan ke BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output

# ==================== TOMBOL EXPORT ====================
expenses = supabase.table("project_expenses") \
    .select("*") \
    .eq("project_id", project_id) \
    .order("expense_date", desc=True) \
    .execute().data

col1, col2 = st.columns([3, 1])
with col1:
    st.write("")
with col2:
    if expenses:
        if st.button("📊 Export ke Excel", type="primary", use_container_width=True):
            excel_file = export_expenses_to_excel(expenses, project_name)
            filename = f"Pengeluaran_{project_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx"
            st.download_button(
                label="⬇️ Download Excel",
                data=excel_file,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

st.divider()

# ==================== FORM TAMBAH PENGELUARAN ====================
with st.expander("➕ Tambah Pengeluaran Baru", expanded=False):
    with st.form("form_add_expense", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            expense_date = st.date_input("Tanggal Pengeluaran", datetime.now().date())
            category = st.selectbox(
                "Kategori Pengeluaran *",
                ["Material", "Upah / Tenaga Kerja", "Sewa Alat", "BBM / Transportasi", "Lain-lain"]
            )
            other_category = ""
            if category == "Lain-lain":
                other_category = st.text_input("Isi Kategori Lainnya *")

        with col2:
            amount = st.number_input("Jumlah Pengeluaran (Rp) *", min_value=0, step=10000, format="%d")
            paid_by = st.text_input("Dibayar Oleh (Nama Orang/Tim)")

        description = st.text_area("Uraian / Keterangan Pengeluaran")
        notes = st.text_input("Catatan Tambahan (Opsional)")

        st.markdown("**📸 Upload Bukti Pengeluaran**")
        uploaded_file = st.file_uploader("Pilih file gambar", type=["jpg", "png", "jpeg"], key="add_photo")

        if st.form_submit_button("💾 Simpan Pengeluaran", type="primary", use_container_width=True):
            if amount <= 0:
                st.error("Jumlah harus lebih dari 0.")
            elif category == "Lain-lain" and not other_category:
                st.error("Mohon isi kategori lainnya.")
            else:
                try:
                    final_category = other_category if category == "Lain-lain" else category
                    data = {
                        "project_id": project_id,
                        "expense_date": str(expense_date),
                        "category": final_category,
                        "description": description,
                        "amount": amount,
                        "paid_by": paid_by,
                        "notes": notes,
                        "created_by": st.session_state.user.get("username", "unknown")
                    }

                    if uploaded_file:
                        file_ext = uploaded_file.name.split(".")[-1].lower()
                        unique_filename = f"{uuid.uuid4()}.{file_ext}"
                        file_path = f"expenses/{project_id}/{unique_filename}"
                        supabase.storage.from_("opname-photos").upload(
                            path=file_path, file=uploaded_file.getvalue(),
                            file_options={"content-type": uploaded_file.type}
                        )
                        data["receipt_photo_url"] = supabase.storage.from_("opname-photos").get_public_url(file_path)

                    supabase.table("project_expenses").insert(data).execute()
                    st.success("✅ Pengeluaran berhasil disimpan!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal menyimpan: {str(e)}")

st.divider()

# ==================== RINGKASAN & DAFTAR ====================
st.subheader("📊 Ringkasan Pengeluaran")

if not expenses:
    st.info("Belum ada data pengeluaran.")
else:
    total_all = sum(item.get("amount", 0) for item in expenses)
    st.metric("Total Pengeluaran", f"Rp {total_all:,.0f}")

    category_summary = defaultdict(float)
    for item in expenses:
        category_summary[item["category"]] += item.get("amount", 0)

    cols = st.columns(len(category_summary))
    for idx, (cat, total) in enumerate(category_summary.items()):
        with cols[idx]:
            st.metric(cat, f"Rp {total:,.0f}")

st.divider()

st.subheader("📋 Daftar Pengeluaran")

if expenses:
    for exp in expenses:
        with st.expander(f"{exp['expense_date']} | {exp['category']} | Rp {exp['amount']:,.0f}"):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write(f"**Uraian:** {exp.get('description') or '-'}")
                st.write(f"**Dibayar Oleh:** {exp.get('paid_by') or '-'}")
                if exp.get('notes'):
                    st.write(f"**Catatan:** {exp.get('notes')}")
                st.caption(f"Diinput oleh: **{exp.get('created_by', '-')}**")
            with col2:
                if exp.get("receipt_photo_url"):
                    st.image(exp["receipt_photo_url"], width=200, caption="Bukti")

            # Edit & Hapus
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("✏️ Edit", key=f"edit_{exp['id']}", use_container_width=True):
                    st.session_state.edit_expense = exp
                    st.rerun()
            with btn_col2:
                if st.button("🗑️ Hapus", key=f"delete_{exp['id']}", use_container_width=True):
                    if st.session_state.get(f"confirm_delete_{exp['id']}", False):
                        supabase.table("project_expenses").delete().eq("id", exp['id']).execute()
                        st.success("Berhasil dihapus!")
                        st.rerun()
                    else:
                        st.session_state[f"confirm_delete_{exp['id']}"] = True
                        st.warning("Klik lagi untuk konfirmasi")
                        st.rerun()

# Form Edit
if "edit_expense" in st.session_state:
    exp = st.session_state.edit_expense
    st.subheader("✏️ Edit Pengeluaran")

    with st.form("form_edit_expense"):
        col1, col2 = st.columns(2)
        with col1:
            new_date = st.date_input("Tanggal", datetime.strptime(exp['expense_date'], "%Y-%m-%d").date())
            new_amount = st.number_input("Jumlah (Rp)", value=float(exp.get('amount', 0)), step=10000.0, format="%.0f")
        with col2:
            new_paid_by = st.text_input("Dibayar Oleh", value=exp.get('paid_by', ''))
        
        new_description = st.text_area("Uraian", value=exp.get('description', ''))
        new_notes = st.text_input("Catatan", value=exp.get('notes', ''))

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.form_submit_button("💾 Simpan Perubahan", type="primary", use_container_width=True):
                supabase.table("project_expenses").update({
                    "expense_date": str(new_date),
                    "amount": new_amount,
                    "paid_by": new_paid_by,
                    "description": new_description,
                    "notes": new_notes
                }).eq("id", exp['id']).execute()
                st.success("Berhasil diperbarui!")
                del st.session_state.edit_expense
                st.rerun()
        with col_btn2:
            if st.form_submit_button("Batal", use_container_width=True):
                del st.session_state.edit_expense
                st.rerun()
