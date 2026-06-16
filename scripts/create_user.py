"""
scripts/create_user.py
Buat user baru dengan password ter-hash (bcrypt).

Jalankan dari root project:
    python scripts/create_user.py

Catatan: script ini perlu akses st.secrets, jadi jalankan lewat Streamlit
context atau set environment yang sesuai. Untuk pemakaian cepat, edit nilai
USERNAME / PASSWORD di bawah lalu jalankan.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.supabase_client import get_supabase
from utils.auth import hash_password

# ── EDIT NILAI INI ──────────────────────────────────────────
USERNAME = "admin"
PASSWORD = "ganti_password_ini"   # WAJIB ganti sebelum dipakai
FULL_NAME = "Administrator"
ROLE = "admin"
# ────────────────────────────────────────────────────────────


def main():
    if PASSWORD == "ganti_password_ini":
        print("⚠️  Ganti dulu nilai PASSWORD di script ini sebelum menjalankan.")
        return

    supabase = get_supabase()
    data = {
        "username": USERNAME,
        "password_hash": hash_password(PASSWORD),
        "full_name": FULL_NAME,
        "role": ROLE,
    }
    res = supabase.table("users").insert(data).execute()
    if res.data:
        print(f"✅ User '{USERNAME}' berhasil dibuat (password ter-hash bcrypt).")
    else:
        print("❌ Gagal membuat user.")


if __name__ == "__main__":
    main()
