"""
models/clipboard.py
-------------------
Starea clipboardului sincronizat intre PC si telefon.
Un singur text la un moment dat, cu timestamp.
"""

import time
import threading

# Starea curenta a clipboardului
_state = {"text": "", "ts": 0}
_lock = threading.Lock()


def get_clipboard() -> dict:
    """Returneaza starea curenta a clipboardului."""
    with _lock:
        return dict(_state)


def set_clipboard(text: str) -> dict:
    """
    Seteaza textul clipboardului si actualizeaza timestamp-ul.
    Returneaza noua stare (pentru SSE broadcast).
    """
    with _lock:
        _state["text"] = text
        _state["ts"] = int(time.time())
        return dict(_state)


def clear_clipboard() -> dict:
    """Reseteaza clipboardul la gol. Returneaza starea noua."""
    return set_clipboard("")
