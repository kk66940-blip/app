import streamlit as st
from utils.supabase_client import get_supabase
from datetime import datetime
from collections import defaultdict

supabase = get_supabase()
project_id = st.session_state.get("current_project_id")
project_name = st.session_state.get("selected_project_name", "Proyek")

st.header("📝 SPK - Surat Perintah Kerja")
st.subheader(f"Proyek: {project_name}")

if not project_id:
    st.warning("Pilih proyek di sidebar terlebih dahulu")
    st.stop()

# ==================== TABS ====================
tab1, tab2 = st.tabs(["➕ Buat SPK Baru", "📋 Daftar SPK"])

# ==================== TAB 1: BUAT SPK BARU ====================
with tab1:
    st.subheader("Buat SPK Baru")

    with st.form("form_spk", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            spk_date = st.date_input("Tanggal SPK", datetime.now().date())
            recipient_name = st.text_input("Nama Penerima SPK *")
            recipient_contact = st.text_input("Kontak Penerima (HP/Email)")
        
        with col2:
            deadline_date = st.date_input("Tenggat Waktu Pelaksanaan *")
            special_terms = st.text_area("Syarat & Ketentuan Khusus")
            notes = st.text_area("Catatan Tambahan")

        st.divider()
        st.markdown("**Pilih Item RAP yang akan dimasukkan ke SPK**")

        # Ambil data RAP
        rap_items = supabase.table("rap_items") \
            .select("id, code, description, execution_price, unit") \
            .eq("project_id", project_id) \
            .execute().data

        if rap_items:
            rap_options = {
                f"{item['code']} - {item['description'][:60]} (Rp {item['execution_price']:,.0f})": item['id']
                for item in rap_items
            }

            selected_rap_labels = st.multiselect(
                "Pilih Item RAP (bisa lebih dari satu)",
                options=list(rap_options.keys()),
                key="rap_select"
            )
        else:
            st.warning("Belum ada data RAP untuk proyek ini.")
            selected_rap_labels = []

        submitted = st.form_submit_button("💾 Simpan SPK", type="primary", use_container_width=True)

        if submitted:
            if not recipient_name or not deadline_date:
                st.error("Nama Penerima dan Tenggat Waktu wajib diisi!")
            elif not selected_rap_labels:
                st.error("Pilih minimal satu item RAP!")
            else:
                try:
                    # Generate nomor SPK sederhana
                    today_str = datetime.now().strftime("%y%m%d")
                    last_spk = supabase.table("spk") \
                        .select("spk_no") \
                        .eq("project_id", project_id) \
                        .order("id", desc=True) \
                        .limit(1).execute().data
                    
                    next_no = 1
                    if last_spk:
                        try:
                            last_num = int(last_spk[0]["spk_no"].split("-")[-1])
                            next_no = last_num + 1
                        except:
                            pass
                    
                    spk_no = f"SPK-{today_str}-{str(next_no).zfill(3)}"

                    # Simpan ke tabel spk
                    spk_data = {
                        "project_id": project_id,
                        "spk_no": spk_no,
                        "spk_date": str(spk_date),
                        "recipient_name": recipient_name,
                        "recipient_contact": recipient_contact,
                        "deadline_date": str(deadline_date),
                        "special_terms": special_terms,
                        "status": "In Progress",   # Langsung In Progress
                        "created_by": st.session_state.user.get("username", "admin"),
                        "approved_by": st.session_state.user.get("username", "admin"),
                        "approved_at": datetime.now().isoformat(),
                        "notes": notes
                    }
                    
                    spk_res = supabase.table("spk").insert(spk_data).execute()
                    new_spk_id = spk_res.data[0]["id"]

                    # Simpan item RAP ke spk_rap_items
                    for label in selected_rap_labels:
                        rap_id = rap_options[label]
                        rap_item = next((r for r in rap_items if r["id"] == rap_id), None)
                        
                        if rap_item:
                            supabase.table("spk_rap_items").insert({
                                "spk_id": new_spk_id,
                                "rap_item_id": rap_id,
                                "volume_target": rap_item.get("volume", 0),
                                "unit_price": rap_item.get("execution_price", 0),
                                "total_value": (rap_item.get("volume", 0) or 0) * (rap_item.get("execution_price", 0) or 0),
                                "description": rap_item.get("description", ""),
                                "unit": rap_item.get("unit", "")
                            }).execute()

                    st.success(f"✅ SPK berhasil dibuat! Nomor: **{spk_no}**")
                    st.balloons()
                    st.rerun()

                except Exception as e:
                    st.error(f"Gagal menyimpan SPK: {str(e)}")

# ==================== TAB 2: DAFTAR SPK ====================
with tab2:
    st.subheader("Daftar Semua SPK")

    spk_list = supabase.table("spk") \
        .select("*") \
        .eq("project_id", project_id) \
        .order("created_at", desc=True) \
        .execute().data

    if spk_list:
        for spk in spk_list:
            with st.expander(f"**{spk['spk_no']}** | {spk['recipient_name']} | Status: {spk['status']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Tanggal:** {spk['spk_date']}")
                    st.write(f"**Tenggat:** {spk['deadline_date']}")
                    st.write(f"**Penerima:** {spk['recipient_name']}")
                    if spk.get("recipient_contact"):
                        st.write(f"**Kontak:** {spk['recipient_contact']}")
                with col2:
                    st.write(f"**Status:** {spk['status']}")
                    st.write(f"**Dibuat oleh:** {spk.get('created_by', '-')}")
                    if spk.get("approved_by"):
                        st.write(f"**Disetujui oleh:** {spk['approved_by']}")

                if spk.get("special_terms"):
                    st.write(f"**Syarat Khusus:** {spk['special_terms']}")
                if spk.get("notes"):
                    st.write(f"**Catatan:** {spk['notes']}")

                # Tombol aksi
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("🔄 Ubah Status", key=f"status_{spk['id']}"):
                        new
