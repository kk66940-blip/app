"""
pages/12_Adendum.py
Halaman khusus Pekerjaan Tambah / Adendum.

Adendum disimpan di tabel rab_items dengan penanda is_addendum=true (sehingga
tetap ikut opname & laporan), tapi dikelola & dilacak terpisah di sini, dan
disembunyikan dari halaman RAB utama.
"""

import sys
from pathlib import Path
from datetime import datetime

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.supabase_client import get_supabase
from utils.helpers import format_rupiah, next_rab_code

supabase = get_supabase()

st.header("📌 Pekerjaan Tambah / Adendum")
st.caption("Pekerjaan di luar RAB asli. Tetap ikut opname & laporan, dilacak terpisah di sini.")

project_id = st.session_state.get("current_project_id")
if not project_id:
    st.warning("Pilih proyek di sidebar terlebih dahulu.")
    st.stop()

# Ambil semua item proyek (untuk penomoran kode & lookup induk)
all_items = supabase.table("rab_items").select("*").eq(
    "project_id", project_id).order("level").order("sort_order").execute().data or []

adendum_items = [it for it in all_items if it.get("is_addendum")]

# ==================== RINGKASAN ====================
def _val(it):
    return (it.get("volume", 0) or 0) * (it.get("unit_price", 0) or 0)

total_adendum = sum(_val(it) for it in adendum_items)
m1, m2 = st.columns(2)
m1.metric("Jumlah Item Adendum", len(adendum_items))
m2.metric("Total Nilai Adendum", format_rupiah(total_adendum))

st.divider()

# ==================== TAMBAH ADENDUM ====================
with st.expander("➕ Tambah Pekerjaan Adendum", expanded=not adendum_items):
    c1, c2 = st.columns([2, 1])
    with c1:
        a_desc = st.text_input("Uraian Pekerjaan", placeholder="mis. Tambah dinding partisi lantai 2")
        a_code = st.text_input("Kode (opsional)", value="",
                               placeholder="Kosongkan untuk otomatis (ADD.x)")
    with c2:
        a_unit = st.text_input("Satuan", value="m³")
        a_sort = st.number_input("Urutan", value=len(adendum_items) + 1, step=1)

    c3, c4 = st.columns(2)
    with c3:
        a_volume = st.number_input("Volume", min_value=0.0, value=1.0, step=0.01)
    with c4:
        a_price = st.number_input("Harga Satuan (Rp)", min_value=0.0, value=0.0, step=1000.0)

    nilai_preview = a_volume * a_price
    st.caption(f"Nilai item: **{format_rupiah(nilai_preview)}**")

    if st.button("💾 Simpan Adendum", type="primary", use_container_width=True):
        if not a_desc.strip():
            st.warning("Uraian pekerjaan wajib diisi.")
        else:
            try:
                # Kode otomatis: ADD.N bila dikosongkan
                if a_code.strip():
                    code = a_code.strip()
                else:
                    existing_add = [it for it in all_items if it.get("is_addendum")
                                    and str(it.get("code", "")).upper().startswith("ADD.")]
                    max_n = 0
                    for it in existing_add:
                        try:
                            max_n = max(max_n, int(str(it["code"]).split(".")[-1]))
                        except (ValueError, IndexError):
                            pass
                    code = f"ADD.{max_n + 1}"

                supabase.table("rab_items").insert({
                    "project_id": project_id,
                    "code": code,
                    "description": a_desc.strip(),
                    "volume": a_volume,
                    "unit": a_unit,
                    "unit_price": a_price,
                    "level": 0,
                    "parent_id": None,
                    "sort_order": a_sort,
                    "is_addendum": True,
                }).execute()
                st.success(f"✅ Adendum '{code}' ditambahkan!")
                st.rerun()
            except Exception as e:
                st.error(f"Gagal menyimpan: {e}")

st.divider()

# ==================== DAFTAR ADENDUM ====================
st.subheader("Daftar Pekerjaan Adendum")

if not adendum_items:
    st.info("Belum ada pekerjaan adendum. Tambahkan lewat form di atas.")
else:
    for it in adendum_items:
        nilai = _val(it)
        with st.container(border=True):
            st.markdown(f"**{it.get('code', '')} — {it.get('description', '')}**")
            cc1, cc2, cc3 = st.columns(3)
            cc1.metric("Volume", f"{it.get('volume', 0):,.2f} {it.get('unit', '')}")
            cc2.metric("Harga Satuan", format_rupiah(it.get('unit_price', 0)))
            cc3.metric("Nilai", format_rupiah(nilai))

            ec1, ec2 = st.columns(2)
            with ec1:
                with st.popover("✏️ Edit", use_container_width=True):
                    with st.form(f"edit_add_{it['id']}"):
                        e_desc = st.text_input("Uraian", value=it.get('description', ''), key=f"ead_{it['id']}")
                        e_unit = st.text_input("Satuan", value=it.get('unit', ''), key=f"eau_{it['id']}")
                        e_vol = st.number_input("Volume", min_value=0.0,
                                                value=float(it.get('volume', 0)), step=0.01, key=f"eav_{it['id']}")
                        e_price = st.number_input("Harga Satuan (Rp)", min_value=0.0,
                                                  value=float(it.get('unit_price', 0)), step=1000.0, key=f"eap_{it['id']}")
                        if st.form_submit_button("💾 Simpan", type="primary"):
                            try:
                                supabase.table("rab_items").update({
                                    "description": e_desc, "unit": e_unit,
                                    "volume": e_vol, "unit_price": e_price,
                                    "updated_at": datetime.now().isoformat(),
                                }).eq("id", it['id']).execute()
                                st.success("Adendum diperbarui!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Gagal: {e}")
            with ec2:
                with st.popover("🗑️ Hapus", use_container_width=True):
                    st.warning(f"Hapus adendum **{it.get('code', '')}**? "
                               "Data opname terkait (bila ada) ikut terhapus.")
                    if st.button("Ya, hapus permanen", key=f"delA_{it['id']}", type="primary"):
                        try:
                            # Hapus opname terkait dulu (FK), lalu itemnya
                            supabase.table("opname_details").delete().eq("rab_item_id", it['id']).execute()
                            supabase.table("opname_sub_details").delete().eq("rab_item_id", it['id']).execute()
                            supabase.table("rab_items").delete().eq("id", it['id']).execute()
                            st.success("Adendum dihapus.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal hapus: {e}")

    st.divider()
    st.metric("TOTAL NILAI ADENDUM", format_rupiah(total_adendum))
