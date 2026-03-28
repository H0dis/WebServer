"""
ws_server.py
------------
WebSocket server dedicat clipboardului.
Ruleaza in paralel cu server.py pe portul WS_PORT (default 8766).

Cum functioneaza:
- Fiecare client (PC sau telefon) se conecteaza si ramane conectat
- Cand cineva trimite text, serverul il distribuie imediat la toti ceilalti
- Salveaza si in models/clipboard.py ca sa fie consistent cu restul aplicatiei
"""

import asyncio
import json
import websockets
from models.clipboard import set_clipboard, get_clipboard
from config import LOCAL_IP, WS_URL, PORT

WS_PORT = PORT + 1  # 8766 daca HTTP e pe 8765

# Setul de clienti conectati in acest moment
# Folosim un set ca sa putem adauga/sterge usor
_clients: set = set()


async def on_connect(websocket):
    """
    Apelata automat cand un client nou se conecteaza.
    websocket = conexiunea cu acel client specific.
    """
    # Inregistram clientul
    _clients.add(websocket)
    print(f"[WS] Client conectat. Total: {len(_clients)}")

    try:
        # Trimitem imediat starea curenta a clipboardului
        # ca noul client sa fie sincronizat de la inceput
        current = get_clipboard()
        await websocket.send(json.dumps(current))

        # Asteptam mesaje de la acest client
        async for message in websocket:
            await handle_message(websocket, message)

    except websockets.exceptions.ConnectionClosed:
        # Clientul s-a deconectat — normal, nu e o eroare
        pass
    finally:
        # Scoatem clientul din set cand pleaca
        _clients.discard(websocket)
        print(f"[WS] Client deconectat. Total: {len(_clients)}")


async def handle_message(sender, message):
    """
    Proceseaza un mesaj primit de la un client.
    sender = clientul care a trimis mesajul (ca sa nu i-l trimitem inapoi).
    message = textul clipboardului (string JSON).
    """
    try:
        data = json.loads(message)
        text = data.get("text", "")
    except Exception:
        return  # mesaj invalid, ignoram

    # Salvam in model — consistent cu restul aplicatiei
    new_state = set_clipboard(text)
    response  = json.dumps(new_state)

    # Trimitem la toti ceilalti clienti conectati (nu inapoi la sender)
    # asyncio.gather ruleaza toate trimiterile in paralel, nu pe rand
    others = [c for c in _clients if c != sender]
    if others:
        await asyncio.gather(
            *[c.send(response) for c in others],
            return_exceptions=True  # daca un client pica, continuam cu ceilalti
        )


async def start():
    """Porneste serverul WebSocket si il tine activ."""
    async with websockets.serve(on_connect, "0.0.0.0", WS_PORT):
        print(f"[WS] Clipboard live pe ws://{LOCAL_IP}:{WS_PORT}")
        await asyncio.Future()  # ruleaza la infinit


def run_in_thread():
    """
    Ruleaza serverul WS intr-un thread separat.
    Necesar ca sa nu blocheze serverul HTTP.
    asyncio.run() creeaza un event loop nou in acel thread.
    """
    asyncio.run(start())
