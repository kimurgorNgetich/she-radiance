"""backend/config.py — SR-005a: shared secret resolution for cloud + local deploy.

Resolution order: 1) st.secrets non-empty value, 2) os.environ, 3) .env
(loaded into os.environ via python-dotenv). Empty values fall through.
Safe to import outside Streamlit — st.secrets access is wrapped in try/except.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

def get_secret(key: str, default=None):
    try:
        import streamlit as st
        val = st.secrets.get(key)
        if val:
            return val
    except Exception:
        pass
    val = os.environ.get(key)
    if val:
        return val
    return default