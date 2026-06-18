"""
pages/10_Pengaturan.py
Halaman Pengaturan Perusahaan.

Mengisi/mengubah data perusahaan (tabel company_settings) yang dipakai sebagai
kop surat pada PDF invoice & SPK. Data bersifat global (bukan per-proyek).
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.company import get_company_settings, save_company_settings, upload_logo

st.header("⚙️ Pengaturan Perusahaan")
st.caption("Data ini dipakai sebagai kop surat pada PDF & Excel (Invoice, SPK, RAB, RAP, Pengeluaran).")

company = get_company_settings()

# ==================== UPLOAD LOGO (di luar form, diproses langsung) ====================
st.subheader("Logo Perusahaan")
lc1, lc2 = st.columns([2, 1])
with lc1:
    logo_file = st.file_uploader(
        "Upload logo (PNG/JPG)", type=["png", "jpg", "jpeg"],
        help="Logo akan disimpan permanen dan dipakai di kop dokumen.",
    )
    if logo_file is not None:
        if st.button("⬆️ Simpan Logo", type="primary"):
            try:
                url = upload_logo(
                    logo_file.getvalue(), logo_file.name,
                    logo_file.type or "image/png",
                )
                # Simpan URL logo ke company_settings (pertahankan field lain)
                current = get_company_settings()
                current["logo_path"] = url
                save_company_settings(current)
                st.success("✅ Logo tersimpan dan akan dipakai di kop dokumen.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Gagal upload logo: {e}")
with lc2:
    if company.get("logo_path"):
        st.caption("Logo saat ini:")
        try:
            st.image(company["logo_path"], width=140)
        except Exception:
            st.warning("Logo tidak bisa dimuat.")

st.divider()

with st.form("company_form"):
    st.subheader("Identitas Perusahaan")
    company_name = st.text_input("Nama Perusahaan", value=company.get("company_name", ""))
    address = st.text_area("Alamat", value=company.get("address", ""), height=70)
    c1, c2 = st.columns(2)
    phone = c1.text_input("Telepon", value=company.get("phone", ""))
    email = c2.text_input("Email", value=company.get("email", ""))
    npwp = st.text_input("NPWP", value=company.get("npwp", ""))
    logo_path = st.text_input(
        "URL Logo (alternatif manual)", value=company.get("logo_path", ""),
        help="Terisi otomatis saat upload logo. Bisa juga tempel URL gambar manual.",
    )

    st.subheader("Rekening Bank (untuk footer Invoice)")
    c3, c4 = st.columns(2)
    bank_name = c3.text_input("Nama Bank", value=company.get("bank_name", ""))
    account_number = c4.text_input("No. Rekening", value=company.get("account_number", ""))
    account_holder = st.text_input("Atas Nama", value=company.get("account_holder", ""))

    footer = st.text_area("Catatan Footer (opsional)", value=company.get("footer", ""), height=60)

    submitted = st.form_submit_button("💾 Simpan", type="primary", use_container_width=True)

if submitted:
    try:
        save_company_settings({
            "company_name": company_name, "address": address, "phone": phone,
            "email": email, "npwp": npwp, "logo_path": logo_path,
            "bank_name": bank_name, "account_number": account_number,
            "account_holder": account_holder, "footer": footer,
        })
        st.success("✅ Data perusahaan tersimpan. Kop surat PDF & Excel akan memakai data ini.")
    except Exception as e:
        st.error(f"❌ Gagal menyimpan: {e}")
