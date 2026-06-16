"""
utils/material_calc.py
Logika perhitungan kebutuhan material — port 1:1 dari kalkulator React (.jsx).

Koefisien diambil PERSIS dari file kalkulator-material-bangunan.jsx (bukan SNI).
Fungsi-fungsi di sini MURNI (tanpa Streamlit) supaya mudah diuji.

CATATAN: Sebagian koefisien adalah angka praktis lapangan / asumsi, bukan SNI
resmi. Untuk anggaran/order final, verifikasi sesuai kondisi proyek. Beberapa
nilai (mis. beton, rasio campuran) bisa diubah dari UI.
"""

import math


def fmt(num, decimals=2):
    """Format angka gaya Indonesia (titik ribuan, koma desimal)."""
    n = num if (num is not None and math.isfinite(num)) else 0.0
    s = f"{n:,.{decimals}f}"  # 1,234,567.89
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def berat_besi_per_m(d_mm):
    """Berat besi (kg/m) dari diameter (mm). 0,00617 x d^2 (densitas baja)."""
    return 0.00617 * d_mm * d_mm


# ============================ PONDASI ============================
def calc_pondasi(panjang, lebar_atas, lebar_bawah, tinggi):
    volume = max(0.0, ((lebar_atas + lebar_bawah) / 2) * tinggi * panjang)
    return {
        "volume": volume,
        "batu_kali_m3": volume * 1.2,
        "semen_kg": volume * 136,
        "pasir_m3": volume * 0.52,
    }


# ============================ BETON ============================
RASIO_BETON = {
    "1:2:3": (1, 2, 3),
    "1:1.5:2.5": (1, 1.5, 2.5),
    "1:3:5": (1, 3, 5),
}
FAKTOR_BETON = 1.5


def calc_beton(panjang, lebar, tinggi, jumlah, rasio,
               jumlah_utama, dia_utama, dia_sengkang, jarak_sengkang_cm):
    a, b, c = RASIO_BETON[rasio]
    total = a + b + c

    volume = max(0.0, panjang * lebar * tinggi * jumlah)
    semen_kg = volume * FAKTOR_BETON * (a / total) * 1400
    pasir_m3 = volume * FAKTOR_BETON * (b / total)
    kerikil_m3 = volume * FAKTOR_BETON * (c / total)

    # Tulangan utama: memanjang sepanjang elemen
    panjang_utama_m = jumlah_utama * panjang * jumlah
    berat_utama_kg = panjang_utama_m * berat_besi_per_m(dia_utama)
    lonjor_utama = math.ceil(panjang_utama_m / 12) if panjang_utama_m > 0 else 0

    # Sengkang/begel: keliling penampang
    keliling_sengkang = 2 * (lebar + tinggi)
    if jarak_sengkang_cm > 0:
        jml_sengkang_per_elemen = math.floor(panjang / (jarak_sengkang_cm / 100)) + 1
    else:
        jml_sengkang_per_elemen = 0
    total_sengkang = jml_sengkang_per_elemen * jumlah
    panjang_sengkang_m = total_sengkang * keliling_sengkang
    berat_sengkang_kg = panjang_sengkang_m * berat_besi_per_m(dia_sengkang)
    lonjor_sengkang = math.ceil(panjang_sengkang_m / 12) if panjang_sengkang_m > 0 else 0

    total_besi_kg = berat_utama_kg + berat_sengkang_kg

    return {
        "volume": volume,
        "semen_kg": semen_kg,
        "pasir_m3": pasir_m3,
        "kerikil_m3": kerikil_m3,
        "berat_utama_kg": berat_utama_kg,
        "lonjor_utama": lonjor_utama,
        "total_sengkang": total_sengkang,
        "berat_sengkang_kg": berat_sengkang_kg,
        "lonjor_sengkang": lonjor_sengkang,
        "total_besi_kg": total_besi_kg,
    }


# ============================ DINDING ============================
KOEF_DINDING = {
    "merah":  {"pcs_m2": 70,   "semen_kg_m2": 9.68, "pasir_m3_m2": 0.045, "nama": "Bata Merah (5x11x22 cm)"},
    "batako": {"pcs_m2": 12.5, "semen_kg_m2": 3.26, "pasir_m3_m2": 0.015, "nama": "Batako (10x20x40 cm)"},
    "hebel":  {"pcs_m2": 8.3,  "mortar_kg_m2": 4,                          "nama": "Bata Ringan / Hebel (60x20 cm)"},
}


def calc_dinding(panjang, tinggi, bukaan, jenis):
    k = KOEF_DINDING[jenis]
    luas_bersih = max(0.0, panjang * tinggi - bukaan)
    jumlah_bata = luas_bersih * k["pcs_m2"]
    semen_kg = luas_bersih * k["semen_kg_m2"] if jenis != "hebel" else 0.0
    pasir_m3 = luas_bersih * k["pasir_m3_m2"] if jenis != "hebel" else 0.0
    mortar_kg = luas_bersih * k["mortar_kg_m2"] if jenis == "hebel" else 0.0
    return {
        "jenis": jenis, "nama_bata": k["nama"], "luas_bersih": luas_bersih,
        "jumlah_bata": jumlah_bata, "semen_kg": semen_kg,
        "pasir_m3": pasir_m3, "mortar_kg": mortar_kg,
    }


