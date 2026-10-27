#!/usr/bin/env bash
# =====================================================================
#           LOCAL CREW COCKPIT - LAUNCHER (Linux / macOS)
# =====================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "====================================================================="
echo "           Local Crew Cockpit (PyQt6) - Launcher"
echo "====================================================================="
echo ""

# 1. Prüfen, ob python3 verfügbar ist
if ! command -v python3 >/dev/null 2>&1; then
    echo "[FEHLER / ERROR] 'python3' wurde nicht gefunden!"
    echo "Bitte stellen Sie sicher, dass Python 3 (mindestens Python 3.10) installiert und im PATH registriert ist."
    exit 1
fi

# 2. Prüfen und Erstellen der virtuellen Umgebung (venv)
if [ ! -f "venv/bin/python" ]; then
    echo "[INFO] Virtuelle Umgebung 'venv' wird erstellt..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[FEHLER / ERROR] Erstellung des virtuellen Environments fehlgeschlagen."
        exit 1
    fi
    echo "[INFO] Virtuelle Umgebung 'venv' erfolgreich erstellt."
fi

# 3. Virtuelle Umgebung aktivieren
source venv/bin/activate

# 4. Check auf benötigte Kernbibliotheken
if ! python3 -c "import PyQt6, crewai, ollama" >/dev/null 2>&1; then
    echo ""
    echo "============================================================"
    echo "Es fehlen noch benötigte Bibliotheken (z. B. PyQt6)."
    echo "Required libraries are missing (e.g. PyQt6)."
    echo "============================================================"
    echo ""
    read -p "Möchten Sie alle erforderlichen Bibliotheken jetzt automatisch installieren? / Install missing libraries now? [J/n]: " choice
    choice="${choice:-J}"
    case "$choice" in
        [jJyY]*)
            echo ""
            echo "[INFO] Installiere Abhängigkeiten, bitte warten / Installing dependencies, please wait..."
            python3 -m pip install --upgrade pip --quiet
            pip install -r requirements.txt
            echo "[INFO] Alle Bibliotheken erfolgreich installiert!"
            ;;
        *)
            echo ""
            echo "[ABBRUCH / CANCEL] Start ohne erforderliche Bibliotheken nicht möglich."
            exit 0
            ;;
    esac
fi

# 5. Anwendung starten
echo ""
echo "[INFO] Starte Local Crew Cockpit..."
echo "---------------------------------------------------------------------"
python3 main.py

EXIT_CODE=$?
echo ""
echo "---------------------------------------------------------------------"
echo "[INFO] Anwendung beendet mit Exit-Code: $EXIT_CODE"
