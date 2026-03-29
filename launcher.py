"""
launcher.py
-----------
Fereastra GUI pentru configurarea si pornirea LocalShare.


Fluxul:
1. Se deschide fereastra de configurare
2. Userul alege folder, port, parola (optional)
3. Apasa "Porneste"
4. Fereastra se transforma — arata IP + QR + buton Stop
5. La Stop sau inchidere fereastra, serverul se opreste
"""

import sys
import json
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path


# ── Setari salvate ───────────────────────────────────────────────────────────
# Le salvam intr-un fisier JSON langa launcher
SETTINGS_FILE = Path(__file__).parent / "settings.json"

DEFAULT_SETTINGS = {
    "folder": str(Path.home() / "LocalShare"),
    "port":   "8765",
}


def load_settings() -> dict:
    """Incarca setarile salvate. Returneaza default daca fisierul nu exista."""
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text())
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)


def save_settings(folder: str, port: str) -> None:
    """Salveaza folder si port (nu si parola — securitate)."""
    data = {"folder": folder, "port": port}
    SETTINGS_FILE.write_text(json.dumps(data, indent=2))


# ── Server process ───────────────────────────────────────────────────────────
_server_thread   = None
_http_server_ref = None   # referinta la HTTPServer ca sa il oprim


def start_server(folder: str, port: str, password: str) -> None:
    """Porneste server.py cu setarile date, intr-un thread separat."""
    global _server_thread

    # Injectam setarile in sys.argv ca server.py sa le citeasca din config.py
    sys.argv = ["server.py", port, folder]
    if password:
        sys.argv.append(password)

    # Importam server abia acum (dupa ce am setat sys.argv)
    # astfel config.py citeste valorile corecte
    import importlib
    import config as cfg
    importlib.reload(cfg)   # reload ca sa reciteasca sys.argv

    from models.files import recalculate_disk_cache
    recalculate_disk_cache()

    import ws_server
    ws_thread = threading.Thread(target=ws_server.run_in_thread, daemon=True)
    ws_thread.start()

    import server as srv
    global _http_server_ref
    _http_server_ref = srv.ThreadedServer(("0.0.0.0", int(port)), srv.Handler)

    _server_thread = threading.Thread(
        target=_http_server_ref.serve_forever,
        daemon=True
    )
    _server_thread.start()


def stop_server() -> None:
    """Opreste serverul HTTP."""
    global _http_server_ref
    if _http_server_ref:
        _http_server_ref.shutdown()
        _http_server_ref = None


