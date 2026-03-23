# LocalShare v3

Transfer fisiere intre PC si telefon, fara cloud, fara cont. Doar WiFi local.

## Structura

```
localshare/
├── server.py              <- entry point, routing HTTP
├── config.py              <- setari (port, folder, parola)
├── sse.py                 <- broadcaster Server-Sent Events
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
pip install qrcode[pil] Pillow
```

### 2. Ruleaza
```bash
# Fara parola
python server.py

# Cu port si folder custom
python server.py 8765 C:\SharedFiles

# Cu parola
python server.py 8765 C:\SharedFiles parolamea
```

### 3. Deschide
- **PC** -> http://localhost:8765
- **Telefon** -> Scaneaza QR-ul din sidebar

---

## Compilare .exe (portabil)

```bash
pip install pyinstaller

pyinstaller --onefile --name LocalShare \
  --add-data "views;views" \
  server.py
```

> Pe Windows foloseste `;` ca separator, pe Linux/Mac foloseste `:`.

Executabilul apare in `dist/LocalShare.exe`.  
Copiaza-l oriunde - nu necesita Python instalat.

---

## Functionalitati

| Feature | Status |
|---|---|
| PC -> Telefon (download) | OK |
| Telefon -> PC (upload) | OK |
| Drag & drop pe PC | OK |
| Update in timp real (SSE) | OK |
| UI mobil dedicat | OK |
| Parola de acces | OK |
| Clipboard sync PC <-> Telefon | OK |
| Download streaming (fisiere mari) | OK |
| Foldere & navigare | OK |
| Thumbnails imagini | OK |
| Logout | OK |
