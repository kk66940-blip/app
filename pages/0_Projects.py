import streamlit as st
from utils.supabase_client import get_supabase
from datetime import datetime
from utils.helpers import format_rupiah

supabase = get_supabase()


st.header("🏗️ Manajemen Proyek")

# ==================== TAMBAH PROYEK BARU ====================
with st.expander("➕ Tambah Proyek Baru", expanded=False):
    with st.form("add_project_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Nama Proyek *")
            client = st.text_input("Pemberi Tugas / Client")
            location = st.text_input("Lokasi Proyek")
        with col2:
            start_date = st.date_input("Tanggal Mulai", datetime.now().date())
            contract_value = st.number_input("Nilai Kontrak (Rp)", value=0, step=1000000, format="%d")   # ← Sudah diperbaiki
            ppn_rate = st.number_input("PPN (%)", value=11.0, step=0.1)
            retensi_rate = st.number_input("Retensi (%)", value=5.0, step=0.1)

        if st.form_submit_button("💾 Simpan Proyek Baru", type="primary", use_container_width=True):
            if not name:
                st.error("Nama proyek harus diisi!")
            else:
                data = {
                    "name": name,
                    "client": client,
                    "location": location,
                    "start_date": str(start_date),
                    "contract_value": contract_value,
                    "ppn_rate": ppn_rate,
                    "retensi_rate": retensi_rate,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                supabase.table("projects").insert(data).execute()
                st.success("✅ Proyek baru berhasil ditambahkan!")
                st.rerun()

st.divider()

# ==================== DAFTAR PROYEK ====================
st.subheader("📋 Daftar Proyek")

projects = supabase.table("projects").select("*").order("created_at", desc=True).execute().data

if projects:
    # Header tabel
    header_cols = st.columns([4, 2.5, 3.5])
    with header_cols[0]:
        st.markdown("**Nama Proyek / Client**")
    with header_cols[1]:
        st.markdown("**Nilai Kontrak**")
    with header_cols[2]:
        st.markdown("**Aksi**")
    
    st.markdown("---")

    for proj in projects:
        is_active = proj['id'] == st.session_state.get("current_project_id")
        
        cols = st.columns([4, 2.5, 3.5])
        
        # Kolom 1: Nama + Client + Status
        with cols[0]:
            status_badge = "🟢 **Aktif**" if is_active else ""
            st.markdown(f"**{proj['name']}** {status_badge}")
            client_loc = f"{proj.get('client', '')} | {proj.get('location', '')}".strip(" | ")
            if client_loc:
                st.caption(client_loc)
        
        # Kolom 2: Nilai Kontrak
        with cols[1]:
            nilai = proj.get('contract_value', 0)
            st.markdown(f"**{format_rupiah(nilai)}**")
            st.caption(f"PPN {proj.get('ppn_rate', 11)}% • Retensi {proj.get('retensi_rate', 5)}%")
        
        # Kolom 3: Tombol Aksi (horizontal)
        with cols[2]:
            btn_cols = st.columns(3)
            
            with btn_cols[0]:
                if st.button("Pilih", key=f"pilih_{proj['id']}", use_container_width=True):
                    st.session_state.current_project_id = proj['id']
                    st.session_state.selected_project_name = proj['name']
                    st.success(f"✅ Proyek **{proj['name']}** diaktifkan!")
                    st.rerun()
            
            with btn_cols[1]:
                if st.button("✏️", key=f"edit_{proj['id']}", use_container_width=True, help="Edit"):
                    st.session_state.edit_project = proj
                    st.rerun()
            
            with btn_cols[2]:
                if st.button("🗑️", key=f"hapus_{proj['id']}", use_container_width=True, help="Hapus"):
                    if is_active:
                        st.error("❌ Tidak bisa menghapus proyek yang sedang aktif!")
                    else:
                        if st.session_state.get(f"confirm_delete_{proj['id']}", False):
                            supabase.table("projects").delete().eq("id", proj['id']).execute()
                            st.success(f"Proyek **{proj['name']}** berhasil dihapus!")
                            if f"confirm_delete_{proj['id']}" in st.session_state:
                                del st.session_state[f"confirm_delete_{proj['id']}"]
                            st.rerun()
                        else:
                            st.session_state[f"confirm_delete_{proj['id']}"] = True
                            st.warning("⚠️ Klik lagi untuk konfirmasi hapus")
                            st.rerun()

        st.markdown("---")

else:
    st.info("📭 Belum ada proyek. Silakan tambahkan proyek baru di atas.")

# ==================== EDIT PROYEK ====================
if "edit_project" in st.session_state:
    p = st.session_state.edit_project
    
    with st.expander(f"✏️ Edit Proyek: {p['name']}", expanded=True):
        with st.form("edit_project_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input("Nama Proyek *", value=p.get('name', ''))
                new_client = st.text_input("Pemberi Tugas / Client", value=p.get('client', ''))
                new_location = st.text_input("Lokasi Proyek", value=p.get('location', ''))
            with col2:
                new_start = st.date_input("Tanggal Mulai", 
                                         value=datetime.strptime(p.get('start_date', '2026-01-01'), "%Y-%m-%d").date() 
                                         if p.get('start_date') else datetime.now().date())
                new_contract = st.number_input("Nilai Kontrak (Rp)", 
                                               value=float(p.get('contract_value', 0)), 
                                               step=1000000, format="%d")   # ← Sudah diperbaiki
                new_ppn = st.number_input("PPN (%)", value=float(p.get('ppn_rate', 11.0)), step=0.1)
                new_retensi = st.number_input("Retensi (%)", value=float(p.get('retensi_rate', 5.0)), step=0.1)

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.form_submit_button("💾 Simpan Perubahan", type="primary", use_container_width=True):
                    if not new_name:
                        st.error("Nama proyek harus diisi!")
                    else:
                        data = {
                            "name": new_name,
                            "client": new_client,
                            "location": new_location,
                            "start_date": str(new_start),
                            "contract_value": new_contract,
                            "ppn_rate": new_ppn,
                            "retensi_rate": new_retensi,
                            "updated_at": datetime.now().isoformat()
                        }
                        supabase.table("projects").update(data).eq("id", p['id']).execute()
                        st.success("✅ Proyek berhasil diperbarui!")
                        del st.session_state.edit_project
                        st.rerun()
            
            with col_btn2:
                if st.form_submit_button("Batal", use_container_width=True):
                    del st.session_state.edit_project
                    st.rerun()