# ── QR generator ─────────────────────────────────────────────────────────────
def make_qr_tk(url: str, size: int = 180):
    """Genereaza un QR code ca ImageTk.PhotoImage pentru tkinter."""
    try:
        import qrcode
        from PIL import ImageTk
        qr = qrcode.QRCode(box_size=4, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img = img.resize((size, size))
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


# ── Fereastra principala ──────────────────────────────────────────────────────
class LauncherApp:
    # Culori tema
    BG       = "#111111"
    SURFACE  = "#1a1a1a"
    BORDER   = "#2a2a2a"
    ACCENT   = "#6ee56e"
    TEXT     = "#eeeeee"
    MUTED    = "#666666"
    FONT     = ("Segoe UI", 10)
    FONT_BIG = ("Segoe UI", 14, "bold")

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("LocalShare")
        self.root.configure(bg=self.BG)
        self.root.resizable(False, False)

        # Centram fereastra pe ecran
        self.root.geometry("400x340")
        self._center_window(400, 340)

        self.settings = load_settings()
        self._build_config_screen()

    def _center_window(self, w: int, h: int) -> None:
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x  = (sw - w) // 2
        y  = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ── Ecranul de configurare ────────────────────────────────────────────────
    def _build_config_screen(self) -> None:
        """Construieste ecranul initial cu campurile de configurare."""
        self._clear()

        # Logo
        tk.Label(
            self.root, text="LocalShare",
            font=("Segoe UI", 18, "bold"),
            bg=self.BG, fg=self.ACCENT
        ).pack(pady=(28, 20))

        # Folder
        self._label("Folder partajat")
        folder_frame = tk.Frame(self.root, bg=self.BG)
        folder_frame.pack(fill="x", padx=24, pady=(2, 10))

        self.folder_var = tk.StringVar(value=self.settings.get("folder", ""))
        self._entry(folder_frame, self.folder_var).pack(
            side="left", fill="x", expand=True, ipady=6
        )
        tk.Button(
            folder_frame, text="...",
            font=self.FONT,
            bg=self.SURFACE, fg=self.TEXT,
            activebackground=self.BORDER,
            relief="flat", bd=0, padx=10,
            cursor="hand2",
            command=self._browse_folder
        ).pack(side="left", padx=(6, 0))

        # Port
        self._label("Port")
        self.port_var = tk.StringVar(value=self.settings.get("port", "8765"))
        self._entry(self.root, self.port_var).pack(
            fill="x", padx=24, pady=(2, 10), ipady=6
        )

        # Parola
        self._label("Parola (optional)")
        self.pass_var = tk.StringVar()
        self._entry(self.root, self.pass_var, show="•").pack(
            fill="x", padx=24, pady=(2, 20), ipady=6
        )

        # Buton Porneste
        tk.Button(
            self.root,
            text="Porneste",
            font=("Segoe UI", 11, "bold"),
            bg=self.ACCENT, fg="#111",
            activebackground="#5bc95b",
            relief="flat", bd=0,
            padx=20, pady=10,
            cursor="hand2",
            command=self._on_start
        ).pack(pady=4)

    def _label(self, text: str) -> None:
        tk.Label(
            self.root, text=text,
            font=("Segoe UI", 9),
            bg=self.BG, fg=self.MUTED,
            anchor="w"
        ).pack(fill="x", padx=24, pady=(6, 0))

    def _entry(self, parent, var: tk.StringVar, show: str = "") -> tk.Entry:
        e = tk.Entry(
            parent,
            textvariable=var,
            font=self.FONT,
            bg=self.SURFACE, fg=self.TEXT,
            insertbackground=self.TEXT,
            relief="flat", bd=0,
            highlightthickness=1,
            highlightbackground=self.BORDER,
            highlightcolor=self.ACCENT,
            show=show
        )
        return e

    def _browse_folder(self) -> None:
        """Deschide dialog pentru alegerea folderului."""
        chosen = filedialog.askdirectory(
            title="Alege folderul partajat",
            initialdir=self.folder_var.get() or str(Path.home())
        )
        if chosen:
            self.folder_var.set(chosen)

    # ── Start ─────────────────────────────────────────────────────────────────
    def _on_start(self) -> None:
        folder   = self.folder_var.get().strip()
        port_str = self.port_var.get().strip()
        password = self.pass_var.get().strip()

        # Validare de baza
        if not folder:
            messagebox.showerror("Eroare", "Alege un folder.")
            return

        # Cream folderul daca nu exista
        Path(folder).mkdir(parents=True, exist_ok=True)

        try:
            port = int(port_str)
            assert 1024 <= port <= 65535
        except Exception:
            messagebox.showerror("Eroare", "Portul trebuie sa fie intre 1024 si 65535.")
            return

        # Salvam setarile (fara parola)
        save_settings(folder, port_str)

        # Pornim serverul
        try:
            start_server(folder, port_str, password)
        except Exception as e:
            messagebox.showerror("Eroare la pornire", str(e))
            return

        # Trecem la ecranul de status
        self._build_running_screen(folder, port, password)

    # ── Ecranul de running ────────────────────────────────────────────────────
    def _build_running_screen(self, folder: str, port: int, password: str) -> None:
        """Dupa pornire, afisam IP, QR si butonul de Stop."""
        self._clear()
        self.root.geometry("400x460")
        self._center_window(400, 460)

        # Calculam URL-ul
        import socket
        def get_ip():
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
            except Exception:
                return "127.0.0.1"
            finally:
                s.close()

        ip  = get_ip()
        url = f"http://{ip}:{port}"

        # Header
        tk.Label(
            self.root, text="LocalShare",
            font=("Segoe UI", 14, "bold"),
            bg=self.BG, fg=self.ACCENT
        ).pack(pady=(20, 4))

        # Status running
        status_frame = tk.Frame(self.root, bg=self.BG)
        status_frame.pack()
        tk.Canvas(
            status_frame, width=10, height=10,
            bg=self.BG, highlightthickness=0
        ).create_oval(1, 1, 9, 9, fill=self.ACCENT, outline="")
        status_frame.pack()

        # Dot + "Rulează"
        dot_frame = tk.Frame(self.root, bg=self.BG)
        dot_frame.pack(pady=(0, 12))
        canvas = tk.Canvas(dot_frame, width=10, height=10, bg=self.BG, highlightthickness=0)
        canvas.create_oval(1, 1, 9, 9, fill=self.ACCENT)
        canvas.pack(side="left", padx=(0, 6))
        tk.Label(
            dot_frame, text="Ruleaza",
            font=("Segoe UI", 9), bg=self.BG, fg=self.ACCENT
        ).pack(side="left")

        # QR code
        qr_img = make_qr_tk(url, size=180)
        if qr_img:
            qr_lbl = tk.Label(
                self.root, image=qr_img,
                bg="white", relief="flat",
                cursor="hand2"
            )
            qr_lbl.image = qr_img  # pastram referinta ca sa nu fie garbage collected
            qr_lbl.pack(pady=(0, 10))
            qr_lbl.bind("<Button-1>", lambda e: webbrowser.open(url))

        # URL clickabil
        url_lbl = tk.Label(
            self.root, text=url,
            font=("Courier New", 10),
            bg=self.BG, fg=self.ACCENT,
            cursor="hand2"
        )
        url_lbl.pack()
        url_lbl.bind("<Button-1>", lambda e: webbrowser.open(url))

        # Info folder
        short_folder = folder if len(folder) < 38 else "..." + folder[-35:]
        tk.Label(
            self.root, text=short_folder,
            font=("Segoe UI", 8),
            bg=self.BG, fg=self.MUTED
        ).pack(pady=(4, 16))

        # Buton deschide browser
        tk.Button(
            self.root,
            text="Deschide in browser",
            font=("Segoe UI", 9),
            bg=self.SURFACE, fg=self.TEXT,
            activebackground=self.BORDER,
            relief="flat", bd=0, padx=14, pady=7,
            cursor="hand2",
            command=lambda: webbrowser.open(url)
        ).pack(pady=(0, 8))

        # Buton Stop
        tk.Button(
            self.root,
            text="Opreste serverul",
            font=("Segoe UI", 9),
            bg=self.SURFACE, fg="#e55",
            activebackground=self.BORDER,
            relief="flat", bd=0, padx=14, pady=7,
            cursor="hand2",
            command=self._on_stop
        ).pack()

        # Deschidem browser-ul automat dupa 500ms
        # (dam timp serverului sa porneasca)
        self.root.after(600, lambda: webbrowser.open(url))

    # ── Stop ──────────────────────────────────────────────────────────────────
    def _on_stop(self) -> None:
        """Opreste serverul si revine la ecranul de configurare."""
        stop_server()
        self.root.geometry("400x340")
        self._center_window(400, 340)
        self._build_config_screen()

    # ── Helper ────────────────────────────────────────────────────────────────
    def _clear(self) -> None:
        """Sterge toate widgeturile din fereastra."""
        for widget in self.root.winfo_children():
            widget.destroy()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Ascundem fereastra CMD pe Windows daca rulam ca .py (nu ca .exe)
    # La compilare cu --noconsole, asta nu mai e necesar
    import platform
    if platform.system() == "Windows":
        try:
            import ctypes
            ctypes.windll.user32.ShowWindow(
                ctypes.windll.kernel32.GetConsoleWindow(), 0
            )
        except Exception:
            pass

    root = tk.Tk()
    app  = LauncherApp(root)
    root.mainloop()