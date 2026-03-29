"""
config.py
---------
Toate setarile aplicatiei intr-un singur loc.
- Portul pe care ruleaza serverul HTTP (ex: 8765)
- Folderul care se expune ca "desktop" (ex: ./shared)
- Parola pentru autentificare (daca e goala, nu se cere parola)
"""

import sys
import socket
from pathlib import Path


# ── Parametri din linia de comanda ─────────────────────────────────────────
# Exemplu: python server.py 8765 ./shared parolamea
PORT     = int(sys.argv[1])             if len(sys.argv) > 1 else 8765
FOLDER   = Path(sys.argv[2]).resolve()  if len(sys.argv) > 2 else Path.cwd() / "shared"
PASSWORD = sys.argv[3]                  if len(sys.argv) > 3 else ""

# Creeaza folderul daca nu exista
FOLDER.mkdir(parents=True, exist_ok=True)

# ── Streaming ───────────────────────────────────────────────────────────────
# Cat de mari sunt chunk-urile la download (512 KB)
CHUNK_SIZE = 512 * 1024

# ── Retea ───────────────────────────────────────────────────────────────────
def get_local_ip() -> str:
    """Gaseste IP-ul local al masinii in retea (nu 127.0.0.1)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


LOCAL_IP = get_local_ip()
BASE_URL = f"http://{LOCAL_IP}:{PORT}"
WS_URL   = f"ws://{LOCAL_IP}:{PORT + 1}"  # portul HTTP + 1, ex: 8766

# ── Views ───────────────────────────────────────────────────────────────────
# Calea catre folderul cu fisierele HTML
# PyInstaller seteaza sys._MEIPASS cand ruleaza din .exe
import os
if getattr(sys, "frozen", False):
    # Rulam din .exe compilat
    BASE_DIR = Path(sys._MEIPASS)
else:
    # Rulam normal cu Python
    BASE_DIR = Path(__file__).parent

VIEWS_DIR = BASE_DIR / "views"
