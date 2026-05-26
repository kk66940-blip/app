import streamlit as st
from utils.supabase_client import get_supabase
from datetime import datetime
from collections import defaultdict
import uuid

supabase = get_supabase()
project_id = st.session_state.get("current_project_id")
project_name = st.session_state.get("selected_project_name", "Proyek")

st.header("💰 Pengeluaran Proyek")
st.subheader(f"Proyek: {project_name}")

if not project_id:
    st.warning("Pilih proyek di sidebar terlebih dahulu.")
    st.stop()

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
        uploaded_file = st.file_uploader("Pilih file gambar", type=["jpg", "png", "jpeg"], key="add_expense_photo")

        if st.form_submit_button("💾 Simpan Pengeluaran", type="primary", use_container_width=True):
            if amount <= 0:
                st.error("Jumlah pengeluaran harus lebih dari 0.")
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

# ==================== RINGKASAN PENGELUARAN ====================
st.subheader("📊 Ringkasan Pengeluaran")

expenses = supabase.table("project_expenses") \
    .select("*") \
    .eq("project_id", project_id) \
    .order("expense_date", desc=True) \
    .execute().data

if not expenses:
    st.info("Belum ada data pengeluaran.")
else:
    total_all = sum(item.get("amount", 0) for item in expenses)
    st.metric("Total Pengeluaran", f"Rp {total_all:,.0f}")

    # Ringkasan per kategori
    category_summary = defaultdict(float)
    for item in expenses:
        category_summary[item["category"]] += item.get("amount", 0)

    cols = st.columns(len(category_summary))
    for idx, (cat, total) in enumerate(category_summary.items()):
        with cols[idx]:
            st.metric(cat, f"Rp {total:,.0f}")

st.divider()

# ==================== DAFTAR PENGELUARAN + EDIT & HAPUS ====================
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

            # Tombol Aksi
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("✏️ Edit", key=f"edit_{exp['id']}", use_container_width=True):
                    st.session_state.edit_expense = exp
                    st.rerun()
            with btn_col2:
                if st.button("🗑️ Hapus", key=f"delete_{exp['id']}", use_container_width=True):
                    if st.session_state.get(f"confirm_delete_{exp['id']}", False):
                        try:
                            supabase.table("project_expenses").delete().eq("id", exp['id']).execute()
                            st.success("Pengeluaran berhasil dihapus!")
                            if f"confirm_delete_{exp['id']}" in st.session_state:
                                del st.session_state[f"confirm_delete_{exp['id']}"]
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal menghapus: {e}")
                    else:
                        st.session_state[f"confirm_delete_{exp['id']}"] = True
                        st.warning("Klik lagi untuk konfirmasi hapus")
                        st.rerun()

# ==================== FORM EDIT ====================
if "edit_expense" in st.session_state:
    exp = st.session_state.edit_expense
    st.subheader(f"✏️ Edit Pengeluaran")

    with st.form("form_edit_expense"):
        col1, col2 = st.columns(2)
        with col1:
            new_date = st.date_input("Tanggal", datetime.strptime(exp['expense_date'], "%Y-%m-%d").date())
            new_amount = st.number_input(
                "Jumlah (Rp)", 
                value=float(exp.get('amount', 0)), 
                step=10000.0,           # ← Diubah menjadi float
                format="%.0f"
            )
        with col2:
            new_paid_by = st.text_input("Dibayar Oleh", value=exp.get('paid_by', ''))

        new_description = st.text_area("Uraian", value=exp.get('description', ''))
        new_notes = st.text_input("Catatan", value=exp.get('notes', ''))

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.form_submit_button("💾 Simpan Perubahan", type="primary", use_container_width=True):
                try:
                    supabase.table("project_expenses").update({
                        "expense_date": str(new_date),
                        "amount": new_amount,
                        "paid_by": new_paid_by,
                        "description": new_description,
                        "notes": new_notes
                    }).eq("id", exp['id']).execute()

                    st.success("✅ Pengeluaran berhasil diperbarui!")
                    del st.session_state.edit_expense
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal memperbarui: {e}")

        with col_btn2:
            if st.form_submit_button("Batal", use_container_width=True):
                del st.session_state.edit_expense
                st.rerun()
