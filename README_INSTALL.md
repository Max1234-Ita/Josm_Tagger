# JOSM Tagger - Installazione e Configurazione (Windows / Linux)

## 1) Prerequisiti

- Python `3.11+` (consigliato `3.12`)
- `pip` aggiornato
- JOSM installato (l'app interagisce con la finestra di JOSM)

## 2) Download progetto

```powershell
git clone https://github.com/Max1234-Ita/Josm_Tagger.git
cd Josm_Tagger
```

## 3) Setup ambiente virtuale

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Linux (bash)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 4) Dipendenze di sistema Linux

Su Debian/Ubuntu installa anche:

```bash
sudo apt update
sudo apt install -y python3-tk libcanberra-gtk-module libcanberra-gtk3-module
```

## 5) Configurazione consigliata di `pystray`

Per il supporto tray/hotkey è consigliata la versione GitHub di `pystray`:

```bash
pip uninstall -y pystray
pip install git+https://github.com/moses-palmer/pystray.git
```

## 6) Avvio applicazione

Da root progetto:

```bash
python main.py
```

## 7) Configurazione operativa

- Apri JOSM prima di usare `Apply`.
- L'app cerca la finestra JOSM con titolo **"Java OpenStreetMap Editor"**.
- Configurazione UI e geometria vengono salvate in `config.json`.
- I codici/tag usati dall'app sono in `codes.json`.

## 8) Problemi comuni

- **Hotkey non funziona su Linux**: prova a eseguire in sessione X11 (su Wayland alcuni hook globali sono limitati).
- **Finestra JOSM non trovata**: verifica che JOSM sia aperto e che il titolo finestra corrisponda.
- **Errore Tkinter su Linux**: verifica installazione di `python3-tk`.

## 9) Build eseguibile

### Windows (PyInstaller)

Il progetto include uno script pronto:

```powershell
python build_exe.py
```

Output atteso: eseguibile in `dist/JOSM_Tagger.exe`.

### Linux (PyInstaller)

Su Linux usa direttamente `pyinstaller` (su Linux il separatore di `--add-data` è `:`):

```bash
pyinstaller \
  --onefile \
  --windowed \
  --name=JOSM_Tagger \
  --icon=resources/josm_tagger.ico \
  --add-data "resources:resources" \
  --add-data "codes.json:." \
  --add-data "config.json:." \
  main.py
```

Output atteso: eseguibile in `dist/JOSM_Tagger`.

### Pulizia build

Per rigenerare da zero:

- rimuovi `build/`
- rimuovi `dist/`
- rimuovi `JOSM_Tagger.spec` (se presente)
