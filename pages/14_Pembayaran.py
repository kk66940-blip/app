"""
pages/14_Pembayaran.py
Pencatatan Pembayaran Masuk dari Klien (kas riil).

Berbeda dari opname (nilai tertagih): halaman ini mencatat uang yang BENAR-BENAR
diterima dari klien. Selisih opname - pembayaran = piutang (belum dibayar).
"""

import sys
from pathlib import Path
from datetime import datetime

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.supabase_client import get_supabase
from utils.helpers import format_rupiah

supabase = get_supabase()

st.header("💵 Pembayaran Masuk dari Klien")
st.caption("Catat uang yang benar-benar diterima dari klien (kas riil), bukan nilai tagihan/opname.")

project_id = st.session_state.get("current_project_id")
if not project_id:
    st.warning("Pilih proyek di sidebar terlebih dahulu.")
    st.stop()

project_name = st.session_state.get("selected_project_name", "Proyek")

# Ambil pembayaran proyek ini
payments = supabase.table("project_payments").select("*").eq(
    "project_id", project_id).order("payment_date", desc=True).execute().data or []

total_masuk = sum((p.get("amount", 0) or 0) for p in payments)

st.metric("Total Uang Masuk", format_rupiah(total_masuk))
st.divider()

# ==================== TAMBAH PEMBAYARAN ====================
with st.expander("➕ Catat Pembayaran Masuk", expanded=not payments):
    with st.form("form_payment", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            pay_date = st.date_input("Tanggal Pembayaran", datetime.now().date())
            pay_amount = st.number_input("Jumlah Diterima (Rp)", min_value=0, step=100000, format="%d")
        with c2:
            pay_termin = st.text_input("Termin / Tahap", placeholder="mis. Termin 1, DP, Pelunasan")
            pay_desc = st.text_input("Keterangan")

        if st.form_submit_button("💾 Simpan Pembayaran", type="primary", use_container_width=True):
            if pay_amount > 0:
                try:
                    supabase.table("project_payments").insert({
                        "project_id": project_id,
                        "payment_date": str(pay_date),
                        "amount": pay_amount,
                        "termin": pay_termin,
                        "description": pay_desc,
                    }).execute()
                    st.success(f"Pembayaran {format_rupiah(pay_amount)} tercatat.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal menyimpan: {e}")
            else:
                st.error("Jumlah harus lebih dari 0.")

st.divider()

# ==================== DAFTAR PEMBAYARAN ====================
st.subheader("Riwayat Pembayaran")
if not payments:
    st.info("Belum ada pembayaran tercatat.")
else:
    for p in payments:
        with st.container(border=True):
            cc = st.columns([2, 2, 1])
            cc[0].markdown(f"**{format_rupiah(p.get('amount', 0))}**  \n{p.get('payment_date', '')}")
            cc[1].markdown(f"{p.get('termin', '') or '—'}  \n_{p.get('description', '') or ''}_")
            with cc[2]:
                with st.popover("🗑️", use_container_width=True):
                    st.write("Hapus pembayaran ini?")
                    if st.button("Ya, hapus", key=f"delpay_{p['id']}", type="primary"):
                        try:
                            supabase.table("project_payments").delete().eq("id", p['id']).execute()
                            st.success("Pembayaran dihapus.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal hapus: {e}")

    st.divider()
    st.metric("TOTAL UANG MASUK", format_rupiah(total_masuk))
