def format_rupiah(value):
    if value is None:
        value = 0
    return f"Rp {float(value):,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")

def parse_rupiah(text):
    if not text:
        return 0.0
    text = text.replace("Rp", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(text)
    except:
        return 0.0

def next_rab_code(all_items, parent_id, level):
    """Hasilkan kode RAB berikutnya secara otomatis.

    Skema:
      - Main item (parent_id None): A.1, A.2, A.3, ... (huruf 'A' tetap, angka naik)
      - Sub item: kode induk + '.' + nomor urut berikutnya di dalam induk itu
        (mis. induk A.1 -> A.1.1, A.1.2; induk A.1.1 -> A.1.1.1, ...)

    Parameters
    ----------
    all_items : list[dict]  semua rab_items proyek (punya 'code','parent_id','id').
    parent_id : int | None  id induk; None untuk main item.
    level     : int         level item (untuk fallback).

    Mengembalikan string kode. Aman bila data kosong.
    """
    def _last_number(code):
        """Ambil angka terakhir dari kode seperti 'A.1.2' -> 2; gagal -> 0."""
        if not code:
            return 0
        tail = str(code).strip().split(".")[-1]
        try:
            return int(tail)
        except (ValueError, TypeError):
            return 0

    if parent_id is None:
        # Main item: cari kode main (parent_id None) dengan prefix 'A.'
        mains = [it for it in all_items if it.get("parent_id") is None]
        max_n = 0
        for it in mains:
            code = str(it.get("code", "") or "")
            # hanya hitung yang berpola 'A.<angka>'
            if code.upper().startswith("A.") and code.count(".") == 1:
                max_n = max(max_n, _last_number(code))
        return f"A.{max_n + 1}"

    # Sub item: temukan kode induk, lalu cari nomor terbesar di antara saudara
    parent = next((it for it in all_items if it.get("id") == parent_id), None)
    parent_code = str(parent.get("code", "")).strip() if parent else ""

    siblings = [it for it in all_items if it.get("parent_id") == parent_id]
    max_n = 0
    for sib in siblings:
        max_n = max(max_n, _last_number(sib.get("code", "")))

    if parent_code:
        return f"{parent_code}.{max_n + 1}"
    # Fallback bila induk tak punya kode: pakai level
    return f"{max_n + 1}"


# ==================== KALKULATOR VOLUME (BOQ) ====================
# Jenis perhitungan volume yang didukung untuk input dimensi RAB.
VOLUME_CALC_TYPES = {
    "volume": {"label": "Volume (P×L×T)", "fields": ["panjang", "lebar", "tinggi"], "unit_hint": "m³"},
    "luas":   {"label": "Luas (P×L)",     "fields": ["panjang", "lebar"],           "unit_hint": "m²"},
    "panjang":{"label": "Panjang (m')",   "fields": ["panjang"],                    "unit_hint": "m'"},
    "besi":   {"label": "Besi (panjang × kg/m)", "fields": ["panjang", "berat_per_m"], "unit_hint": "kg"},
    "unit":   {"label": "Jumlah/Unit",    "fields": ["jumlah"],                     "unit_hint": "bh"},
}


def calc_segment_result(calc_type: str, seg: dict) -> float:
    """Hitung hasil satu segmen berdasarkan jenis perhitungan.

    seg berisi key seperti panjang/lebar/tinggi/berat_per_m/jumlah (angka).
    'jumlah' (multiplier) berlaku untuk semua tipe; default 1 bila tak ada.
    """
    def g(k):
        try:
            return float(seg.get(k) or 0)
        except (ValueError, TypeError):
            return 0.0

    mult = g("jumlah") if seg.get("jumlah") not in (None, "") else 1.0
    if mult == 0:
        mult = 1.0

    if calc_type == "volume":
        base = g("panjang") * g("lebar") * g("tinggi")
    elif calc_type == "luas":
        base = g("panjang") * g("lebar")
    elif calc_type == "panjang":
        base = g("panjang")
    elif calc_type == "besi":
        base = g("panjang") * g("berat_per_m")
    elif calc_type == "unit":
        # untuk unit, 'jumlah' ADALAH nilainya, bukan multiplier
        return g("jumlah")
    else:
        base = 0.0
    return base * mult


def calc_total_volume(segments: list) -> float:
    """Jumlahkan hasil semua segmen. Tiap segmen punya 'tipe' & dimensinya."""
    if not segments:
        return 0.0
    total = 0.0
    for seg in segments:
        total += calc_segment_result(seg.get("tipe", "volume"), seg)
    return round(total, 4)


# ==================== BOBOT PEKERJAAN (%) ====================
def compute_rab_weights(items: list) -> dict:
    """Hitung bobot tiap item RAB = (nilai item / grand total) * 100.

    Untuk item DAUN (tanpa anak): bobot = nilai sendiri / grand total.
    Untuk item GRUP (punya anak, mis. main item): bobot = jumlah bobot semua
    anaknya (rollup rekursif), sehingga main item menampilkan total bobot dari
    seluruh sub-item di bawahnya. Total bobot semua main item = 100%.

    Grand total = jumlah nilai item daun. Bila 0 -> semua bobot 0.
    """
    def _val(it):
        return (it.get("volume", 0) or 0) * (it.get("unit_price", 0) or 0)

    # Peta anak per parent_id
    children = {}
    for it in items:
        children.setdefault(it.get("parent_id"), []).append(it)

    def _is_leaf(it):
        return not children.get(it.get("id"))

    grand = sum(_val(it) for it in items if _is_leaf(it))
    if grand <= 0:
        return {it.get("id"): 0.0 for it in items}

    weights = {}

    def _calc(it):
        """Kembalikan bobot item; rekursif menjumlahkan anak untuk item grup."""
        iid = it.get("id")
        kids = children.get(iid, [])
        if not kids:
            w = _val(it) / grand * 100.0
        else:
            w = sum(_calc(child) for child in kids)
        weights[iid] = w
        return w

    # Mulai dari root (parent_id None) agar seluruh pohon terhitung
    for root in children.get(None, []):
        _calc(root)

    # Pastikan semua item punya entry (mis. item yatim yg parent-nya tak ada)
    for it in items:
        if it.get("id") not in weights:
            weights[it.get("id")] = (_val(it) / grand * 100.0) if _is_leaf(it) else 0.0

    return weights


# ==================== KURVA-S (PROGRES RENCANA vs REALISASI) ====================
def compute_scurve_actual(rab_items: list, periods: list, opname_by_period: dict) -> list:
    """Hitung realisasi KUMULATIF (%) per periode opname, berbasis NILAI.

    Opname disimpan per-periode (increment), jadi progres kumulatif pada periode
    ke-N = jumlah nilai opname periode 1..N. Progres nilai item =
    volume × harga; dibagi grand total RAB × 100.
    """
    price_map = {it.get("id"): (it.get("unit_price", 0) or 0) for it in rab_items}
    grand = sum((it.get("volume", 0) or 0) * (it.get("unit_price", 0) or 0) for it in rab_items)

    out = []
    if grand <= 0:
        return out

    periods_sorted = sorted(periods, key=lambda p: (p.get("period_no") or 0, p.get("opname_date") or ""))

    cumulative_nilai = 0.0
    for p in periods_sorted:
        pid = p.get("id")
        vols = opname_by_period.get(pid, {})
        nilai_periode = sum((vols.get(iid, 0) or 0) * price_map.get(iid, 0) for iid in vols)
        cumulative_nilai += nilai_periode
        pct = cumulative_nilai / grand * 100.0
        out.append({
            "date": p.get("opname_date"),
            "period_no": p.get("period_no"),
            "actual_pct": round(pct, 2),
        })
    return out


def compute_scurve_plan_linear(start_date, end_date, n_points: int = 12) -> list:
    """Garis rencana LINEAR 0%→100% antara start_date dan end_date.

    Mengembalikan list {"date", "plan_pct"}. n_points titik merata.
    Catatan: ini baseline disederhanakan (garis lurus), bukan jadwal nyata.
    """
    from datetime import date, datetime, timedelta

    def _to_date(d):
        if isinstance(d, date):
            return d
        if isinstance(d, str):
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
                try:
                    return datetime.strptime(d[:10], fmt).date()
                except ValueError:
                    continue
        return None

    s, e = _to_date(start_date), _to_date(end_date)
    if not s or not e or e <= s:
        return []

    total_days = (e - s).days
    out = []
    for i in range(n_points + 1):
        frac = i / n_points
        d = s + timedelta(days=round(total_days * frac))
        out.append({"date": d.isoformat(), "plan_pct": round(frac * 100.0, 2)})
    return out


def compute_rab_totals(items: list) -> dict:
    """Hitung total tiap item RAB dengan rollup.

    Item DAUN: total = volume * unit_price.
    Item GRUP (punya anak): total = jumlah total anak-anaknya (rekursif).

    Mengembalikan dict {item_id: total_rupiah}.
    """
    children = {}
    for it in items:
        children.setdefault(it.get("parent_id"), []).append(it)

    totals = {}

    def _calc(it):
        iid = it.get("id")
        kids = children.get(iid, [])
        if not kids:
            t = (it.get("volume", 0) or 0) * (it.get("unit_price", 0) or 0)
        else:
            t = sum(_calc(c) for c in kids)
        totals[iid] = t
        return t

    for root in children.get(None, []):
        _calc(root)

    # Item yatim (parent tak dikenal) tetap dapat entry
    for it in items:
        if it.get("id") not in totals:
            kids = children.get(it.get("id"), [])
            totals[it.get("id")] = sum(_calc(c) for c in kids) if kids else \
                (it.get("volume", 0) or 0) * (it.get("unit_price", 0) or 0)

    return totals


# ==================== REKAP LINTAS PROYEK ====================
def compute_project_recap(project_id, rab_items, opname_details, expenses, payments=None):
    """Hitung ringkasan satu proyek untuk rekap.

    Parameters
    ----------
    project_id      : id proyek.
    rab_items       : list rab_items proyek ini.
    opname_details  : list opname_details proyek ini (SEMUA periode).
    expenses        : list project_expenses proyek ini.
    payments        : list project_payments proyek ini (uang masuk riil dari
                      klien). Bila None, uang_masuk = 0.

    Returns dict termasuk: nilai_rab_total, total_opname (nilai tertagih),
    uang_masuk (kas riil), total_pengeluaran, piutang (tertagih - uang_masuk),
    margin (uang_masuk - pengeluaran), sisa_penagihan, laba_kasar.

    Catatan: total_opname menjumlahkan SEMUA periode (opname per-periode).
    'uang_masuk' adalah pembayaran klien yang BENAR-BENAR tercatat (bukan opname).
    """
    children = {}
    for it in rab_items:
        children.setdefault(it.get("parent_id"), []).append(it)

    def _is_leaf(it):
        return not children.get(it.get("id"))

    def _val(it):
        return (it.get("volume", 0) or 0) * (it.get("unit_price", 0) or 0)

    nilai_rab_asli = sum(_val(it) for it in rab_items if _is_leaf(it) and not it.get("is_addendum"))
    nilai_adendum = sum(_val(it) for it in rab_items if _is_leaf(it) and it.get("is_addendum"))
    nilai_rab_total = nilai_rab_asli + nilai_adendum

    price_map = {it.get("id"): (it.get("unit_price", 0) or 0) for it in rab_items}

    total_opname = 0.0
    for d in opname_details:
        rid = d.get("rab_item_id")
        total_opname += (d.get("actual_volume", 0) or 0) * price_map.get(rid, 0)

    total_pengeluaran = sum((e.get("amount", 0) or 0) for e in expenses)
    uang_masuk = sum((p.get("amount", 0) or 0) for p in (payments or []))

    progres_pct = (total_opname / nilai_rab_total * 100.0) if nilai_rab_total > 0 else 0.0
    sisa_penagihan = nilai_rab_total - total_opname        # nilai kontrak belum diopname
    piutang = total_opname - uang_masuk                    # sudah ditagih, belum dibayar
    margin = uang_masuk - total_pengeluaran                # untung KAS riil
    laba_kasar = total_opname - total_pengeluaran          # untung atas dasar tertagih

    return {
        "project_id": project_id,
        "nilai_rab_asli": nilai_rab_asli,
        "nilai_adendum": nilai_adendum,
        "nilai_rab_total": nilai_rab_total,
        "total_opname": total_opname,
        "uang_masuk": uang_masuk,
        "progres_pct": round(progres_pct, 2),
        "total_pengeluaran": total_pengeluaran,
        "sisa_penagihan": sisa_penagihan,
        "piutang": piutang,
        "margin": margin,
        "laba_kasar": laba_kasar,
    }
