@echo off
setlocal enabledelayedexpansion
title Local Crew Cockpit (PyQt6)

:: 1. Initialisierung & Pfad-Isolation
cd /d "%~dp0"

:: 2. Python-Systempruefung
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ============================================================
    echo [FEHLER] Python wurde auf Ihrem System nicht gefunden!
    echo.
    echo Bitte installieren Sie Python 3.10 oder 3.11 und stellen Sie sicher,
    echo dass die Option "Add Python to PATH" im Installer aktiviert ist.
    echo Download: https://www.python.org/downloads/
    echo ============================================================
    pause
    exit /b 1
)

:: 3. Autonome Virtual Environment (venv) Erstellung
if not exist "venv\Scripts\python.exe" (
    echo [SETUP] Virtuelle Python-Umgebung wird isoliert eingerichtet...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ============================================================
        echo [FEHLER] Die Erstellung der virtuellen Umgebung ist fehlgeschlagen.
        echo Bitte ueberpruefen Sie Ihre Python-Installation.
        echo ============================================================
        pause
        exit /b 1
    )
    echo [SETUP] Aktualisiere pip in der virtuellen Umgebung...
    ".\venv\Scripts\python.exe" -m pip install --upgrade pip
)

:: 4. Abhaengigkeiten pruefen & installieren
".\venv\Scripts\python.exe" -c "import PyQt6, crewai" >nul 2>&1
if %errorlevel% neq 0 (
    echo [SETUP] Installiere benoetigte Bibliotheken aus requirements.txt...
    ".\venv\Scripts\pip.exe" install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ============================================================
        echo [WARNUNG] Die Installation der Abhaengigkeiten ist fehlgeschlagen.
        echo Bitte Internetverbindung und requirements.txt ueberpruefen.
        echo ============================================================
        pause
        exit /b 1
    )
    echo [OK] Alle Abhaengigkeiten erfolgreich installiert.
)

:: 5. Start der Applikation
echo.
echo [OK] Starte Local Crew Cockpit...
echo.
".\venv\Scripts\python.exe" main.py %*
if %errorlevel% neq 0 (
    echo.
    echo ============================================================
    echo [FEHLER] Die Anwendung wurde mit Fehlercode %errorlevel% beendet.
    echo ============================================================
    pause
)

exit /b 0
