"""
utils/material_coeffs.py
Koefisien kebutuhan material untuk Kalkulator Material (Mode A - rumus SNI).

================================ PERINGATAN PENTING ================================
Angka-angka di bawah adalah DEFAULT yang dikumpulkan dari rujukan publik yang
mengutip SNI (SNI 7394:2008 untuk beton, SNI 6897:2008 untuk pasangan/plesteran,
SNI 2835/2008 untuk tanah). SUMBER PUBLIK SERING TIDAK SERAGAM — koefisien yang
sama bisa berbeda antar sumber (mis. semen pasangan bata 1:4 muncul sebagai
9,6 / 9,68 / 14,37 kg/m2 di sumber berbeda).

JANGAN gunakan angka ini untuk order/anggaran final tanpa memverifikasi terhadap
dokumen SNI/AHSP PUPR resmi yang berlaku untuk proyekmu. Di UI, semua koefisien
ini DAPAT DIEDIT, jadi timpa dengan koefisien resmi/perusahaanmu bila berbeda.
====================================================================================

Struktur:
- Tiap "pekerjaan" punya satuan volume (m3 / m2), sumber, dan daftar material.
- Tiap material: koefisien per-satuan-volume, satuan SNI (kg/m3/buah), dan info
  konversi opsional ke "satuan beli" (mis. semen kg -> sak).
"""

# Berat 1 sak semen (kg). Umum: 40 atau 50 kg. Default 50, bisa diubah di UI.
SAK_SEMEN_KG_DEFAULT = 50.0

# Definisi koefisien. coeff = jumlah material per 1 satuan volume pekerjaan.
# buy_unit / buy_factor: untuk konversi ke satuan beli (nilai_kg / buy_factor),
#   atau None jika material sudah dalam satuan beli (mis. bata = buah).
MATERIAL_COEFFS = {
    # ---------------- BETON ----------------
    "Beton K-225 (1 m3)": {
        "volume_unit": "m3",
        "source": "SNI 7394:2008",
        "materials": [
            {"name": "Semen (PC)",   "coeff": 371.0,  "unit": "kg",  "buy_unit": "sak", "buy_by": "sak_semen"},
            {"name": "Pasir beton",  "coeff": 698.0,  "unit": "kg",  "buy_unit": "m3",  "buy_factor": 1400.0},
            {"name": "Kerikil/split","coeff": 1047.0, "unit": "kg",  "buy_unit": "m3",  "buy_factor": 1350.0},
            {"name": "Air",          "coeff": 215.0,  "unit": "liter","buy_unit": None},
        ],
    },
    "Beton K-300 (1 m3)": {
        "volume_unit": "m3",
        "source": "SNI 7394:2008",
        "materials": [
            {"name": "Semen (PC)",   "coeff": 413.0,  "unit": "kg",  "buy_unit": "sak", "buy_by": "sak_semen"},
            {"name": "Pasir beton",  "coeff": 681.0,  "unit": "kg",  "buy_unit": "m3",  "buy_factor": 1400.0},
            {"name": "Kerikil/split","coeff": 1021.0, "unit": "kg",  "buy_unit": "m3",  "buy_factor": 1350.0},
            {"name": "Air",          "coeff": 215.0,  "unit": "liter","buy_unit": None},
        ],
    },
    # ---------------- PASANGAN BATA ----------------
    "Pasangan bata merah 1/2 bata, camp 1:4 (1 m2)": {
        "volume_unit": "m2",
        "source": "SNI 6897:2008 (verifikasi: 9,6-14,37 kg semen antar sumber)",
        "materials": [
            {"name": "Bata merah",   "coeff": 70.0,   "unit": "buah", "buy_unit": None},
            {"name": "Semen (PC)",   "coeff": 9.68,   "unit": "kg",   "buy_unit": "sak", "buy_by": "sak_semen"},
            {"name": "Pasir pasang", "coeff": 0.045,  "unit": "m3",   "buy_unit": "m3",  "buy_factor": 1.0},
        ],
    },
    "Pasangan bata merah 1/2 bata, camp 1:6 (1 m2)": {
        "volume_unit": "m2",
        "source": "SNI 6897:2008",
        "materials": [
            {"name": "Bata merah",   "coeff": 70.0,   "unit": "buah", "buy_unit": None},
            {"name": "Semen (PC)",   "coeff": 7.3,    "unit": "kg",   "buy_unit": "sak", "buy_by": "sak_semen"},
            {"name": "Pasir pasang", "coeff": 0.05,   "unit": "m3",   "buy_unit": "m3",  "buy_factor": 1.0},
        ],
    },
    "Pasangan batako (1 m2)": {
        "volume_unit": "m2",
        "source": "Rujukan umum (verifikasi)",
        "materials": [
            {"name": "Batako",       "coeff": 12.5,   "unit": "buah", "buy_unit": None},
            {"name": "Semen (PC)",   "coeff": 6.0,    "unit": "kg",   "buy_unit": "sak", "buy_by": "sak_semen"},
            {"name": "Pasir pasang", "coeff": 0.03,   "unit": "m3",   "buy_unit": "m3",  "buy_factor": 1.0},
        ],
    },
    # ---------------- PLESTERAN & ACIAN ----------------
    "Plesteran camp 1:4, tebal 15 mm (1 m2)": {
        "volume_unit": "m2",
        "source": "SNI 6897:2008 (verifikasi)",
        "materials": [
            {"name": "Semen (PC)",   "coeff": 6.24,   "unit": "kg",   "buy_unit": "sak", "buy_by": "sak_semen"},
            {"name": "Pasir pasang", "coeff": 0.024,  "unit": "m3",   "buy_unit": "m3",  "buy_factor": 1.0},
        ],
    },
    "Acian (1 m2)": {
        "volume_unit": "m2",
        "source": "SNI 6897:2008 (verifikasi)",
        "materials": [
            {"name": "Semen (PC)",   "coeff": 3.25,   "unit": "kg",   "buy_unit": "sak", "buy_by": "sak_semen"},
        ],
    },
    # ---------------- TANAH ----------------
    "Galian tanah biasa (1 m3)": {
        "volume_unit": "m3",
        "source": "SNI 2835:2008 (umumnya tanpa material, hanya tenaga)",
        "materials": [],
    },
    "Urugan pasir (1 m3)": {
        "volume_unit": "m3",
        "source": "SNI (verifikasi); faktor gembur ~1,2",
        "materials": [
            {"name": "Pasir urug",   "coeff": 1.2,    "unit": "m3",   "buy_unit": "m3",  "buy_factor": 1.0},
        ],
    },
}


def convert_to_buy_unit(material: dict, total_kg_or_native: float, sak_semen_kg: float):
    """Konversi hasil ke satuan beli.

    Mengembalikan (nilai_beli, satuan_beli) atau (None, None) bila tak ada konversi.
    - buy_by == 'sak_semen': bagi dengan berat sak (kg -> sak)
    - buy_factor ada: bagi dengan faktor (kg -> m3 via berat isi, atau m3 -> m3 = 1)
    """
    buy_unit = material.get("buy_unit")
    if not buy_unit:
        return None, None
    if material.get("buy_by") == "sak_semen":
        return total_kg_or_native / sak_semen_kg, "sak"
    factor = material.get("buy_factor")
    if factor:
        return total_kg_or_native / factor, buy_unit
    return None, None
