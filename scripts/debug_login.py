"""
scripts/debug_login.py
Utilitas debug: cek isi tabel users (tanpa membocorkan hash penuh).
Jalankan: python scripts/debug_login.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.supabase_client import get_supabase


def main():
    supabase = get_supabase()
    res = supabase.table("users").select("username, full_name, role").execute()
    if not res.data:
        print("❌ Tabel users kosong atau tidak ditemukan.")
        return
    print("Daftar user:")
    for u in res.data:
        print(f"  • {u.get('username')} | {u.get('full_name')} | role={u.get('role')}")


if __name__ == "__main__":
    main()
