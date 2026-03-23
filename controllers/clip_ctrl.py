"""
controllers/clip_ctrl.py
------------------------
Clipboard sync intre PC si telefon.
Fix: orice schimbare (inclusiv stergere) face push SSE imediat.
"""

import json
from models.clipboard import get_clipboard, set_clipboard, clear_clipboard
import sse


def handle_get_clipboard(handler) -> None:
    """GET /api/clipboard — returneaza starea curenta."""
    state = get_clipboard()
    handler.send_json(state)


def handle_set_clipboard(handler) -> None:
    """
    POST /api/clipboard
    Body: { text: "..." }
    Seteaza textul si face broadcast SSE tuturor clientilor.
    """
    length = int(handler.headers.get("Content-Length", 0))
    body = json.loads(handler.rfile.read(length))
    text = body.get("text", "")

    new_state = set_clipboard(text)
    # Trimite noua stare la toti clientii (PC + telefon)
    sse.broadcast("clipboard", json.dumps(new_state))
    handler.send_json({"ok": True})


def handle_clear_clipboard(handler) -> None:
    """
    POST /api/clipboard/clear
    Reseteaza clipboardul la gol si face broadcast SSE.
    """
    new_state = clear_clipboard()
    sse.broadcast("clipboard", json.dumps(new_state))
    handler.send_json({"ok": True})
