import streamlit as st
from utils.ahsp_helper import (
    get_all_ahsp_items,
    update_unit_price,
    get_price_breakdown,
    update_all_ahsp_prices,
    search_ahsp_items,
    get_ahsp_by_division,
    get_all_resources,
    add_resource,
    get_item_composition,
    save_item_composition
)
from utils.helpers import format_rupiah
from datetime import datetime
from utils.supabase_client import get_supabase

supabase = get_supabase()

st.header("📋 Database AHSP - Full Management")
st.caption("Level 3 • Kelola Item, Resource, dan Komposisi")

# ==================== TABS ====================
tab1, tab2, tab3 = st.tabs(["📋 Daftar AHSP + Komposisi", "➕ Kelola Resource", "➕ Tambah Item AHSP"])

# ============================================================
# TAB 1: DAFTAR AHSP + KOMPOSISI
# ============================================================
with tab1:
    col1, col2, col3 = st.columns([2, 1, 1])
    with col2:
        if st.button("🔄 Update Semua Harga", type="primary", use_container_width=True):
            with st.spinner("Memperbarui semua harga..."):
                count = update_all_ahsp_prices()
                st.success(f"Berhasil update {count} item!")
                st.rerun()
    with col3:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    st.divider()

    # Search & Filter
    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        search_term = st.text_input("🔍 Cari AHSP", placeholder="Kode atau uraian...")
    with col_f2:
        all_items_temp = get_all_ahsp_items()
        divisions = sorted(list(set([item.get('division_name', 'Lainnya') for item in all_items_temp if item.get('division_name')])))
        selected_division = st.selectbox("Filter Divisi", ["Semua"] + divisions)

    if search_term:
        items = search_ahsp_items(search_term)
    elif selected_division != "Semua":
        items = get_ahsp_by_division(selected_division)
    else:
        items = get_all_ahsp_items()

    if not items:
        st.info("Tidak ada data AHSP.")
        st.stop()

    st.subheader(f"Total: {len(items)} item")

    for item in items:
        with st.expander(f"**{item['code']}** — {item['description']}", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Satuan", item.get("unit", "-"))
            col2.metric("Harga Tersimpan", format_rupiah(item.get('stored_unit_price', 0)))
            col3.metric("Harga Dihitung", format_rupiah(item.get('calculated_unit_price', 0)))
            col4.metric("Divisi", item.get('division_name', '-'))

            breakdown = get_price_breakdown(item['id'])
            st.markdown("**Rincian Biaya:**")
            bcol1, bcol2, bcol3 = st.columns(3)
            bcol1.write(f"Material: {format_rupiah(breakdown.get('material_cost', 0))}")
            bcol2.write(f"Upah: {format_rupiah(breakdown.get('labor_cost', 0))}")
            bcol3.write(f"Peralatan: {format_rupiah(breakdown.get('equipment_cost', 0))}")

            st.divider()
            st.markdown("**Komposisi Resource saat ini:**")

            composition = get_item_composition(item['id'])
            if composition:
                for comp in composition:
                    res = comp.get('ahsp_resources', {})
                    st.write(f"• {res.get('name', 'Unknown')} → Koefisien: **{comp['coefficient']}** {res.get('unit', '')}")
            else:
                st.caption("Belum ada komposisi.")

            # Form tambah komposisi
            with st.form(f"form_comp_{item['id']}", clear_on_submit=True):
                resources = get_all_resources()
                if resources:
                    res_options = {f"{r['name']} ({r['unit']})": r['id'] for r in resources}
                    selected_res_label = st.selectbox("Tambah Resource", list(res_options.keys()), key=f"res_{item['id']}")
                    coefficient = st.number_input("Koefisien", value=1.0, step=0.01, key=f"coef_{item['id']}")

                    if st.form_submit_button("➕ Tambahkan Resource ke Komposisi"):
                        resource_id = res_options[selected_res_label]
                        current_comp = get_item_composition(item['id'])
                        new_list = [{"resource_id": c['resource_id'], "coefficient": c['coefficient']} for c in current_comp]
                        new_list.append({"resource_id": resource_id, "coefficient": coefficient})

                        if save_item_composition(item['id'], new_list):
                            st.success("Komposisi berhasil ditambahkan!")
                            st.rerun()
                else:
                    st.warning("Belum ada Resource. Tambahkan dulu di tab 'Kelola Resource'.")

            if st.button("🔄 Update Harga Item Ini", key=f"upd_{item['id']}"):
                if update_unit_price(item['id']):
                    st.success("Harga diperbarui!")
                    st.rerun()

# ============================================================
# TAB 2: KELOLA RESOURCE
# ============================================================
with tab2:
    st.subheader("Tambah Resource Baru")

    with st.form("form_add_resource"):
        col1, col2 = st.columns(2)
        with col1:
            res_code = st.text_input("Kode", placeholder="M001")
            res_name = st.text_input("Nama Resource", placeholder="Semen Portland 50kg")
            res_type = st.selectbox("Jenis Resource", ["material", "labor", "equipment"])
        with col2:
            res_unit = st.text_input("Satuan", placeholder="zak / OH / ls")
            res_price = st.number_input("Harga Saat Ini (Rp)", value=0, step=1000)

        if st.form_submit_button("💾 Simpan Resource", type="primary"):
            if res_code and res_name and res_unit:
                if add_resource(res_code, res_name, res_type, res_unit, float(res_price)):
                    st.success("Resource berhasil ditambahkan!")
                    st.rerun()
                else:
                    st.error("Gagal menambahkan (mungkin kode sudah ada).")
            else:
                st.warning("Mohon isi semua field yang wajib.")

    st.divider()
    st.subheader("Daftar Semua Resource")
    resources = get_all_resources()
    if resources:
        for r in resources:
            st.write(f"`{r['code']}` | **{r['name']}** | {r['resource_type']} | {r['unit']} | {format_rupiah(r['current_price'])}")
    else:
        st.info("Belum ada resource.")

# ============================================================
# TAB 3: TAMBAH ITEM AHSP
# ============================================================
with tab3:
    st.subheader("Tambah Item AHSP Baru")

    with st.form("form_add_ahsp"):
        new_code = st.text_input("Kode AHSP *", placeholder="A.3.1")
        new_desc = st.text_input("Uraian Pekerjaan *", placeholder="Pasangan Bata Merah 1:4")
        col1, col2 = st.columns(2)
        with col1:
            new_unit = st.text_input("Satuan *", placeholder="m²")
        with col2:
            new_base_price = st.number_input("Harga Dasar (opsional)", value=0)

        if st.form_submit_button("💾 Simpan Item AHSP", type="primary"):
            if new_code and new_desc and new_unit:
                try:
                    supabase.table("ahsp_items").insert({
                        "code": new_code,
                        "description": new_desc,
                        "unit": new_unit,
                        "base_unit_price": new_base_price
                    }).execute()
                    st.success(f"Item AHSP '{new_code}' berhasil ditambahkan!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Kode, Uraian, dan Satuan wajib diisi.")

st.caption(f"Update terakhir: {datetime.now().strftime('%d %B %Y %H:%M')}")
