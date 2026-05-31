#!/bin/bash

# --- Configuration specific for JOSM Tagger ---

# Set the DISPLAY variable, if not defined.
# Useful when the app is launched from a remote terminal (e.g.. SSH)
# or there's no X server in the environment.

# 1.  Avvio manuale da terminale: L'utente può semplicemente renderlo eseguibile (chmod +x josmtagger.sh)
#     e poi lanciarlo da terminale (./josmtagger.sh).
# 2.  Come comando per le hotkey del desktop (su Wayland): Nelle impostazioni delle scorciatoie da tastiera
#     del desktop, l'utente dovrebbe impostare il comando come il percorso completo di questo script
#       -> esempio:
#          josmtagger.sh


SESSION_TYPE="${XDG_SESSION_TYPE:-unknown}"
USE_XEPHYR="${JOSM_TAGGER_USE_XEPHYR:-0}"

start_xephyr_session() {
    local xephyr_display="${JOSM_TAGGER_XEPHYR_DISPLAY:-:99}"
    local xephyr_geometry="${JOSM_TAGGER_XEPHYR_GEOMETRY:-1280x800}"
    local xephyr_pid=""
    local wm_pid=""
    local app_pid=""
    local display_socket="${xephyr_display#:}"

    if [ -z "${DISPLAY:-}" ]; then
        cat <<'EOF'
ERRORE: per avviare Xephyr serve un display X host gia' disponibile.
Su Ubuntu Wayland questo di solito significa che XWayland non e' ancora attivo.
Apri una sessione grafica normale, verifica che la variabile DISPLAY sia presente
e rilancia il comando.
EOF
        exit 1
    fi

    if ! command -v Xephyr >/dev/null 2>&1; then
        cat <<'EOF'
ERRORE: Xephyr non trovato.
Installa il pacchetto con:
  sudo apt install xserver-xephyr
EOF
        exit 1
    fi

    (
        cleanup() {
            [ -n "$app_pid" ] && kill "$app_pid" 2>/dev/null || true
            [ -n "$wm_pid" ] && kill "$wm_pid" 2>/dev/null || true
            [ -n "$xephyr_pid" ] && kill "$xephyr_pid" 2>/dev/null || true
        }

        trap cleanup EXIT INT TERM

        nohup Xephyr "$xephyr_display" \
            -screen "$xephyr_geometry" \
            -ac \
            -br \
            -reset \
            >/dev/null 2>&1 &
        xephyr_pid=$!

        for _ in $(seq 1 100); do
            if [ -S "/tmp/.X11-unix/X${display_socket}" ]; then
                break
            fi
            sleep 0.1
        done

        sleep 0.5

        if command -v openbox >/dev/null 2>&1; then
            nohup env DISPLAY="$xephyr_display" openbox >/dev/null 2>&1 &
            wm_pid=$!
        fi

        nohup env DISPLAY="$xephyr_display" "${APP_COMMAND[@]}" >/dev/null 2>&1 &
        app_pid=$!

        wait "$app_pid"
    ) >/dev/null 2>&1 &
}

if [ "$SESSION_TYPE" = "wayland" ] && [ "$USE_XEPHYR" != "1" ] && [ "${JOSM_TAGGER_ALLOW_WAYLAND:-0}" != "1" ]; then
    cat <<'EOF'
ERRORE: La sessione grafica attuale e' Wayland.
La hotkey globale di JOSM Tagger funziona in modo affidabile solo su X11.

Per avviarlo correttamente:
1. Esci dalla sessione corrente.
2. Alla schermata di login, scegli una sessione X11/Xorg, oppure usa Xephyr.
   - Per un X11 vero: "GNOME on Xorg" o una sessione X11 equivalente
   - Per restare su Wayland: avvia JOSM Tagger in Xephyr
3. Verifica dopo il login con:
   echo $XDG_SESSION_TYPE
   Deve stampare: x11
4. Per Xephyr installa il pacchetto:
   sudo apt install xserver-xephyr
5. Poi rilancia questo script.

Se vuoi solo testare l'interfaccia senza hotkey globale, puoi forzare il lancio con:
   JOSM_TAGGER_ALLOW_WAYLAND=1 ./josmtagger.sh
EOF
    exit 1
fi

if [ -z "$DISPLAY" ] && [ "$SESSION_TYPE" != "wayland" ]; then
    echo "AVVISO: La variabile d'ambiente DISPLAY non è impostata. Tentativo di impostarla a :0.0"
    export DISPLAY=:0.0
    echo "Se l'applicazione non si avvia, potrebbe essere necessario configurare manualmente DISPLAY o assicurarsi che il server X sia in esecuzione e accessibile."
fi

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
MODE="${JOSM_TAGGER_MODE:-auto}"
if [ "$MODE" = "auto" ]; then
    if [ -f "$SCRIPT_DIR/main.py" ]; then
        MODE="local"
    else
        MODE="installed"
    fi
fi

echo "JOSM Tagger launcher mode: $MODE"
echo "JOSM Tagger session type: ${SESSION_TYPE:-unknown}"

APP_COMMAND=()

if [ "$MODE" = "local" ]; then
    if [ -f "$SCRIPT_DIR/josmtagger" ]; then
        APP_COMMAND=("$SCRIPT_DIR/josmtagger")
    elif [ -f "$SCRIPT_DIR/main.py" ]; then
        if [ -x "$SCRIPT_DIR/.venv/bin/python" ]; then
            APP_COMMAND=("$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/main.py")
        elif command -v python3 >/dev/null 2>&1; then
            APP_COMMAND=(python3 "$SCRIPT_DIR/main.py")
        else
            echo "ERRORE: python3 non trovato e nessun ambiente locale disponibile."
            exit 1
        fi
    fi
else
    if [ -x /usr/bin/josm-tagger ]; then
        APP_COMMAND=(/usr/bin/josm-tagger)
    elif [ -x /usr/bin/josmtagger ]; then
        APP_COMMAND=(/usr/bin/josmtagger)
    fi
fi

# Verifica se abbiamo trovato un comando valido.
if [ -z "${APP_COMMAND[*]}" ]; then
    echo "ERRORE: Nessun eseguibile o sorgente avviabile di JOSM Tagger trovato."
    echo "Controlla l'installazione oppure avvia il progetto dal repository con main.py."
    exit 1
fi

echo "JOSM Tagger command: ${APP_COMMAND[*]}"

# Wayland con hotkey globale: avvia la sessione in un Xephyr separato.
if [ "$SESSION_TYPE" = "wayland" ] && [ "$USE_XEPHYR" = "1" ]; then
    echo "JOSM Tagger nested X11 display: ${JOSM_TAGGER_XEPHYR_DISPLAY:-:99}"
    start_xephyr_session
    exit 0
fi

# Esegui l'applicazione in background e disconnettila dal terminale corrente
# Questo è importante per le applicazioni GUI avviate da script,
# specialmente se usate con hotkey o lanciatori desktop.
nohup "${APP_COMMAND[@]}" > /dev/null 2>&1 &
