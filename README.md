# LocalShare

Transfer fisiere intre PC si telefon, fara cloud, fara cont. Doar WiFi local.

---

## Pornire rapida

### 1. Instaleaza dependentele (o singura data)
```bash
pip install qrcode[pil] Pillow websockets
```

### 2. Porneste
```bash
python launcher.py
```

Se deschide o fereastra unde alegi folderul, portul si parola.
Setarile se salveaza automat. Browserul se deschide singur dupa pornire.

---

## Compilare .exe

```bash
pip install pyinstaller

pyinstaller --onefile --noconsole --name LocalShare \
  --add-data "views;views" \
  launcher.py
```

Executabilul apare in `dist/LocalShare.exe` — copiaza-l oriunde, nu necesita Python.

---

## Structura proiect

```
localshare/
├── launcher.py            <- GUI pornire (entry point)
├── server.py              <- HTTP server + routing
├── ws_server.py           <- WebSocket clipboard live
├── updater.py             <- OTA update logic
├── sse.py                 <- Server-Sent Events broadcaster
├── config.py              <- toate setarile (VERSION, PORT, FOLDER etc.)
├── models/
│   ├── auth.py            <- sesiuni si tokeni
│   ├── clipboard.py       <- starea clipboardului
│   └── files.py           <- logica filesystem (list, save, delete)
├── controllers/
│   ├── auth_ctrl.py       <- login / logout
│   ├── clip_ctrl.py       <- get / set / clear clipboard
│   └── file_ctrl.py       <- upload, download, delete, mkdir, thumbnail
└── views/
    ├── login.html         <- pagina de autentificare
    ├── desktop.html       <- interfata PC
    └── mobile.html        <- interfata telefon
```

---

## Configurare

In `config.py` sunt doua lucruri de schimbat inainte de primul release:

```python
VERSION     = "1.0.0"               # versiunea curenta
GITHUB_REPO = "username/localshare" # repo-ul tau GitHub
```

---

## OTA Update

Aplicatia verifica automat la fiecare pornire daca exista o versiune noua pe GitHub.

**Cum publici un update:**
1. Compileaza noul `.exe`
2. GitHub repo → Releases → Draft a new release
3. Tag: `v1.1.0` (sau orice versiune noua)
4. Uploadeaza `LocalShare.exe` ca asset
5. Publish release

La urmatoarea pornire, userii vad un banner galben cu optiunea de download.

---

## Linie de comanda (avansat)

```bash
# Fara parola
python server.py

# Cu port, folder si parola custom
python server.py 8765 C:\SharedFiles parolamea
```

---

## Functionalitati

| Feature | Status |
|---|---|
| Launcher GUI cu QR | ok |
| OTA update automat | ok |
| PC -> Telefon (download streaming) | ok |
| Telefon -> PC (upload) | ok |
| Drag & drop pe PC | ok |
| Update lista in timp real (SSE) | ok |
| Clipboard live PC <-> Telefon (WebSocket) | ok |
| UI mobil dedicat | ok |
| Preview fisiere (desktop + mobil) | ok |
| Skeleton loading | ok |
| Foldere & navigare | ok |
| Thumbnails imagini | ok |
| Parola de acces | ok |
| Romana / Engleza | ok |
| Logout | ok |