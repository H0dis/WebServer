"""
models/auth.py
--------------
Gestioneaza sesiunile de autentificare.
Simplu: un set de tokeni in memorie.
"""

import secrets
import threading
from config import PASSWORD

_sessions: set[str] = set()
_lock = threading.Lock()


def create_session() -> str:
    """Creeaza un token nou si il salveaza. Returneaza tokenul."""
    token = secrets.token_hex(24)
    with _lock:
        _sessions.add(token)
    return token


def is_valid_token(token: str) -> bool:
    """Verifica daca tokenul exista in sesiuni active."""
    with _lock:
        return token in _sessions


def check_password(password: str) -> bool:
    """Compara parola primita cu cea configurata."""
    # Daca nu e setata parola, oricine poate intra
    if not PASSWORD:
        return True
    return password == PASSWORD


def extract_token_from_cookie(cookie_header: str) -> str:
    """Extrage tokenul ls_token din header-ul Cookie."""
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith("ls_token="):
            return part[len("ls_token="):]
    return ""
