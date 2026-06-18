"""
pages/11_Kurva_S.py
Kurva-S: Progres Rencana (linear) vs Realisasi (dari opname per periode).

Realisasi: kumulatif berbasis NILAI = Σ(volume aktual × harga) ÷ grand total RAB.
Rencana: garis lurus 0%→100% antara tanggal mulai & selesai (kamu input).

CATATAN: garis rencana linear adalah baseline disederhanakan, bukan jadwal
sungguhan. Berguna sebagai indikasi kasar, bukan klaim keterlambatan presisi.
"""

import sys
from pathlib import Path
from datetime import date

import streamlit as st
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.supabase_client import get_supabase
from utils.helpers import compute_scurve_actual, compute_scurve_plan_linear

supabase = get_supabase()

st.header("📈 Kurva-S — Rencana vs Realisasi")

project_id = st.session_state.get("current_project_id")
if not project_id:
    st.warning("Pilih proyek di sidebar terlebih dahulu.")
    st.stop()

project_name = st.session_state.get("selected_project_name", "Proyek")

# Ambil data proyek (untuk default tanggal mulai)
proj = supabase.table("projects").select("start_date").eq("id", project_id).execute().data
default_start = None
if proj and proj[0].get("start_date"):
    try:
        default_start = date.fromisoformat(str(proj[0]["start_date"])[:10])
    except Exception:
        default_start = None

# Ambil RAB + periode + opname
rab_items = supabase.table("rab_items").select("id, volume, unit_price").eq(
    "project_id", project_id).execute().data or []
periods = supabase.table("opname_periods").select("id, period_no, opname_date").eq(
    "project_id", project_id).execute().data or []

if not rab_items:
    st.info("Belum ada data RAB untuk proyek ini.")
    st.stop()
if not periods:
    st.info("Belum ada periode opname. Buat opname dulu untuk melihat realisasi.")
    st.stop()

# Opname per periode: {period_id: {rab_item_id: actual_volume}}
period_ids = [p["id"] for p in periods]
opname_rows = supabase.table("opname_details").select(
    "period_id, rab_item_id, actual_volume").in_("period_id", period_ids).execute().data or []
opname_by_period = {}
for row in opname_rows:
    opname_by_period.setdefault(row["period_id"], {})[row["rab_item_id"]] = row.get("actual_volume", 0)

# ---------- Input tanggal rencana ----------
st.markdown("##### Periode Rencana (untuk garis baseline)")
c1, c2 = st.columns(2)
with c1:
    start_plan = st.date_input("Tanggal Mulai", value=default_start or date.today())
with c2:
    end_plan = st.date_input("Tanggal Selesai (rencana)", value=date.today())

st.caption("⚠️ Garis rencana adalah baseline linear (garis lurus) — indikasi kasar, "
           "bukan jadwal detail. Realisasi diambil dari opname per periode (berbasis nilai).")

# ---------- Hitung ----------
actual = compute_scurve_actual(rab_items, periods, opname_by_period)
plan = compute_scurve_plan_linear(start_plan, end_plan, n_points=max(len(actual), 6))

if not actual:
    st.warning("Realisasi belum bisa dihitung (grand total RAB 0 atau belum ada opname bernilai).")
    st.stop()

# ---------- Grafik ----------
fig = go.Figure()

if plan:
    fig.add_trace(go.Scatter(
        x=[p["date"] for p in plan],
        y=[p["plan_pct"] for p in plan],
        mode="lines",
        name="Rencana (linear)",
        line=dict(color="#9ca3af", width=2, dash="dash"),
    ))

fig.add_trace(go.Scatter(
    x=[a["date"] for a in actual],
    y=[a["actual_pct"] for a in actual],
    mode="lines+markers",
    name="Realisasi",
    line=dict(color="#0d6efd", width=3),
    marker=dict(size=8),
))

fig.update_layout(
    title=f"Kurva-S — {project_name}",
    xaxis_title="Tanggal",
    yaxis_title="Progres Kumulatif (%)",
    yaxis=dict(range=[0, 105]),
    hovermode="x unified",
    height=480,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
st.plotly_chart(fig, use_container_width=True)

# ---------- Ringkasan ----------
last_actual = actual[-1]["actual_pct"]
st.divider()
m1, m2, m3 = st.columns(3)
m1.metric("Realisasi Terakhir", f"{last_actual:.2f}%")
m2.metric("Jumlah Periode", len(actual))
# Deviasi vs rencana di tanggal opname terakhir (perkiraan kasar)
if plan and end_plan > start_plan:
    total_days = (end_plan - start_plan).days
    try:
        last_date = date.fromisoformat(str(actual[-1]["date"])[:10])
        elapsed = (last_date - start_plan).days
        plan_pct_now = max(0.0, min(100.0, elapsed / total_days * 100.0)) if total_days > 0 else 0.0
        deviasi = last_actual - plan_pct_now
        m3.metric("Deviasi vs Rencana", f"{deviasi:+.2f}%",
                  delta=f"{deviasi:+.1f}%",
                  help="Positif = lebih cepat dari baseline linear; negatif = di bawahnya. "
                       "Ingat baseline ini garis lurus, jadi tafsirkan sebagai indikasi kasar.")
    except Exception:
        m3.metric("Deviasi vs Rencana", "—")

# ---------- Tabel data ----------
with st.expander("📋 Data per periode", expanded=False):
    rows = [{"Periode": a["period_no"], "Tanggal": a["date"],
             "Realisasi Kumulatif (%)": f"{a['actual_pct']:.2f}%"} for a in actual]
    st.table(rows)
