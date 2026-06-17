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

from utils.company import get_company_settings, save_company_settings

st.header("⚙️ Pengaturan Perusahaan")
st.caption("Data ini dipakai sebagai kop surat pada PDF Invoice & SPK.")

company = get_company_settings()

with st.form("company_form"):
    st.subheader("Identitas Perusahaan")
    company_name = st.text_input("Nama Perusahaan", value=company.get("company_name", ""))
    address = st.text_area("Alamat", value=company.get("address", ""), height=70)
    c1, c2 = st.columns(2)
    phone = c1.text_input("Telepon", value=company.get("phone", ""))
    email = c2.text_input("Email", value=company.get("email", ""))
    npwp = st.text_input("NPWP", value=company.get("npwp", ""))
    logo_path = st.text_input(
        "URL Logo (opsional)", value=company.get("logo_path", ""),
        help="Tempel URL gambar logo (https://...). Dipakai di kop PDF bila valid.",
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
        st.success("✅ Data perusahaan tersimpan. Kop surat PDF akan memakai data ini.")
    except Exception as e:
        st.error(f"❌ Gagal menyimpan: {e}")

if company.get("logo_path"):
    st.divider()
    st.caption("Pratinjau logo:")
    try:
        st.image(company["logo_path"], width=180)
    except Exception:
        st.warning("URL logo tidak bisa dimuat sebagai gambar. Periksa kembali URL-nya.")
