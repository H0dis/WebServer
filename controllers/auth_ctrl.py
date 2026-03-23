"""
controllers/auth_ctrl.py
------------------------
Logica de autentificare: login, logout, verificare acces.
"""

import json
from models.auth import check_password, create_session, is_valid_token, extract_token_from_cookie
from config import PASSWORD


def get_token(handler) -> str:
    """Extrage tokenul din cookie-ul request-ului."""
    cookie = handler.headers.get("Cookie", "")
    return extract_token_from_cookie(cookie)


def is_authenticated(handler) -> bool:
    """Verifica daca request-ul curent e autentificat."""
    if not PASSWORD:
        return True
    return is_valid_token(get_token(handler))


def handle_login(handler) -> None:
    """
    POST /api/login
    Primeste JSON cu { password }, verifica si seteaza cookie daca e ok.
    """
    length = int(handler.headers.get("Content-Length", 0))
    body = json.loads(handler.rfile.read(length))
    password = body.get("password", "")

    if check_password(password):
        token = create_session()
        handler.send_response(200)
        handler.send_header("Content-Type", "application/json")
        handler.send_header(
            "Set-Cookie",
            f"ls_token={token}; Path=/; HttpOnly; SameSite=Strict"
        )
        handler.end_headers()
        handler.wfile.write(json.dumps({"ok": True}).encode())
    else:
        handler.send_response(200)
        handler.send_header("Content-Type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps({"ok": False}).encode())


def handle_logout(handler) -> None:
    """
    POST /api/logout
    Sterge cookie-ul de sesiune.
    """
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json")
    # Expira cookie-ul imediat
    handler.send_header(
        "Set-Cookie",
        "ls_token=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0"
    )
    handler.end_headers()
    handler.wfile.write(json.dumps({"ok": True}).encode())
