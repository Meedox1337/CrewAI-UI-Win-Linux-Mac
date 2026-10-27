@echo off
setlocal EnableDelayedExpansion
title Local Crew Cockpit

cd /d "%~dp0"

echo ============================================================
echo               Local Crew Cockpit Starter
echo ============================================================
echo.

:: 1. Virtuelle Umgebung prüfen und ggf. erstellen
if not exist "venv\Scripts\python.exe" (
    echo [INFO] Virtuelle Umgebung 'venv' wird erstellt...
    python -m venv venv
    if errorlevel 1 (
        echo [FEHLER] Python konnte keine venv erstellen. Ist Python installiert?
        pause
        exit /b 1
    )
    goto :INSTALL_DEPS
)

:: 2. Prüfen, ob Kernbibliotheken vorhanden sind
"venv\Scripts\python.exe" -c "import PyQt6, crewai, ollama" >nul 2>&1
if %errorlevel% equ 0 (
    goto :RUN_APP
)

:PROMPT_USER
echo ============================================================
echo Es fehlen noch benoetigte Bibliotheken (z. B. PyQt6).
echo ============================================================
set /p USER_CHOICE="Moechten Sie alle Pakete jetzt installieren? (J/N): "

if /i "%USER_CHOICE%"=="J" goto :INSTALL_DEPS
if /i "%USER_CHOICE%"=="Ja" goto :INSTALL_DEPS
if /i "%USER_CHOICE%"=="Y" goto :INSTALL_DEPS
if /i "%USER_CHOICE%"=="Yes" goto :INSTALL_DEPS

echo.
echo [ABBRUCH] Start ohne erforderliche Bibliotheken nicht moeglich.
pause
exit /b 0

:INSTALL_DEPS
echo.
echo [INFO] Installiere Abhaengigkeiten aus requirements.txt...
echo Dies kann beim ersten Mal 1-2 Minuten dauern. Bitte warten...
echo.
call "venv\Scripts\pip.exe" install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [FEHLER] Die Installation der Pakete ist fehlgeschlagen.
    pause
    exit /b 1
)

echo.
echo [INFO] Installation erfolgreich abgeschlossen!
echo.

:RUN_APP
echo [INFO] Starte Local Crew Cockpit...
echo.
call "venv\Scripts\python.exe" main.py
if errorlevel 1 (
    echo.
    echo [FEHLER] Die Anwendung wurde unerwartet beendet.
)

pause
exit /b 0
