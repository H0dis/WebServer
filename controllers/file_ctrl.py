"""
controllers/file_ctrl.py
------------------------
Toate operatiile pe fisiere: listare, upload, download, stergere, foldere.
"""

import io
import json
import mimetypes
from pathlib import Path
from urllib.parse import unquote

import sse
from config import CHUNK_SIZE
from models.files import (
    list_folder, save_file, delete_file,
    create_folder, resolve_safe_path, get_parent_rel
)


def handle_list_files(handler, rel: str = "") -> None:
    """GET /api/files?rel=... — listeaza fisierele dintr-un folder."""
    data = list_folder(rel)
    handler.send_json(data)


def handle_download(handler, rel: str) -> None:
    """
    GET /api/download/<rel_path>
    Trimite fisierul in streaming (nu il citeste tot in memorie).
    """
    path = resolve_safe_path(rel)
    if not path or not path.is_file():
        handler.send_error(404)
        return

    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    size = path.stat().st_size

    handler.send_response(200)
    handler.send_header("Content-Type", mime)
    handler.send_header("Content-Length", size)
    handler.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()

    # Trimite in bucati - nu incarca tot fisierul in RAM
    with open(path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            handler.wfile.write(chunk)


def handle_thumbnail(handler, rel: str) -> None:
    """
    GET /api/thumb/<rel_path>
    Genereaza un thumbnail mic pentru imagini (80x80, WebP).
    Fallback: trimite imaginea originala daca Pillow nu e disponibil.
    """
    path = resolve_safe_path(rel)
    if not path or not path.is_file():
        handler.send_error(404)
        return

    try:
        from PIL import Image
        img = Image.open(path)
        img.thumbnail((80, 80))
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=70)
        data = buf.getvalue()

        handler.send_response(200)
        handler.send_header("Content-Type", "image/webp")
        handler.send_header("Content-Length", len(data))
        handler.send_header("Cache-Control", "max-age=3600")
        handler.end_headers()
        handler.wfile.write(data)

    except Exception:
        # Pillow nu e disponibil sau fisierul nu e o imagine valida
        handle_download(handler, rel)


def handle_upload(handler) -> None:
    """
    POST /api/upload
    Primeste multipart/form-data cu campurile: file, rel.
    Salveaza fisierul si face broadcast SSE.
    """
    ctype = handler.headers.get("Content-Type", "")
    if "multipart/form-data" not in ctype:
        handler.send_error(400)
        return

    boundary = ctype.split("boundary=")[-1].encode()
    length = int(handler.headers.get("Content-Length", 0))
    body = handler.rfile.read(length)

    rel = ""
    parts = body.split(b"--" + boundary)

    for part in parts[1:-1]:
        if b"\r\n\r\n" not in part:
            continue
        header_raw, _, content = part.partition(b"\r\n\r\n")
        content = content.rstrip(b"\r\n")
        header = header_raw.decode(errors="replace")

        # Camp "rel" - folderul destinatie
        if 'name="rel"' in header:
            rel = content.decode(errors="replace").strip()
            continue

        # Camp "file" - fisierul propriu-zis
        if 'filename="' not in header:
            continue
        filename = header.split('filename="')[1].split('"')[0]
        if not filename:
            continue

        save_file(filename, content, rel)

    # Notifica toti clientii ca lista s-a schimbat
    _broadcast_folder(rel)
    handler.send_json({"ok": True})


def handle_delete(handler, rel: str) -> None:
    """
    DELETE /api/delete/<rel_path>
    Sterge fisierul si face broadcast SSE in folderul parinte.
    """
    deleted = delete_file(rel)
    parent_rel = get_parent_rel(rel)
    _broadcast_folder(parent_rel)
    handler.send_json({"ok": deleted})


def handle_mkdir(handler) -> None:
    """
    POST /api/mkdir
    Body: { name: "...", rel: "..." }
    Creeaza un subfolder nou.
    """
    length = int(handler.headers.get("Content-Length", 0))
    body = json.loads(handler.rfile.read(length))
    name = body.get("name", "")
    rel = body.get("rel", "")

    created = create_folder(name, rel)
    if created:
        _broadcast_folder(rel)
        handler.send_json({"ok": True})
    else:
        handler.send_error(400)


# ── Helpers interne ─────────────────────────────────────────────────────────

def _broadcast_folder(rel: str) -> None:
    """Trimite lista actualizata de fisiere la toti clientii SSE."""
    data = json.dumps(list_folder(rel), ensure_ascii=False)
    sse.broadcast("files", data)
