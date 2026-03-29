# LocalShare v3

Transfer fisiere intre PC si telefon, fara cloud, fara cont. Doar WiFi local.

## Structura

```
localshare/
├── launcher.py            <- pornire cu GUI (recomandat)
├── server.py              <- entry point, routing HTTP
├── config.py              <- setari (port, folder, parola)
├── sse.py                 <- broadcaster Server-Sent Events
├── ws_server.py           <- WebSocket pentru clipboard live
├── models/
│   ├── auth.py            <- sesiuni si tokeni
│   ├── clipboard.py       <- starea clipboardului
│   └── files.py           <- logica filesystem
├── controllers/
│   ├── auth_ctrl.py       <- login / logout
│   ├── clip_ctrl.py       <- get / set / clear clipboard
│   └── file_ctrl.py       <- upload, download, delete, mkdir
└── views/
    ├── login.html
    ├── desktop.html
    └── mobile.html
```

---

## Pornire

### 1. Instaleaza dependentele (o singura data)
```bash
pip install qrcode[pil] Pillow websockets
```

### 2. Varianta simpla — launcher GUI (recomandat)
```bash
python launcher.py
```
Se deschide o fereastra unde alegi folderul, portul si parola.
Setarile se salveaza automat pentru data viitoare.

### 3. Varianta avansata — linie de comanda
```bash
python server.py 8765 C:\SharedFiles parolamea
```

---

## Compilare .exe (portabil)

```bash
pip install pyinstaller

pyinstaller --onefile --name LocalShare \
  --add-data "views;views" \
  launcher.py
```

Executabilul apare in `dist/LocalShare.exe`.

---

## Functionalitati

| Feature | Status |
|---|---|
| Launcher GUI cu QR | OK |
| PC -> Telefon (download) | OK |
| Telefon -> PC (upload) | OK |
| Drag & drop pe PC | OK |
| Update in timp real (SSE) | OK |
| Clipboard live (WebSocket) | OK |
| UI mobil dedicat | OK |
| Preview fisiere (desktop + mobil) | OK |
| Skeleton loading | OK |
| Parola de acces | OK |
| Foldere & navigare | OK |
| Thumbnails imagini | OK |
| Romana / Engleza | OK |
| Logout | OK |