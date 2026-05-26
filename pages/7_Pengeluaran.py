import streamlit as st
from utils.supabase_client import get_supabase
from datetime import datetime
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
with st.expander("➕ Tambah Pengeluaran Baru", expanded=True):
    with st.form("form_add_expense", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            expense_date = st.date_input("Tanggal Pengeluaran", datetime.now().date())
            category = st.selectbox(
                "Kategori Pengeluaran",
                ["Material", "Upah / Tenaga Kerja", "Sewa Alat", "BBM / Transportasi", "Lain-lain"]
            )
            
            # Jika pilih Lain-lain, munculkan textbox
            other_category = ""
            if category == "Lain-lain":
                other_category = st.text_input("Kategori Lainnya (Isi Manual)")

        with col2:
            amount = st.number_input("Jumlah Pengeluaran (Rp)", min_value=0, step=10000, format="%d")
            paid_by = st.text_input("Dibayar Oleh (Nama Orang/Tim)")
        
        description = st.text_area("Uraian / Keterangan Pengeluaran")
        notes = st.text_input("Catatan Tambahan (Opsional)")

        # Upload Bukti
        st.markdown("**📸 Upload Bukti Pengeluaran (Nota/Foto)**")
        uploaded_file = st.file_uploader(
            "Pilih file gambar (jpg, png, jpeg)", 
            type=["jpg", "png", "jpeg"],
            key="expense_receipt"
        )

        submitted = st.form_submit_button("💾 Simpan Pengeluaran", type="primary", use_container_width=True)

        if submitted:
            if amount <= 0:
                st.error("Jumlah pengeluaran harus lebih dari 0.")
            else:
                try:
                    # Tentukan kategori final
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

                    # Upload foto jika ada
                    if uploaded_file:
                        file_ext = uploaded_file.name.split(".")[-1].lower()
                        unique_filename = f"{uuid.uuid4()}.{file_ext}"
                        file_path = f"expenses/{project_id}/{unique_filename}"

                        supabase.storage.from_("opname-photos").upload(
                            path=file_path,
                            file=uploaded_file.getvalue(),
                            file_options={"content-type": uploaded_file.type}
                        )
                        public_url = supabase.storage.from_("opname-photos").get_public_url(file_path)
                        data["receipt_photo_url"] = public_url

                    # Insert ke database
                    supabase.table("project_expenses").insert(data).execute()
                    st.success("✅ Pengeluaran berhasil disimpan!")
                    st.rerun()

                except Exception as e:
                    st.error(f"Gagal menyimpan: {str(e)}")

st.divider()

# ==================== DAFTAR PENGELUARAN ====================
st.subheader("📋 Daftar Pengeluaran")

expenses = supabase.table("project_expenses")\
    .select("*")\
    .eq("project_id", project_id)\
    .order("expense_date", desc=True)\
    .execute().data

if not expenses:
    st.info("Belum ada data pengeluaran untuk proyek ini.")
else:
    # Ringkasan Total
    total_expense = sum(item.get("amount", 0) for item in expenses)
    st.metric("Total Pengeluaran Saat Ini", f"Rp {total_expense:,.0f}")

    st.divider()

    for exp in expenses:
        with st.expander(f"{exp['expense_date']} | {exp['category']} | Rp {exp['amount']:,.0f}"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**Uraian:** {exp.get('description', '-')}")
                st.write(f"**Dibayar Oleh:** {exp.get('paid_by', '-')}")
                if exp.get('notes'):
                    st.write(f"**Catatan:** {exp.get('notes')}")
                st.caption(f"Diinput oleh: {exp.get('created_by', '-')}")

            with col2:
                if exp.get("receipt_photo_url"):
                    st.image(exp["receipt_photo_url"], width=200, caption="Bukti Pengeluaran")
                else:
                    st.caption("Tidak ada bukti foto")

st.caption(f"Update: {datetime.now().strftime('%d %B %Y %H:%M')}")
