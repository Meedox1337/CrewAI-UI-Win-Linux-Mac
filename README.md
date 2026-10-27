# Local Crew Cockpit (PyQt6)

> **Produktionsreife, lokale Multi-Agenten-Orchestrierung ohne Cloud-Zwang.**  
> [![GitHub Profile](https://img.shields.io/badge/Developer-Medox1337-1e293b?style=flat-square&logo=github&logoColor=white)](https://github.com/Meedox1337?tab=repositories)

---

## 1. Urheberschaft & Technologie-Stack

* **UI & Architektur-Konzeption:** [**Medox1337**](https://github.com/Meedox1337?tab=repositories)  
  Vollständig entkoppelte, modulare PyQt6/PySide6 Benutzeroberfläche mit reaktivem Multi-Threading, tabellarischem Modell-Pool, Pipeline-Karten und unterbrechungsfreier Live-Hardwareüberwachung.
* **Core Agent Framework:** **[CrewAI](https://github.com/crewAIInc/crewAI)**  
  Strukturierte Rollenaufteilung (`Agent`), zielgerichtete Aufgabenverteilung (`Task`) und deterministische Pipeline-Steuerung mit synchroner und asynchroner Ausführung.
* **Lokale Inferenz & Modell-Backend:** **[Ollama](https://github.com/ollama/ollama)**  
  Vollständig lokale Modell-Inferenz über standardisierte REST/HTTP-Endpunkte (`/api/tags`, `/api/pull`, `/api/chat`, `/api/generate`). Garantierte Datenhoheit und Offline-Betrieb.
* **Echtzeit-Hardwareüberwachung:** **NVIDIA Management Library (NVML / pynvml)**  
  Direktes Polling von physischem Gesamt-, Belegungs- und freiem VRAM sowie GPU-Auslastung im Hintergrund-Thread ohne Beeinträchtigung des Qt-Event-Loops.

---

## 2. Funktionsweise & Kernarchitektur

### Multi-Model-Pipeline (Heterogenes Spezialisten-Team)
Das Cockpit bricht mit dem Dogma homogener Agenten-Setups: Jede Stufe der sequentiellen Pipeline kann mit einem dedizierten, auf die jeweilige Aufgabe spezialisierten Modell belegt werden:
* **Architektur, Planung & Code-Audit:** Reasoning-Modelle (z. B. `deepseek-r1:14b`, `deepseek-r1:32b`, `deepseek-r1:70b`) analysieren Anforderungen, erkennen Edge-Cases und erstellen Architekturpläne.
* **Code-Generierung & Refactoring:** Programmierspezialisten (z. B. `qwen2.5-coder:14b`, `qwen2.5-coder:32b`, `starcoder2`) setzen die Architektur präzise in sauberen Code um.
* **Recherche, Dokumentation & Test:** Sprachmodelle mit starker Allgemeinbildung (z. B. `mistral-nemo:12b`, `llama3.3:70b`, `llama3.1:8b`) übernehmen Dokumentation, Testfall-Synthese und Web-Recherche.

### Dynamisches Kontextfenster (Hardware-Adaptive `num_ctx`)
Anstelle starrer oder willkürlicher Begrenzungen (wie standardmäßigen 2k- oder 4k-Tokens) kalkuliert das Cockpit vor jedem Workflow dynamisch das maximal sichere Kontextfenster:
1. Ermittlung des physisch verbauten GPU-VRAMs via NVML (`vram_total_gb`).
2. Bestimmung des speicherintensivsten Modells im Team (`max_model_size_gb`).
3. Berechnung des verbleibenden Puffers für KV-Cache und GPU-Headroom:
   $$\text{Headroom} = \text{VRAM}_{\text{total}} - \text{Modellgröße} - \text{Sicherheitsreserve (2.5 GB)}$$
4. Automatische hardware-agnostische Skalierung:
   * **Spar- & Mid-Range-Hardware (< 16 GB VRAM):** Konservative Kontextfenster von 4.096 bis 16.384 Tokens zur Vermeidung von CUDA Out-of-Memory-Crashes.
   * **High-End-Hardware (24 GB bis 32 GB VRAM, z. B. RTX 3090/4090/5090):** Automatische Freigabe von 65.536 bis 131.072 Tokens (`64k` / `128k`), die bei CrewAI-Initialisierung explizit als `num_ctx` an Ollama übergeben werden.

### Tool-Calling & Auto-Execute Sandbox
Agenten interagieren direkt und sicher mit dem Projekt-Workspace:
* **Isolierter Workspace-Schutz:** Alle Schreib- und Patch-Operationen (`file_write_tool`, `file_patch_tool`, `file_grep_tool`, `file_read_tool`) validieren Zielpfade über `os.path.commonpath`. Jeder Zugriff außerhalb des freigegebenen Workspace-Ordners wird mit einer Sicherheitsblockade abgewiesen.
* **Physisches Patching:** Präzise Ersetzung von Codeblöcken via `file_patch_tool` minimiert Token-Verbrauch gegenüber vollständigen Dateineuschreibungen.
* **Fallback-Parsing für Text-Toolcalls:** Gibt ein Modell (insbesondere reine Reasoning-Modelle) Tool-Aufrufe fälschlicherweise als JSON-Textblock (`{"name": "file_write_tool", ...}`) anstelle eines nativen API-Tool-Calls aus, erkennt der Runner dieses Verhalten automatisch, extrahiert die Parameter und führt die Dateioperation physisch im Workspace aus.

### Resource Lifecycle & Zero-Leak-Reset
Um VRAM-Fragmentierung und persistente Speicherblockaden nach Abschluss oder Abbruch einer Pipeline zu verhindern:
* Nach Pipeline-Ende werden alle Ollama-Verbindungen ordnungsgemäß geschlossen.
* Gezielter Aufruf mit `keep_alive: 0` erzwingt bei Bedarf die sofortige Freigabe des VRAMs durch den Ollama-Daemon.
* Worker-Threads werden deterministisch beendet (`quit()` mit Timeout-Fallback auf `terminate()`), UI-Buttons sofort wieder entsperrt.

---

## 3. Installation & Schnellstart

### Systemvoraussetzungen
* **Betriebssystem:** Windows 10/11 (64-Bit), Linux oder macOS.
* **Python:** Python 3.10 oder 3.11 empfohlen.
* **GPU & Treiber:** NVIDIA-Grafikkarte mit aktuellem NVIDIA-Treiber (für NVML VRAM-Tracking).
* **Ollama:** Installiert und im Hintergrund aktiv ([ollama.com](https://ollama.com)).

### Schritt-für-Schritt Setup

1. **Repository klonen oder Projektordner öffnen:**
   ```bash
   git clone https://github.com/Meedox1337/LocalCrewCockpit.git
   cd LocalCrewCockpit
   ```

2. **Virtuelle Python-Umgebung anlegen & aktivieren:**
   ```bash
   # Windows PowerShell / CMD
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. **Abhängigkeiten installieren:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ollama starten:**
   Stelle sicher, dass der lokale Ollama-Server läuft:
   ```bash
   ollama serve
   ```
   *(Empfohlene Modelle vorab laden, z. B. `ollama pull qwen2.5-coder:14b` und `ollama pull deepseek-r1:14b`)*

5. **Local Crew Cockpit starten:**
   ```bash
   python main.py
   ```

---

## 4. Streaming-Tracking & Modell-Management

Das Cockpit verfügt über ein voll-integriertes Modell-Pool-Management in Zone 1:
* **Hintergrund-Update-Check:** Vergleicht lokale SHA256-Manifest-Digests via HEAD/GET mit der Ollama-Registry (`https://registry.ollama.ai/v2/...`). Ist eine neuere Version verfügbar, wechselt die Update-Schaltfläche auf `⚡ Update verfügbar`.
* **Live-Streaming-Tracking:** Beim Download/Update wird der JSON-Stream zeilenweise geparst:
  * In der UI: Button wechselt auf `⏳ 45% (10.0 GB)`.
  * Im Terminal: Interaktiver Fortschrittsbalken mit Geschwindigkeits- und Restzeitanzeige:
    ```text
    [PULL] qwen2.5-coder:14b:  45%|████▍     | 10.0G/22.2G [01:23<01:45, 115MB/s]
    ```
  * Im Live-Log: Regelmäßige Zwischenstände alle 10% sowie Abschlussmeldung `[SUCCESS] Modell '...' vollständig geladen und einsatzbereit.`

---

## 5. Entwickler- & Debugging-Guide (Py-Debugging & CLI)

Für Entwickler, Prompt-Ingenieure und System-Fehlersuche bietet das Cockpit einen dedizierten, hochdetaillierten Debug-Modus.

### Aktivierung des Debug-Modus
Starte das Cockpit über das CLI-Flag `--debug`:
```bash
python main.py --debug
```
Alternativ über die Umgebungsvariable `COCKPIT_DEBUG=1`:
```powershell
# PowerShell
$env:COCKPIT_DEBUG="1"
python main.py

# CMD
set COCKPIT_DEBUG=1
python main.py
```

Beim Start signalisiert das Cockpit den aktiven Modus:
```text
[DEBUG-MODE AKTIV] Detaillierte Fehlerprotokollierung eingeschaltet.
```

### Diagnose & Logging-Transparenz
Im Debug-Modus protokolliert das System in Echtzeit auf der Konsole:
1. **Ollama HTTP REST-Events:**
   Ausgabe aller Request-URLs, Headers, Payloads (`/api/pull`, `/api/tags`, `/api/show`, `/api/delete`) und Chunk-Streams.
2. **Tool-Payloads & Sandboxing:**
   Vollständige Erfassung der an Werkzeuge übergebenen Argumente (`file_path`, `content_len`, `pattern`) sowie deren exakte Rückgabewerte.
3. **CrewAI Step & Callback Tracking:**
   Schritt-für-Schritt-Protokollierung jedes Task-Zustandswechsels und Gedankengangs.
4. **Vollständige Python-Tracebacks:**
   Bei Ausnahmen in Threads, REST-Aufrufen oder Tool-Ausführungen wird der gesamte Callstack mit Dateinamen und Zeilennummern ausgegeben.

### Fehlerbehebung & Best Practices

| Symptom / Problem | Ursache | Lösung |
| :--- | :--- | :--- |
| **`Connection refused` / Offline** | Ollama-Dienst läuft nicht auf Port 11434. | Führe `ollama serve` in einem separaten Terminal aus und klicke auf `Modelle neu laden`. |
| **`CUDA out of memory`** | Das gewählte Modell überschreitet den realen VRAM zusammen mit dem KV-Cache. | Wähle ein kleineres Quantisierungs-Level (z. B. `q4_K_M` statt `q8_0`) oder reduziere die Anzahl gleichzeitiger Hintergrundprogramme. |
| **Agent simuliert Tool-Calls als Text** | Kleinere Modelle (< 7B) verstehen native Function-Calling-Tokens nicht immer zuverlässig. | Das integrierte Fallback-System fängt den Text ab und führt ihn aus. Für beste native Ergebnisse wird `qwen2.5-coder:14b` oder höher empfohlen. |
| **NVML Warning beim Start** | Deprecation-Hinweis älterer `pynvml`-Pakete. | Unkritisch; wird vom Cockpit intern abgefangen. Optional auf `nvidia-ml-py` aktualisieren. |

---

## 6. Projektstruktur

```text
CrewAI/
├── core/
│   ├── crew_runner.py        # CrewAI Orchestrierung, Task-Queue & Hardware-Kontext-Kalkulation
│   ├── logger.py             # Zentrales Logging-System (--debug & Payload-Tracing)
│   ├── model_knowledge.py    # VRAM-Schätzungen, Capability- & Rollen-Matrix
│   ├── ollama_client.py      # Asynchroner REST-Client, Registry-Checks & Download-Streamer
│   ├── system_monitor.py     # NVML GPU- & VRAM-Monitor im Hintergrund-Thread
│   ├── tools.py              # Sandbox-gesicherte Datei-, Patch- & Suchwerkzeuge
│   └── locales.py            # Lokalisierungs-Strings (Deutsch & Englisch)
├── ui/
│   ├── components/
│   │   ├── model_pool_widget.py   # Zone 1: Tabellarischer Modell-Pool & Update-Status
│   │   ├── pipeline_widget.py     # Zone 2: Rollenbasierte Agenten-Pipeline & Reordering
│   │   ├── workspace_widget.py    # Zone 3: Aufgabenprompt & Workspace-Dateibaum
│   │   ├── system_dock.py         # Hardware-Dock (VRAM, RAM, CPU-Bargraphen)
│   │   └── log_dock.py            # Live-Aktivitätslog & Terminalausgabe
│   ├── main_window.py        # Schlanker Koordinator & Layout-Assembler
│   └── pipeline_card.py      # Einzelne Agenten-Karte mit Live-Gedankenstream
├── main.py                   # Applikations-Einstiegspunkt & Theme-Initialisierung
├── requirements.txt          # Python-Paketabhängigkeiten
└── README.md                 # Projektdokumentation & Architektur-Guide
```

---

## 7. Lizenz & Nutzungsbestimmungen

Entwickelt für den transparenten, datenschutzkonformen und hochperformanten Einsatz lokaler Sprachmodelle in professionellen Software-Entwicklungsworkflows. Freie Nutzung im Rahmen lokaler Forschung und Entwicklung.
