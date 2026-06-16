"""
scripts/update_password.py
Reset / update password user dengan hash bcrypt.

Jalankan dari root project:
    python scripts/update_password.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.supabase_client import get_supabase
from utils.auth import hash_password

# ── EDIT NILAI INI ──────────────────────────────────────────
NEW_PASSWORD = "ganti_password_ini"
USERS_TO_UPDATE = ["admin"]
# ────────────────────────────────────────────────────────────


def main():
    if NEW_PASSWORD == "ganti_password_ini":
        print("⚠️  Ganti dulu nilai NEW_PASSWORD sebelum menjalankan.")
        return

    supabase = get_supabase()
    new_hash = hash_password(NEW_PASSWORD)

    for username in USERS_TO_UPDATE:
        res = (
            supabase.table("users")
            .update({"password_hash": new_hash})
            .eq("username", username)
            .execute()
        )
        status = "✅" if res.data else "❌"
        print(f"{status} Password '{username}'")


if __name__ == "__main__":
    main()
