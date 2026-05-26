# --- Configuration specific for JOSM Tagger ---

# Set the DISPLAY variable, if not defined.
# Useful when the app is launched from a remote terminal (e.g.. SSH)
# or there's no X server in the environment.

if [ -z "$DISPLAY" ]; then
    echo "AVVISO: La variabile d'ambiente DISPLAY non è impostata. Tentativo di impostarla a :0.0"
    export DISPLAY=:0.0
    echo "Se l'applicazione non si avvia, potrebbe essere necessario configurare manualmente DISPLAY o assicurarsi che il server X sia in esecuzione e accessibile."
fi
