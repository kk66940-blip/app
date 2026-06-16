"""
utils/auth.py
Helper otentikasi terpusat.

Menggunakan library `bcrypt` secara langsung (BUKAN passlib). passlib 1.7.4
sudah tidak dipelihara dan rusak terhadap bcrypt >= 5.0 (error
"module 'bcrypt' has no attribute '__about__'"), jadi sengaja dihindari.

Mendukung verifikasi hash SHA-256 lama agar user lama tetap bisa login, lalu
otomatis di-upgrade ke bcrypt pada login berikutnya (rehash-on-login).

Catatan: bcrypt hanya memproses 72 byte pertama dari password. Kita encode ke
UTF-8 dan memotong ke 72 byte secara eksplisit agar konsisten dan tidak
melempar error pada password panjang.
"""

import hashlib

try:
    import bcrypt
    _HAS_BCRYPT = True
except ImportError:  # pragma: no cover
    _HAS_BCRYPT = False

_BCRYPT_MAX_BYTES = 72


def _to_bcrypt_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Hash password untuk disimpan. Pakai bcrypt bila tersedia."""
    if _HAS_BCRYPT:
        return bcrypt.hashpw(_to_bcrypt_bytes(password), bcrypt.gensalt()).decode("utf-8")
    # Fallback terakhir (tidak disarankan untuk produksi).
    return hashlib.sha256(password.encode()).hexdigest()


def _is_bcrypt_hash(stored: str) -> bool:
    return isinstance(stored, str) and stored.startswith(("$2a$", "$2b$", "$2y$"))


def verify_password(password: str, stored_hash: str) -> bool:
    """Verifikasi password terhadap hash tersimpan (bcrypt ATAU sha256 lama)."""
    if not stored_hash:
        return False
    if _is_bcrypt_hash(stored_hash):
        if not _HAS_BCRYPT:
            return False
        try:
            return bcrypt.checkpw(
                _to_bcrypt_bytes(password), stored_hash.encode("utf-8")
            )
        except (ValueError, TypeError):
            return False
    # Hash SHA-256 lama (legacy).
    legacy = hashlib.sha256(password.encode()).hexdigest()
    return legacy == stored_hash


def needs_rehash(stored_hash: str) -> bool:
    """True jika hash tersimpan masih format lama dan perlu di-upgrade."""
    return _HAS_BCRYPT and not _is_bcrypt_hash(stored_hash or "")


def authenticate(supabase, username: str, password: str):
    """Cari user dan verifikasi password.

    Mengembalikan dict user jika sukses, atau None jika gagal.
    Jika login sukses dengan hash lama, otomatis upgrade ke bcrypt.
    """
    if not username or not password:
        return None

    res = (
        supabase.table("users")
        .select("*")
        .eq("username", username)
        .execute()
        .data
    )
    if not res:
        return None

    user = res[0]
    stored = user.get("password_hash") or user.get("password")
    if not verify_password(password, stored or ""):
        return None

    # Rehash-on-login: upgrade hash lama ke bcrypt secara transparan.
    if needs_rehash(stored):
        try:
            new_hash = hash_password(password)
            update = {}
            if "password_hash" in user:
                update["password_hash"] = new_hash
            else:
                update["password"] = new_hash
            supabase.table("users").update(update).eq("id", user["id"]).execute()
        except Exception:
            # Upgrade gagal tidak boleh menggagalkan login.
            pass

    return user
