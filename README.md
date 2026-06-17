# 🏗️ RAB & Opname Online

**Sistem Manajemen Anggaran & Progres Konstruksi Berbasis Web (Streamlit)**

Aplikasi untuk pengelolaan **RAB** (Rencana Anggaran Biaya), **Opname**, **RAP**
(Rencana Anggaran Pelaksanaan), **AHSP**, **SPK**, dan **Pengeluaran Proyek**.

---

## ✨ Fitur

- Manajemen multi-proyek (PPN & Retensi per proyek)
- RAB hirarkis (Main → Sub → Detail) + import/export Excel & PDF
- Opname & Opname Sub (RAB vs RAP) + upload foto bukti
- RAP otomatis dari RAB dengan persentase yang bisa diatur
- Database AHSP (Material + Upah + Peralatan + komposisi dinamis)
- SPK dengan output PDF
- Pengeluaran proyek per kategori + export
- Dashboard analitik + progress hirarkis
- Invoice otomatis per periode Opname

---

## 🚀 Cara Menjalankan

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Buat `.streamlit/secrets.toml`:

```toml
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOi..."
```

> Format `[supabase]` section juga didukung; lihat `utils/supabase_client.py`.

Jalankan:

```bash
streamlit run app.py
```

---

## 🔐 Login & User Management

Otentikasi memakai tabel `users` custom. Password di-hash dengan **bcrypt**
(`utils/auth.py`). Hash SHA-256 lama tetap bisa login dan akan **otomatis
di-upgrade ke bcrypt saat login berikutnya** (rehash-on-login) — tidak perlu
reset massal.

Tabel `users` sebaiknya punya kolom `password_hash`. Jika datamu masih memakai
kolom `password`, kode tetap membacanya, tapi disarankan migrasi ke
`password_hash`.

Buat user baru / reset password:

```bash
python scripts/create_user.py      # edit USERNAME & PASSWORD di file dulu
python scripts/update_password.py  # edit NEW_PASSWORD di file dulu
```

---

## ⚠️ Catatan Keamanan (PENTING — belum selesai)

Aplikasi ini memakai **SUPABASE_SERVICE_ROLE_KEY**, yang **mem-bypass seluruh
Row Level Security (RLS)**. Konsekuensinya:

- Otorisasi sepenuhnya bergantung pada kode aplikasi, bukan database. Setiap
  user yang berhasil login secara teknis bisa mengakses data semua proyek.
- Key ini tidak boleh bocor ke sisi klien.

**Rekomendasi produksi (belum dikerjakan):** migrasi ke **Supabase Auth + anon
key + RLS** agar database yang menegakkan otorisasi. Ini perubahan arsitektur
yang perlu keputusan & desain skema, sehingga sengaja tidak dilakukan di pass
perbaikan ini.

---

## 🛠️ Perubahan pada Pass Perbaikan Ini

Yang **sudah** diperbaiki dan terverifikasi (lolos `py_compile`):

- **Bug crash:** `export_hierarchical_pdf` mengembalikan `None` (salah
  indentasi `return`) — semua export PDF RAB & RAP gagal. Diperbaiki.
- **Bug crash:** mismatch signature callback Opname (tree memanggil 4 argumen,
  handler hanya 3) → `TypeError` saat simpan opname. Diperbaiki.
- **Bug crash:** `st.set_page_config` dipanggil ulang di `0_Projects.py` &
  `6_AHSP.py` (sudah dipanggil di `app.py`). Dihapus.
- **Keamanan:** hashing password dipindah ke `utils/auth.py` (bcrypt + fallback
  legacy + rehash-on-login). `create_user.py` tidak lagi menyimpan plaintext.
- **Keamanan:** pesan error login dibuat generik; script debug tidak lagi
  membocorkan hash password.
- **Cleanup:** fungsi mati 130 baris di `2_RAB.py`, file duplikat di `app/`,
  `rxconfig.py`, import ganda, subheader dobel, pesan sukses sisa debugging.
- **requirements.txt:** tambah `passlib[bcrypt]`, hapus `st-supabase-connection`
  yang tidak dipakai.
- **Koneksi Supabase** sekarang di-cache (`@st.cache_resource`).
- **SPK number** auto-increment (sebelumnya hardcoded `/001` → bentrok).

Perbaikan pada audit lanjutan:

- **Import RAB di Laporan** tidak lagi menelan error diam-diam (`except: pass`);
  baris yang gagal kini dilaporkan ke user.
- **Export Excel RAP** sebelumnya flat (tidak berhirarki) karena tidak meneruskan
  `id_key="rab_item_id"`; sudah diperbaiki agar konsisten dengan export PDF RAP.

Yang **BELUM** dikerjakan / perlu perhatianmu:

- [ ] Migrasi ke Supabase Auth + RLS (lihat Catatan Keamanan di atas).
- [ ] **KANDIDAT BUG-DIAM (perlu cek vs schema):** kode opname mengasumsikan
  `opname_details.rab_item_id == rab_items.id`. Bila tidak, volume opname tak
  akan muncul. Verifikasi terhadap schema-mu.
- [ ] **KANDIDAT BUG-DIAM:** modul AHSP bergantung pada RPC `calculate_ahsp_unit_price`,
  `update_ahsp_unit_price`, `get_ahsp_price_breakdown` (param `p_ahsp_item_id`)
  dan view `v_ahsp_items`. Jika tidak ada / beda nama param di DB, modul AHSP gagal.
- [ ] Import RAB lewat Laporan selalu set `parent_id=None` → hasil import flat
  (tanpa hirarki). Perlu disatukan dengan logika import berhirarki di 2_RAB.py.
- [ ] Heuristik "Main Item" masih rapuh:
  `volume == 0 and "pekerjaan" in description.lower()`. Disarankan menambah
  kolom boolean `is_main_item` di DB agar konsisten. Butuh perubahan skema.
- [ ] Dua jalur import RAB berbeda (`2_RAB.py` pakai `header=3`; `5_Laporan.py`
  pakai header default dan **tidak men-set `parent_id`** sehingga hasil import
  jadi flat). Sebaiknya disatukan ke satu helper.
- [ ] `utils/excel_utils.py` masih ada tapi praktis tidak dipakai (legacy).
- [ ] Belum ada test otomatis & belum diverifikasi berjalan end-to-end terhadap
  database sungguhan (tidak ada skema/secret saat perbaikan dilakukan).

---

## 📁 Struktur

```
app.py                    # Entry point + login + navigation
requirements.txt
utils/
  supabase_client.py      # Koneksi Supabase (cached)
  auth.py                 # Hashing & verifikasi password (bcrypt)
  helpers.py              # format_rupiah, parse_rupiah
  ahsp_helper.py          # Business logic AHSP
  export_utils.py         # Export hirarkis terpusat (Excel + PDF)
  excel_utils.py          # Legacy (kandidat dihapus)
components/
  hierarchical_tree.py    # Komponen tree reusable
pages/
  0_Projects.py ... 8_SPK.py
scripts/                  # Utilitas/debug (bukan bagian runtime app)
```

---

Internal project — manajemen proyek konstruksi.
