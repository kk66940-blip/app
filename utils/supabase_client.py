"""
utils/supabase_client.py
Koneksi Supabase terpusat dengan caching.

CATATAN KEAMANAN PENTING:
- Aplikasi ini menggunakan SERVICE_ROLE_KEY yang mem-bypass seluruh Row Level
  Security (RLS) Supabase. Itu berarti otorisasi SEPENUHNYA bergantung pada
  logika di dalam aplikasi ini, bukan pada database. Jangan pernah mengekspos
  key ini ke sisi browser/klien.
- Untuk produksi, sangat disarankan migrasi ke Supabase Auth + anon key + RLS,
  sehingga database yang menegakkan otorisasi, bukan kode aplikasi.
"""

from functools import lru_cache

import streamlit as st
from supabase import create_client, Client


def _read_secret(*names: str) -> str:
    """Ambil secret pertama yang tersedia dari beberapa nama alternatif."""
    for name in names:
        if name in st.secrets:
            return st.secrets[name]
        # Dukung format [supabase] section
        if "supabase" in st.secrets and name in st.secrets["supabase"]:
            return st.secrets["supabase"][name]
    raise KeyError(
        f"Secret tidak ditemukan. Set salah satu dari: {names} "
        f"di .streamlit/secrets.toml"
    )


@st.cache_resource
def get_supabase() -> Client:
    """Kembalikan satu Client Supabase yang di-cache untuk seluruh sesi.

    Menggunakan @st.cache_resource agar tidak membuat koneksi baru pada setiap
    interaksi halaman.
    """
    url = _read_secret("SUPABASE_URL")
    key = _read_secret("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_KEY")
    return create_client(url, key)
