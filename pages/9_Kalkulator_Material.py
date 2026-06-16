"""
pages/9_Kalkulator_Material.py
Kalkulator Kebutuhan Material.

Mode A — Material curah (rumus koefisien SNI): input volume -> daftar material.
         Koefisien DAPAT DIEDIT di layar (default dari rujukan SNI, perlu verifikasi).
Mode B — Rincian komponen (input kuantitas manual): untuk pekerjaan berbasis
         komponen (elektrikal, plumbing, kusen, plafon, dll) yang TIDAK punya
         koefisien material curah yang sahih. Kamu input kuantitas dari gambar
         kerja; kalkulator hanya menjumlahkan dan (opsional) mengalikan harga.

Halaman ini berdiri sendiri dan tidak menulis ke database.
"""

import sys
from io import BytesIO
from pathlib import Path
from datetime import datetime

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.helpers import format_rupiah
from utils.material_coeffs import (
    MATERIAL_COEFFS,
    SAK_SEMEN_KG_DEFAULT,
    convert_to_buy_unit,
)


# =====================================================================
# HELPER EXPORT
# =====================================================================
def _build_excel(title: str, header: list, data_rows: list, total_label=None, total_val=None) -> BytesIO:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Material"
    thin = Border(*[Side(style="thin")] * 4)

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(header))
    ws.cell(row=1, column=1, value=title).font = Font(bold=True, size=14, color="0d6efd")
    ws.cell(row=2, column=1, value=f"Tanggal: {datetime.now().strftime('%d %B %Y')}").font = Font(italic=True, size=10)

    for c, h in enumerate(header, 1):
        cell = ws.cell(row=4, column=c, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="0d6efd", end_color="0d6efd", fill_type="solid")
        cell.alignment = Alignment(horizontal="center")
        cell.border = thin

    r = 5
    for row in data_rows:
        for c, key in enumerate(header, 1):
            ws.cell(row=r, column=c, value=row.get(key, "")).border = thin
        r += 1

    if total_label is not None:
        ws.cell(row=r + 1, column=1, value=total_label).font = Font(bold=True)
        ws.cell(row=r + 1, column=len(header), value=total_val).font = Font(bold=True)

    for c in range(1, len(header) + 1):
        ws.column_dimensions[chr(64 + c)].width = 22

    out = BytesIO()
    wb.save(out)
    out.seek(0)
    return out


