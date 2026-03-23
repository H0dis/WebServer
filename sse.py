"""
sse.py
------
Server-Sent Events broadcaster.
Tine o lista de clienti conectati si trimite mesaje tuturor.
"""

import threading

# Lista de cozi - fiecare client conectat are propria coada
_clients: list[list] = []
_lock = threading.Lock()


def add_client() -> list:
    """Inregistreaza un client nou si returneaza coada lui."""
    queue: list = []
    with _lock:
        _clients.append(queue)
    return queue


def remove_client(queue: list) -> None:
    """Sterge clientul din lista cand se deconecteaza."""
    with _lock:
        if queue in _clients:
            _clients.remove(queue)


def broadcast(event: str, data: str) -> None:
    """Trimite un eveniment SSE tuturor clientilor conectati."""
    msg = f"event: {event}\ndata: {data}\n\n".encode()
    with _lock:
        dead = []
        for queue in _clients:
            try:
                queue.append(msg)
            except Exception:
                dead.append(queue)
        for queue in dead:
            _clients.remove(queue)
