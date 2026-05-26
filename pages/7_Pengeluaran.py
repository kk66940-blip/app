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

        st.markdown("**📸 Upload Bukti Pengeluaran (Nota/Foto)**")
        uploaded_file = st.file_uploader("Pilih file gambar", type=["jpg", "png", "jpeg"], key="expense_upload")

        submitted = st.form_submit_button("💾 Simpan Pengeluaran", type="primary", use_container_width=True)

        if submitted:
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

                    # Upload foto bukti
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

                    supabase.table("project_expenses").insert(data).execute()
                    st.success("✅ Pengeluaran berhasil disimpan!")
                    st.rerun()

                except Exception as e:
                    st.error(f"Gagal menyimpan: {str(e)}")

st.divider()

# ==================== RINGKASAN & DAFTAR PENGELUARAN ====================
st.subheader("📊 Ringkasan Pengeluaran")

expenses = supabase.table("project_expenses") \
    .select("*") \
    .eq("project_id", project_id) \
    .order("expense_date", desc=True) \
    .execute().data

if not expenses:
    st.info("Belum ada data pengeluaran untuk proyek ini.")
else:
    # Hitung total keseluruhan
    total_all = sum(item.get("amount", 0) for item in expenses)
    st.metric("Total Pengeluaran", f"Rp {total_all:,.0f}")

    # Ringkasan per kategori
    category_summary = defaultdict(float)
    for item in expenses:
        category_summary[item["category"]] += item.get("amount", 0)

    st.markdown("**Ringkasan per Kategori:**")
    cols = st.columns(len(category_summary))
    for idx, (cat, total) in enumerate(category_summary.items()):
        with cols[idx]:
            st.metric(cat, f"Rp {total:,.0f}")

    st.divider()

    # Daftar Pengeluaran
    st.subheader("📋 Daftar Pengeluaran")

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
                    st.image(exp["receipt_photo_url"], width=220, caption="Bukti Pengeluaran")
                else:
                    st.caption("Tidak ada bukti foto")

st.caption(f"Update terakhir: {datetime.now().strftime('%d %B %Y %H:%M')}")
