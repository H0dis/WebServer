"""
models/files.py
---------------
Toata logica legata de fisiere si foldere.
Nu stie nimic de HTTP - doar citeste/scrie pe disk.
"""

from pathlib import Path
from config import FOLDER


# ── Utilitare ───────────────────────────────────────────────────────────────

def format_size(bytes: int) -> str:
    """Converteste bytes intr-un string lizibil (KB, MB, GB)."""
    if bytes < 1024:
        return f"{bytes} B"
    if bytes < 1024 ** 2:
        return f"{bytes / 1024:.1f} KB"
    if bytes < 1024 ** 3:
        return f"{bytes / 1024**2:.1f} MB"
    return f"{bytes / 1024**3:.1f} GB"


def is_image(filename: str) -> bool:
    """Returneaza True daca fisierul e o imagine."""
    return filename.split(".")[-1].lower() in (
        "png", "jpg", "jpeg", "gif", "webp", "svg"
    )


def can_preview(filename: str) -> bool:
    """Returneaza True daca fisierul poate fi previzualizat in browser."""
    return filename.split(".")[-1].lower() in (
        "png", "jpg", "jpeg", "gif", "webp", "svg",
        "txt", "md", "py", "js", "json", "html", "css"
    )


# ── Securitate ──────────────────────────────────────────────────────────────

def resolve_safe_path(rel: str) -> Path | None:
    """
    Rezolva o cale relativa in calea absoluta din FOLDER.
    Returneaza None daca cineva incearca path traversal (../../etc).
    """
    try:
        resolved = (FOLDER / rel).resolve()
        if not str(resolved).startswith(str(FOLDER)):
            return None
        return resolved
    except Exception:
        return None


# ── Citire ──────────────────────────────────────────────────────────────────

def list_folder(rel: str = "") -> dict:
    """
    Listeaza continutul unui subfolder.
    Returneaza un dict cu: files, folders, rel, total, disk.
    """
    folder = resolve_safe_path(rel)
    if not folder or not folder.is_dir():
        folder = FOLDER

    files = []
    folders = []
    folder_size = 0

    try:
        for entry in sorted(folder.iterdir()):
            if entry.is_dir():
                folders.append(entry.name)
            elif entry.is_file():
                size = entry.stat().st_size
                folder_size += size
                # path relativ fata de FOLDER (pentru download URL)
                file_rel = str(entry.relative_to(FOLDER)).replace("\\", "/")
                files.append({
                    "name":  entry.name,
                    "size":  format_size(size),
                    "bytes": size,
                    "ext":   entry.suffix.lower().lstrip("."),
                    "img":   is_image(entry.name),
                    "prev":  can_preview(entry.name),
                    "path":  file_rel,
                })
    except Exception:
        pass

    # Spatiu total folosit in intregul folder shared
    total_disk = sum(
        f.stat().st_size for f in FOLDER.rglob("*") if f.is_file()
    )

    return {
        "files":   files,
        "folders": folders,
        "rel":     rel,
        "total":   format_size(folder_size),
        "disk":    format_size(total_disk),
        "count":   len(files),
    }


# ── Scriere ─────────────────────────────────────────────────────────────────

def save_file(filename: str, content: bytes, rel: str = "") -> bool:
    """
    Salveaza un fisier in folderul rel.
    Returneaza True daca a reusit.
    """
    dest_folder = resolve_safe_path(rel)
    if dest_folder is None:
        return False
    dest_folder.mkdir(parents=True, exist_ok=True)
    try:
        (dest_folder / filename).write_bytes(content)
        return True
    except Exception:
        return False


def create_folder(name: str, rel: str = "") -> bool:
    """Creeaza un subfolder nou. Returneaza True daca a reusit."""
    # Curatam numele - nu permitem / sau \ in numele folderului
    safe_name = name.strip().replace("/", "").replace("\\", "")
    if not safe_name:
        return False
    parent = resolve_safe_path(rel)
    if parent is None:
        return False
    try:
        (parent / safe_name).mkdir(parents=True, exist_ok=True)
        return True
    except Exception:
        return False


def delete_file(rel: str) -> bool:
    """Sterge un fisier. Returneaza True daca a reusit."""
    path = resolve_safe_path(rel)
    if path and path.is_file():
        try:
            path.unlink()
            return True
        except Exception:
            pass
    return False


def get_parent_rel(rel: str) -> str:
    """Returneaza calea relativa a folderului parinte."""
    parent = str(Path(rel).parent)
    return "" if parent == "." else parent
