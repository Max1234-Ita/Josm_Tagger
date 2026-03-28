import subprocess
import sys
import os

def build_exe():
    # Percorso del file principale
    main_script = "main.py"

    # Verifica che il file esista
    if not os.path.exists(main_script):
        print(f"Errore: {main_script} non trovato.")
        return

    # Comando PyInstaller
    cmd = [
        "pyinstaller",
        "--onefile",  # Crea un singolo file eseguibile
        "--windowed",  # Nessuna console (per app GUI)
        "--name=JOSM_Tagger",  # Nome dell'eseguibile
        f"--icon=resources/josm_tagger.ico",  # Icona
        "--add-data", "resources;resources",  # Includi la cartella resources
        "--add-data", "codes.json;.",  # Includi codes.json
        "--add-data", "config.json;.",  # Includi config.json
        main_script
    ]

    try:
        print("Avvio build con PyInstaller...")
        subprocess.run(cmd, check=True)
        print("Build completato! L'eseguibile si trova nella cartella 'dist'.")
    except subprocess.CalledProcessError as e:
        print(f"Errore durante il build: {e}")
    except FileNotFoundError:
        print("PyInstaller non trovato. Assicurati che sia installato (pip install pyinstaller).")

if __name__ == "__main__":
    build_exe()</content>
<parameter name="filePath">S:\PythonProject\Josm_Tagger\build_exe.py
