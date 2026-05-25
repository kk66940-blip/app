import streamlit as st
from utils.supabase_client import get_supabase
from utils.helpers import format_rupiah
from datetime import datetime
from collections import defaultdict

supabase = get_supabase()
project_id = st.session_state.get("current_project_id")

st.header("📋 RAB - Rencana Anggaran Biaya")

if not project_id:
    st.warning("Pilih proyek terlebih dahulu di sidebar")
    st.stop()

# ==================== AMBIL DATA ====================
all_rab_items = supabase.table("rab_items")\
    .select("*")\
    .eq("project_id", project_id)\
    .order("level").order("sort_order").execute().data

# ==================== TRUE LIVE SEARCH ====================
st.markdown("### 🔍 Live Search (Update Langsung Saat Mengetik)")

search_term = st.text_input(
    "Ketik untuk mencari...",
    placeholder="Contoh: hebel, rangka, pasangan, A.1...",
    key="rab_live_search"
)

# === FORCE LIVE UPDATE (menggunakan st.rerun) ===
if "previous_search" not in st.session_state:
    st.session_state.previous_search = ""

if search_term != st.session_state.previous_search:
    st.session_state.previous_search = search_term
    st.rerun()   # ← Sudah diperbaiki

# Proses filtering
if search_term and search_term.strip() != "":
    search_lower = search_term.lower().strip()
    
    matched_ids = set()
    for item in all_rab_items:
        if search_lower in item.get('code', '').lower() or search_lower in item.get('description', '').lower():
            matched_ids.add(item['id'])
            current = item
            while current.get('parent_id'):
                matched_ids.add(current['parent_id'])
                current = next((x for x in all_rab_items if x['id'] == current['parent_id']), None)
                if current is None:
                    break

    filtered_items = [item for item in all_rab_items if item['id'] in matched_ids]
    match_count = len([i for i in filtered_items if search_lower in i.get('code','').lower() or search_lower in i.get('description','').lower()])
    st.success(f"✅ Ditemukan **{match_count} item** yang cocok dengan **'{search_term}'**")
else:
    filtered_items = all_rab_items

st.divider()

# ==================== TAMBAH ITEM ====================
with st.expander("➕ Tambah Item BARU", expanded=False):
    col1, col2 = st.columns([1, 2])
    with col1:
        level = st.selectbox("Level", [0, 1, 2, 3], index=0)
        parent_options = ["Tidak ada (Main Item)"] + [f"{item['code']} - {item['description'][:40]}" for item in all_rab_items if item.get('level') == level-1]
        parent_choice = st.selectbox("Parent Item", parent_options)
    with col2:
        code = st.text_input("Kode Item", value="A.1")
        description = st.text_input("Uraian Pekerjaan", value="Pekerjaan ...")
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        volume = st.number_input("Volume", value=1.0, step=0.01)
        unit = st.text_input("Satuan", value="m³")
    with col_b:
        unit_price = st.number_input("Harga Satuan (Rp)", value=100000, step=1000)
    with col_c:
        sort_order = st.number_input("Urutan", value=1, step=1)
    
    if st.button("💾 Simpan Item BARU", type="primary"):
        parent_id = None
        if parent_choice != "Tidak ada (Main Item)":
            parent_code = parent_choice.split(" - ")[0]
            parent = next((item for item in all_rab_items if item['code'] == parent_code), None)
            if parent:
                parent_id = parent['id']
        
        new_item = {
            "project_id": project_id, "code": code, "description": description,
            "volume": volume, "unit": unit, "unit_price": unit_price,
            "level": level, "parent_id": parent_id, "sort_order": sort_order
        }
        supabase.table("rab_items").insert(new_item).execute()
        st.success("✅ Item berhasil ditambahkan!")
        st.rerun()

st.divider()

# ==================== STRUKTUR RAB ====================
st.subheader("Struktur RAB")

def display_rab_tree(items, parent_id=None, level=0):
    children = [item for item in items if item.get("parent_id") == parent_id]
    for item in sorted(children, key=lambda x: x.get('sort_order', 0)):
        indent = "　" * level * 3
        total = (item.get("volume") or 0) * (item.get("unit_price") or 0)
        
        is_match = False
        if search_term:
            search_lower = search_term.lower().strip()
            if search_lower in item.get('code', '').lower() or search_lower in item.get('description', '').lower():
                is_match = True
        
        label = f"{indent}{item.get('code','')} - {item.get('description','')[:65]}"
        if is_match:
            label = f"✅ {label}"

        with st.expander(label, expanded=bool(search_term)):
            col1, col2, col3 = st.columns([3,2,2])
            col1.write(f"**Volume:** {item.get('volume','0')} {item.get('unit','')}")
            col2.write(f"**Harga Satuan:** {format_rupiah(item.get('unit_price',0))}")
            col3.write(f"**Total:** {format_rupiah(total)}")

            col_edit, col_delete = st.columns(2)
            with col_edit:
                if st.button("✏️ Edit", key=f"edit_{item['id']}"):
                    st.session_state.edit_item = item
                    st.rerun()
            with col_delete:
                if st.button("🗑️ Hapus", key=f"del_{item['id']}"):
                    st.session_state.delete_item = item
                    st.rerun()

            display_rab_tree(items, item["id"], level + 1)

if filtered_items:
    display_rab_tree(filtered_items)
else:
    if search_term:
        st.warning(f"Tidak ada item yang cocok dengan **'{search_term}'**")
    else:
        st.info("Belum ada data RAB.")

# ==================== EDIT FORM ====================
if "edit_item" in st.session_state:
    item = st.session_state.edit_item
    
    with st.form("edit_rab_form"):
        st.subheader(f"✏️ Edit Item: {item['code']} - {item['description']}")
        
        col1, col2 = st.columns(2)
        with col1:
            new_code = st.text_input("Kode", value=item.get('code', ''))
            new_desc = st.text_input("Uraian Pekerjaan", value=item.get('description', ''))
            new_level = st.selectbox("Level", [0,1,2,3], index=item.get('level', 0))
        with col2:
            new_volume = st.number_input("Volume", value=float(item.get('volume', 0)), step=0.01)
            new_unit = st.text_input("Satuan", value=item.get('unit', ''))
            new_price = st.number_input("Harga Satuan (Rp)", value=float(item.get('unit_price', 0)), step=1000)

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.form_submit_button("💾 Simpan Perubahan", type="primary", use_container_width=True):
                try:
                    supabase.table("rab_items").update({
                        "code": new_code,
                        "description": new_desc,
                        "level": new_level,
                        "volume": new_volume,
                        "unit": new_unit,
                        "unit_price": new_price,
                        "updated_at": datetime.now().isoformat()
                    }).eq("id", item['id']).execute()
                    
                    st.success("✅ Item berhasil diperbarui!")
                    del st.session_state.edit_item
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        
        with col_btn2:
            if st.form_submit_button("Batal", use_container_width=True):
                del st.session_state.edit_item
                st.rerun()

st.divider()

# Export buttons
col1, col2 = st.columns(2)
with col1:
    st.button("📊 Export ke Excel (Format Profesional)", type="primary", use_container_width=True)
with col2:
    st.button("🖨️ Export ke PDF", type="primary", use_container_width=True)
