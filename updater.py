"""
updater.py
----------
Verifica daca exista o versiune noua pe GitHub si o descarca.

Fluxul:
1. check_for_update()  -> returneaza info despre noua versiune (sau None)
2. download_update()   -> descarca noul .exe ca LocalShare_new.exe
3. apply_update()      -> scrie un .bat care face swap si porneste .bat-ul
4. App se inchide, .bat asteapta, inlocuieste .exe, reporneste
"""

import sys
import os
import json
import urllib.request
import urllib.error
import threading
from pathlib import Path
from config import VERSION, GITHUB_REPO


# ── Comparare versiuni ───────────────────────────────────────────────────────

def parse_version(v: str) -> tuple:
    """
    Converteste "1.2.3" in (1, 2, 3) pentru comparare.
    Scoate 'v' din fata daca exista (ex: "v1.2.3" -> (1,2,3)).
    """
    v = v.lstrip("v").strip()
    try:
        return tuple(int(x) for x in v.split("."))
    except Exception:
        return (0, 0, 0)


def is_newer(remote: str, local: str) -> bool:
    """Returneaza True daca versiunea remote e mai noua decat cea locala."""
    return parse_version(remote) > parse_version(local)


# ── GitHub API ───────────────────────────────────────────────────────────────

def fetch_latest_release() -> dict | None:
    url = f"https://api.github.com/repos/H0dis/WebServer/releases/latest" 
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": f"LocalShare/{VERSION}"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        # Cautam asset-ul .exe in lista de assets a release-ului
        exe_url = None
        for asset in data.get("assets", []):
            if asset["name"].endswith(".exe"):
                exe_url = asset["browser_download_url"]
                break

        if not exe_url:
            return None

        return {
            "version":      data.get("tag_name", "").lstrip("v"),
            "download_url": exe_url,
            "notes":        data.get("body", "").strip()[:200],  # primele 200 de caractere
        }

    except Exception:
        # Fara internet, timeout, repo inexistent — ignoram silentios
        return None


def check_for_update() -> dict | None:
    """
    Verifica daca exista update. Returneaza info despre update sau None. Apelata intr-un thread separat ca sa nu blocheze launcher-ul.
    """
    info = fetch_latest_release()
    if info and is_newer(info["version"], VERSION):
        return info
    return None


# ── Download ─────────────────────────────────────────────────────────────────

def download_update(download_url: str, on_progress=None) -> Path | None:
    """
    Descarca noul .exe langa cel curent, cu numele LocalShare_new.exe. 
    on_progress(percent) e apelat pe masura ce descarca (pentru progress bar). Returneaza calea fisierului descarcat sau None daca a esuat.
    """
    # Punem noul .exe langa cel care ruleaza acum
    if getattr(sys, "frozen", False):
        # Rulam din .exe compilat
        current_exe = Path(sys.executable)
    else:
        # Rulam din Python — punem langa launcher.py
        current_exe = Path(__file__).parent / "LocalShare.exe"

    dest = current_exe.parent / "LocalShare_new.exe"

    try:
        req = urllib.request.Request(
            download_url,
            headers={"User-Agent": f"LocalShare/{VERSION}"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 64 * 1024  # 64 KB per chunk

            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if on_progress and total:
                        on_progress(int(downloaded / total * 100))

        return dest

    except Exception:
        # Curatam fisierul partial daca a esuat
        if dest.exists():
            dest.unlink()
        return None


# ── Aplicare update ──────────────────────────────────────────────────────────

def apply_update(new_exe: Path) -> None:
    """
    Scrie un .bat care:
    1. Asteapta 2 secunde ca procesul curent sa se inchida
    2. Inlocuieste LocalShare.exe cu LocalShare_new.exe
    3. Porneste noul LocalShare.exe
    4. Se sterge singur la final
    Apoi porneste .bat-ul si inchide aplicatia. """
    if getattr(sys, "frozen", False):
        current_exe = Path(sys.executable)
    else:
        current_exe = new_exe.parent / "LocalShare.exe"

    bat_path = new_exe.parent / "localshare_update.bat"

    # Scriptul batch — ruleaza dupa ce inchidem app-ul
    bat_content = f"""@echo off
timeout /t 2 /nobreak > nul
move /y "{new_exe}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
"""
    bat_path.write_text(bat_content, encoding="utf-8")

    # Pornim .bat-ul minimizat (nu apare CMD) si inchidem app-ul
    import subprocess
    subprocess.Popen(
        ["cmd", "/c", str(bat_path)],
        creationflags=subprocess.CREATE_NO_WINDOW
                      | subprocess.DETACHED_PROCESS
    )


# ── Helper pentru thread ──────────────────────────────────────────────────────

def check_async(on_result) -> None:
    """
    Verifica update-ul intr-un thread de fundal.
    on_result(info) e apelat pe thread-ul principal (via after() in tkinter)
    cu info-ul update-ului sau None daca nu e nimic nou.
    """
    def run():
        result = check_for_update()
        on_result(result)

    t = threading.Thread(target=run, daemon=True)
    t.start()