def _excel_download(job, volume, vunit, rows, grand_cost):
    header = list(rows[0].keys()) if rows else []
    buf = _build_excel(
        f"KEBUTUHAN MATERIAL — {job}", header, rows,
        "TOTAL", format_rupiah(grand_cost) if grand_cost > 0 else None,
    )
    st.download_button(
        "⬇️ Download Excel", data=buf,
        file_name=f"Material_{job[:20].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


def _excel_download_modeb(display, total):
    header = list(display[0].keys()) if display else []
    buf = _build_excel(
        "RINCIAN KEBUTUHAN MATERIAL (Komponen)", header, display,
        "TOTAL", format_rupiah(total) if total > 0 else None,
    )
    st.download_button(
        "⬇️ Download Excel", data=buf,
        file_name=f"Material_Rincian_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


st.header("🧮 Kalkulator Kebutuhan Material")

st.warning(
    "⚠️ Koefisien default diambil dari rujukan publik yang mengutip SNI dan "
    "**belum tentu seragam antar sumber**. Verifikasi terhadap SNI/AHSP PUPR "
    "resmi sebelum dipakai untuk order atau anggaran final. Semua koefisien di "
    "Mode A bisa kamu ubah langsung di tabel."
)

mode = st.radio(
    "Pilih mode perhitungan:",
    [
        "Mode A — Material curah (rumus SNI)",
        "Mode B — Rincian komponen (input manual)",
    ],
    horizontal=True,
)

# Pengaturan umum
with st.expander("⚙️ Pengaturan", expanded=False):
    sak_semen_kg = st.number_input(
        "Berat 1 sak semen (kg)", min_value=1.0, value=SAK_SEMEN_KG_DEFAULT, step=1.0,
        help="Untuk konversi kebutuhan semen dari kg ke sak."
    )

st.divider()

# =====================================================================
# MODE A — MATERIAL CURAH (RUMUS SNI)
# =====================================================================
if mode.startswith("Mode A"):
    job = st.selectbox("Pilih jenis pekerjaan", list(MATERIAL_COEFFS.keys()))
    cfg = MATERIAL_COEFFS[job]
    vunit = cfg["volume_unit"]

    st.caption(f"Sumber koefisien: **{cfg['source']}**")

    volume = st.number_input(
        f"Volume pekerjaan ({vunit})", min_value=0.0, value=10.0, step=1.0
    )

    if not cfg["materials"]:
        st.info(
            "Pekerjaan ini tidak memiliki kebutuhan material curah (umumnya hanya "
            "tenaga kerja/alat). Tidak ada yang dihitung."
        )
        st.stop()

    st.markdown("#### Koefisien (dapat diedit)")
    st.caption("Koefisien = jumlah material per 1 " + vunit + " pekerjaan.")

    # Tabel koefisien yang bisa diedit
    edited = []
    for i, mat in enumerate(cfg["materials"]):
        c1, c2, c3 = st.columns([3, 2, 2])
        with c1:
            st.text_input(
                "Material", value=mat["name"], key=f"a_name_{job}_{i}",
                disabled=True, label_visibility="collapsed" if i else "visible"
            )
        with c2:
            coeff = st.number_input(
                f"Koef ({mat['unit']}/{vunit})",
                value=float(mat["coeff"]), step=0.001, format="%.4f",
                key=f"a_coeff_{job}_{i}",
                label_visibility="visible" if i == 0 else "collapsed",
            )
        with c3:
            price = st.number_input(
                "Harga/satuan beli (Rp, opsional)",
                min_value=0.0, value=0.0, step=1000.0,
                key=f"a_price_{job}_{i}",
                label_visibility="visible" if i == 0 else "collapsed",
            )
        edited.append({**mat, "coeff": coeff, "price": price})

    if st.button("🔢 Hitung Kebutuhan Material", type="primary", use_container_width=True):
        rows = []
        grand_cost = 0.0
        for mat in edited:
            total_native = mat["coeff"] * volume  # dalam satuan SNI (kg/m3/buah/liter)
            buy_val, buy_unit = convert_to_buy_unit(mat, total_native, sak_semen_kg)

            # Biaya dihitung atas satuan beli bila ada, kalau tidak atas satuan native
            if buy_val is not None:
                cost = buy_val * mat["price"]
                buy_display = f"{buy_val:,.2f} {buy_unit}"
            else:
                cost = total_native * mat["price"]
                buy_display = "—"
            grand_cost += cost

            rows.append({
                "Material": mat["name"],
                f"Jumlah ({mat['unit']})": f"{total_native:,.2f}",
                "Satuan Beli": buy_display,
                "Perkiraan Biaya": format_rupiah(cost) if mat["price"] > 0 else "—",
            })

        st.markdown("#### Hasil Kebutuhan Material")
        st.caption(f"Untuk **{volume:,.2f} {vunit}** pekerjaan **{job}**")
        st.table(rows)

        if grand_cost > 0:
            st.metric("Perkiraan Total Biaya Material", format_rupiah(grand_cost))

        # Export Excel
        _excel_download(job, volume, vunit, rows, grand_cost)


# =====================================================================
# MODE B — RINCIAN KOMPONEN (INPUT MANUAL)
# =====================================================================
else:
    st.markdown(
        "Untuk pekerjaan berbasis komponen (elektrikal, plumbing, kusen, plafon, "
        "keramik, atap/rangka, cat, pembesian). Masukkan **kuantitas dari gambar "
        "kerja** beserta satuan dan harga. Kalkulator menjumlahkan biayanya."
    )
    st.caption(
        "Catatan jujur: untuk pekerjaan ini tidak ada koefisien material curah "
        "yang sahih, jadi kuantitas berasal dari hitunganmu, bukan rumus."
    )

    kategori = st.selectbox(
        "Kategori pekerjaan",
        ["Elektrikal", "Plumbing", "Kusen kayu/aluminium", "Plafon",
         "Keramik/lantai", "Atap/rangka", "Cat", "Pembesian", "Lainnya"],
    )

    if "modeb_rows" not in st.session_state:
        st.session_state.modeb_rows = []

    with st.form("modeb_add", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns([3, 1.2, 1.2, 1.6])
        with c1:
            item = st.text_input("Uraian item", placeholder="mis. Titik lampu, Pipa PVC Ø1/2\"")
        with c2:
            qty = st.number_input("Kuantitas", min_value=0.0, value=1.0, step=1.0)
        with c3:
            satuan = st.text_input("Satuan", placeholder="titik / m / unit")
        with c4:
            harga = st.number_input("Harga satuan (Rp)", min_value=0.0, value=0.0, step=1000.0)

        if st.form_submit_button("➕ Tambah item", type="primary", use_container_width=True):
            if item.strip():
                st.session_state.modeb_rows.append({
                    "kategori": kategori, "item": item.strip(),
                    "qty": qty, "satuan": satuan.strip(), "harga": harga,
                })
            else:
                st.warning("Uraian item tidak boleh kosong.")

    rows = st.session_state.modeb_rows
    if rows:
        st.markdown("#### Daftar Item")
        display = []
        total = 0.0
        for idx, r in enumerate(rows):
            subtotal = r["qty"] * r["harga"]
            total += subtotal
            display.append({
                "Kategori": r["kategori"],
                "Uraian": r["item"],
                "Kuantitas": f"{r['qty']:,.2f} {r['satuan']}",
                "Harga Satuan": format_rupiah(r["harga"]) if r["harga"] else "—",
                "Subtotal": format_rupiah(subtotal) if r["harga"] else "—",
            })
        st.table(display)
        if total > 0:
            st.metric("Perkiraan Total Biaya", format_rupiah(total))

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🗑️ Kosongkan daftar", use_container_width=True):
                st.session_state.modeb_rows = []
                st.rerun()
        with col_b:
            _excel_download_modeb(display, total)
    else:
        st.info("Belum ada item. Tambahkan lewat form di atas.")