# ============================ PLESTERAN ============================
RATIO_PLESTER = {"1:4": (1, 4), "1:3": (1, 3)}
FAKTOR_PLESTER = 1.33


def calc_plesteran(luas, tebal_cm, jenis, acian):
    a, b = RATIO_PLESTER[jenis]
    volume = max(0.0, luas * (tebal_cm / 100))
    semen_plester_kg = volume * FAKTOR_PLESTER * (a / (a + b)) * 1400
    pasir_m3 = volume * FAKTOR_PLESTER * (b / (a + b))
    acian_kg = luas * 2.5 if acian else 0.0
    semen_kg = semen_plester_kg + acian_kg
    return {"volume": volume, "semen_kg": semen_kg, "pasir_m3": pasir_m3}


# ============================ LANTAI / KERAMIK ============================
SIZES_KERAMIK = {"30": (30, 30), "40": (40, 40), "50": (50, 50), "60": (60, 60), "80": (80, 80)}


def calc_lantai(luas, ukuran, custom_p, custom_l, isi_dus):
    if ukuran == "custom":
        p, l = custom_p, custom_l
    else:
        p, l = SIZES_KERAMIK[ukuran]
    # Bulatkan luas keping ke presisi wajar agar tidak terkena galat floating
    # point (mis. 0.6*0.6 = 0.35999... yang membuat ceil meleset +1 keping).
    luas_keping = round((p / 100) * (l / 100), 6)
    jumlah_keping = math.ceil(round((luas * 1.07) / luas_keping, 6)) if luas_keping > 0 else 0
    semen_instan_kg = luas * 5
    nat_kg = luas * 0.5
    jumlah_dus = math.ceil(jumlah_keping / isi_dus) if isi_dus > 0 else 0
    return {
        "jumlah_keping": jumlah_keping, "ukuran_label": f"{p}x{l} cm",
        "semen_instan_kg": semen_instan_kg, "nat_kg": nat_kg, "jumlah_dus": jumlah_dus,
    }


# ============================ ATAP ============================
KOEF_ATAP = {
    "keramik": {"pcs_m2": 22, "nama": "Genteng Keramik"},
    "beton":   {"pcs_m2": 11, "nama": "Genteng Beton"},
    "metal":   {"pcs_m2": 10, "nama": "Genteng Metal Berpasir"},
}


def calc_atap(luas, jenis, hitung_rangka):
    k = KOEF_ATAP[jenis]
    jumlah_genteng = math.ceil(luas * k["pcs_m2"] * 1.05)
    baja_ringan_batang = math.ceil((luas * 4.5) / 6) if hitung_rangka else 0
    return {"jumlah_genteng": jumlah_genteng, "nama_genteng": k["nama"],
            "baja_ringan_batang": baja_ringan_batang}


# ============================ PLAFON ============================
KOEF_PLAFON = {
    "gypsum": {"luas_lembar": 2.88, "nama": "Gypsum 9mm (120x240cm)"},
    "grc":    {"luas_lembar": 2.98, "nama": "GRC / Kalsiboard (122x244cm)"},
}


def calc_plafon(luas, keliling, jenis, drop, panjang_drop, lebar_drop_cm):
    k = KOEF_PLAFON[jenis]
    luas_drop_tambahan = panjang_drop * (lebar_drop_cm / 100) if drop else 0.0
    luas_efektif = luas + luas_drop_tambahan
    jumlah_lembar = math.ceil((luas_efektif * 1.05) / k["luas_lembar"])
    rangka_atas_batang = math.ceil((luas * 1.6) / 4)
    rangka_bawah_batang = math.ceil((luas * 2.0) / 4)
    dropan_batang = math.ceil((panjang_drop * 2.5) / 4) if drop else 0
    wall_angle_batang = math.ceil(keliling / 3)
    sekrup = math.ceil(luas_efektif * 17)
    return {
        "jumlah_lembar": jumlah_lembar, "nama_plafon": k["nama"],
        "rangka_atas_batang": rangka_atas_batang,
        "rangka_bawah_batang": rangka_bawah_batang,
        "dropan_batang": dropan_batang,
        "wall_angle_batang": wall_angle_batang, "sekrup": sekrup,
    }


# ============================ CAT ============================
def calc_cat(luas, lapis, daya_sebar, kemasan_liter):
    total_liter = (luas * lapis) / daya_sebar if daya_sebar > 0 else 0.0
    jumlah_kemasan = math.ceil(total_liter / kemasan_liter) if kemasan_liter > 0 else 0
    return {"total_liter": total_liter, "jumlah_kemasan": jumlah_kemasan,
            "kemasan": kemasan_liter}
