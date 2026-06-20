"""
pages/13_Rekap_Proyek.py
Rekap lintas-proyek: ringkasan semua proyek bersebelahan untuk dibandingkan,
dengan tombol "Lihat Detail" yang mengarahkan ke Dashboard proyek tsb.

Data ditarik sekaligus (bukan per-proyek dalam loop) lalu dikelompokkan di
memori, agar tetap cepat walau proyek banyak.
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.supabase_client import get_supabase
from utils.helpers import format_rupiah, compute_project_recap

supabase = get_supabase()

st.header("📑 Rekap Semua Proyek")
st.caption("Ringkasan tiap proyek bersebelahan. Klik 'Lihat Detail' untuk membuka dashboard proyek.")

# ---------- Tarik semua data sekaligus ----------
projects = supabase.table("projects").select("id, name, client, location").order("id").execute().data or []
if not projects:
    st.info("Belum ada proyek.")
    st.stop()

project_ids = [p["id"] for p in projects]

# RAB semua proyek
all_rab = supabase.table("rab_items").select(
    "id, project_id, parent_id, volume, unit_price, is_addendum").in_(
    "project_id", project_ids).execute().data or []

# Opname semua proyek: opname_details tak punya project_id langsung -> lewat
# period. Tarik periode dulu untuk peta period_id -> project_id.
periods = supabase.table("opname_periods").select("id, project_id").in_(
    "project_id", project_ids).execute().data or []
period_to_proj = {p["id"]: p["project_id"] for p in periods}
period_ids = list(period_to_proj.keys())

all_opname = []
if period_ids:
    all_opname = supabase.table("opname_details").select(
        "period_id, rab_item_id, actual_volume").in_("period_id", period_ids).execute().data or []

# Pengeluaran semua proyek
all_exp = supabase.table("project_expenses").select(
    "project_id, amount").in_("project_id", project_ids).execute().data or []

# Pembayaran masuk semua proyek (kas riil). Aman bila tabel belum ada.
all_pay = []
try:
    all_pay = supabase.table("project_payments").select(
        "project_id, amount").in_("project_id", project_ids).execute().data or []
except Exception:
    all_pay = []

# ---------- Kelompokkan per proyek ----------
rab_by_proj = {}
for it in all_rab:
    rab_by_proj.setdefault(it["project_id"], []).append(it)

opname_by_proj = {}
for d in all_opname:
    pid = period_to_proj.get(d["period_id"])
    if pid is not None:
        opname_by_proj.setdefault(pid, []).append(d)

exp_by_proj = {}
for e in all_exp:
    exp_by_proj.setdefault(e["project_id"], []).append(e)

pay_by_proj = {}
for p in all_pay:
    pay_by_proj.setdefault(p["project_id"], []).append(p)

# ---------- Hitung rekap tiap proyek ----------
recaps = []
for p in projects:
    pid = p["id"]
    r = compute_project_recap(
        pid,
        rab_by_proj.get(pid, []),
        opname_by_proj.get(pid, []),
        exp_by_proj.get(pid, []),
        pay_by_proj.get(pid, []),
    )
    r["name"] = p["name"]
    r["client"] = p.get("client", "")
    recaps.append(r)

# ---------- Total gabungan semua proyek ----------
g_rab = sum(r["nilai_rab_total"] for r in recaps)
g_opname = sum(r["total_opname"] for r in recaps)
g_masuk = sum(r["uang_masuk"] for r in recaps)
g_exp = sum(r["total_pengeluaran"] for r in recaps)
g_margin = sum(r["margin"] for r in recaps)

st.markdown("##### Total Gabungan Semua Proyek")
c1, c2, c3 = st.columns(3)
c1.metric("Total Nilai Proyek (RAB)", format_rupiah(g_rab))
c2.metric("Total Tertagih (Opname)", format_rupiah(g_opname))
c3.metric("Total Uang Masuk (Kas)", format_rupiah(g_masuk))
c4, c5, c6 = st.columns(3)
c4.metric("Total Pengeluaran", format_rupiah(g_exp))
c5.metric("Total Piutang (blm dibayar)", format_rupiah(g_opname - g_masuk))
c6.metric("Total Margin (kas)", format_rupiah(g_margin))

st.divider()

# ---------- Tabel rekap ----------
st.markdown("##### Rincian per Proyek")
st.table([{
    "Proyek": r["name"],
    "Nilai RAB": format_rupiah(r["nilai_rab_total"]),
    "Tertagih (Opname)": format_rupiah(r["total_opname"]),
    "Progres": f"{r['progres_pct']:.1f}%",
    "Uang Masuk": format_rupiah(r["uang_masuk"]),
    "Piutang": format_rupiah(r["piutang"]),
    "Pengeluaran": format_rupiah(r["total_pengeluaran"]),
    "Margin (kas)": format_rupiah(r["margin"]),
} for r in recaps])

st.divider()

# ---------- Kartu per proyek + tombol detail ----------
st.markdown("##### Buka Detail Proyek")
for r in recaps:
    with st.container(border=True):
        top = st.columns([3, 1])
        with top[0]:
            st.markdown(f"**{r['name']}**" + (f" — {r['client']}" if r['client'] else ""))
            st.progress(min(r["progres_pct"] / 100.0, 1.0),
                        text=f"Progres {r['progres_pct']:.1f}%")
        with top[1]:
            if st.button("🔍 Lihat Detail", key=f"detail_{r['project_id']}", use_container_width=True):
                st.session_state.current_project_id = r["project_id"]
                st.session_state.selected_project_name = r["name"]
                st.success(f"Proyek '{r['name']}' dipilih. Buka menu **Dashboard** untuk detailnya.")

        cc = st.columns(4)
        cc[0].metric("Nilai RAB", format_rupiah(r["nilai_rab_total"]),
                     help=f"RAB asli {format_rupiah(r['nilai_rab_asli'])}"
                          + (f" + adendum {format_rupiah(r['nilai_adendum'])}" if r["nilai_adendum"] else ""))
        cc[1].metric("Uang Masuk", format_rupiah(r["uang_masuk"]),
                     help=f"Tertagih (opname): {format_rupiah(r['total_opname'])}")
        cc[2].metric("Piutang", format_rupiah(r["piutang"]),
                     help="Sudah ditagih (opname) tapi belum dibayar klien.")
        cc[3].metric("Margin (kas)", format_rupiah(r["margin"]),
                     delta=f"{(r['margin']/r['uang_masuk']*100):.0f}%" if r["uang_masuk"] else None,
                     help="Uang masuk riil - pengeluaran.")
