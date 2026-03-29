
import sys
import json
import time
import base64
import qrcode
import io
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote, parse_qs

import sse
import config
import ws_server
from models.files import recalculate_disk_cache
from models.clipboard import get_clipboard
from models.files import list_folder
from controllers.auth_ctrl import is_authenticated, handle_login, handle_logout
from controllers.file_ctrl import (
    handle_list_files, handle_download, handle_thumbnail,
    handle_upload, handle_delete, handle_mkdir
)
from controllers.clip_ctrl import (
    handle_get_clipboard, handle_set_clipboard, handle_clear_clipboard
)


# ── QR code ─────────────────────────────────────────────────────────────────
def make_qr_base64(url: str) -> str:
    """Genereaza QR code ca imagine PNG encodata base64."""
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ── Views loader ─────────────────────────────────────────────────────────────
def load_view(name: str) -> str:
    """Citeste un fisier HTML din folderul views/."""
    path = config.VIEWS_DIR / name
    return path.read_text(encoding="utf-8")


# Cache views in memorie ca sa nu citim disk la fiecare request
_views_cache: dict[str, str] = {}

def get_view(name: str) -> str:
    if name not in _views_cache:
        _views_cache[name] = load_view(name)
    return _views_cache[name]


# ── Request Handler ──────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        # Dezactivam log-urile default (prea verbose)
        pass

    def is_mobile(self) -> bool:
        """Detecteaza daca request-ul vine de pe un telefon."""
        ua = self.headers.get("User-Agent", "").lower()
        return any(x in ua for x in ("iphone", "ipad", "android", "mobile"))

    # ── GET ─────────────────────────────────────────────────────────────────
    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip("/") or "/"
        qs     = parse_qs(parsed.query)

        # Login nu necesita autentificare
        if not is_authenticated(self) and path != "/api/login":
            if path.startswith("/api/"):
                self.send_error(401)
            else:
                self.send_html(get_view("login.html"))
            return

        # ── Routing GET ──
        if path == "/":
            view = "mobile.html" if self.is_mobile() else "desktop.html"
            self.send_html(get_view(view))

        elif path == "/api/info":
            self.send_json({
                "url":    config.BASE_URL,
                "ws_url": config.WS_URL,
                "ip":     config.LOCAL_IP,
                "port":   config.PORT,
                "folder": str(config.FOLDER),
                "qr":     make_qr_base64(config.BASE_URL),
            })

        elif path == "/api/events":
            self._handle_sse(qs)

        elif path == "/api/files":
            rel = qs.get("rel", [""])[0]
            handle_list_files(self, rel)

        elif path.startswith("/api/download/"):
            rel = unquote(path[len("/api/download/"):])
            handle_download(self, rel)

        elif path.startswith("/api/thumb/"):
            rel = unquote(path[len("/api/thumb/"):])
            handle_thumbnail(self, rel)

        elif path == "/api/clipboard":
            handle_get_clipboard(self)

        else:
            self.send_error(404)

    # ── POST ────────────────────────────────────────────────────────────────
    def do_POST(self):
        path = urlparse(self.path).path

        # Login e public
        if path == "/api/login":
            handle_login(self)
            return

        if not is_authenticated(self):
            self.send_error(401)
            return

        # ── Routing POST ──
        if path == "/api/logout":
            handle_logout(self)
        elif path == "/api/upload":
            handle_upload(self)
        elif path == "/api/mkdir":
            handle_mkdir(self)
        elif path == "/api/clipboard":
            handle_set_clipboard(self)
        elif path == "/api/clipboard/clear":
            handle_clear_clipboard(self)
        else:
            self.send_error(404)

    # ── DELETE ──────────────────────────────────────────────────────────────
    def do_DELETE(self):
        if not is_authenticated(self):
            self.send_error(401)
            return

        path = urlparse(self.path).path
        if path.startswith("/api/delete/"):
            rel = unquote(path[len("/api/delete/"):])
            handle_delete(self, rel)
        else:
            self.send_error(404)

    # ── OPTIONS (CORS) ──────────────────────────────────────────────────────
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.end_headers()

    # ── SSE handler ─────────────────────────────────────────────────────────
    def _handle_sse(self, qs: dict):
        """
        Conexiune SSE persistenta.
        Trimite snapshot initial apoi asteapta broadcast-uri.
        """
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        queue = sse.add_client()
        try:
            # Trimite starea initiala imediat la conectare
            rel = qs.get("rel", [""])[0]
            files_data = json.dumps(list_folder(rel), ensure_ascii=False)
            clip_data  = json.dumps(get_clipboard(), ensure_ascii=False)

            self.wfile.write(f"event: files\ndata: {files_data}\n\n".encode())
            self.wfile.write(f"event: clipboard\ndata: {clip_data}\n\n".encode())
            self.wfile.flush()

            # Loop: trimite mesaje din coada sau heartbeat la fiecare 15s
            while True:
                while queue:
                    self.wfile.write(queue.pop(0))
                self.wfile.write(b": ping\n\n")
                self.wfile.flush()
                time.sleep(15)

        except Exception:
            pass
        finally:
            sse.remove_client(queue)

    # ── HTTP helpers ─────────────────────────────────────────────────────────
    def send_html(self, html: str):
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, obj: dict):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(data))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)


# ── Threaded server ──────────────────────────────────────────────────────────
class ThreadedServer(HTTPServer):
    """
    Fiecare request e tratat intr-un thread separat.
    Necesar pentru SSE - altfel o conexiune SSE ar bloca totul.
    """
    def process_request(self, request, client_address):
        t = threading.Thread(target=self._handle, args=(request, client_address))
        t.daemon = True
        t.start()

    def _handle(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            pass


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    pw_info = f"parola: {config.PASSWORD}" if config.PASSWORD else "fara parola (acces liber)"

    # Calculam spatiul de disk o singura data la pornire
    recalculate_disk_cache()

    # Pornim WebSocket-ul intr-un thread de fundal
    ws_thread = threading.Thread(target=ws_server.run_in_thread, daemon=True)
    ws_thread.start()

    print(f"""
+----------------------------------------------+
|         LocalShare v3 - pornit!              |
+----------------------------------------------+
  PC     -> http://localhost:{config.PORT}
  Telefon-> {config.BASE_URL}
  Folder -> {config.FOLDER}
  Auth   -> {pw_info}
+----------------------------------------------+
Ctrl+C pentru a opri.
""")
    server = ThreadedServer(("0.0.0.0", config.PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nOprit. Pa!")