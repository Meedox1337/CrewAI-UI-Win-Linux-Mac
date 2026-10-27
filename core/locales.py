"""
Local Crew Cockpit - Bilingual Localization System (DE/EN)
Provides complete, type-safe text dictionaries and helper functions
for the user interface, tooltips, status badges, and logs.
"""

from typing import Any, Dict, List, Optional

TEXTS: Dict[str, Dict[str, str]] = {
    "de": {
        # App-Metadaten & Allgemeines
        "app_title": "Local Crew Cockpit",
        "app_subtitle": "Transparente Steuerung lokaler CrewAI-Agenten-Workflows",
        "app_version": "v1.0.0",
        "loading": "Wird geladen...",
        "cancel": "Abbrechen",
        "close": "Schließen",
        "confirm": "Bestätigen",
        "save": "Speichern",
        "copy": "Kopieren",
        "copied": "In die Zwischenablage kopiert!",

        # Header: Statusanzeigen & globale Aktionen
        "header_ollama_title": "Ollama Service",
        "header_ollama_online": "Ollama: Online",
        "header_ollama_offline": "Ollama: Offline",
        "header_ollama_tooltip_online": "Lokale Ollama-Instanz ist erreichbar und einsatzbereit.",
        "header_ollama_tooltip_offline": "Ollama ist nicht erreichbar. Bitte führe 'ollama serve' im Terminal aus.",
        "header_vram_title": "VRAM / GPU",
        "header_vram_status": "VRAM: {used:.1f} / {total:.1f} GB ({percent:.0f}%)",
        "header_vram_cpu_fallback": "RAM: {used:.1f} / {total:.1f} GB ({percent:.0f}%) [CPU-Modus]",
        "header_vram_tooltip": "Aktueller Videospeicher-Verbrauch Ihrer Grafikkarte.",
        "header_token_budget_title": "Token-Budget",
        "header_token_budget_status": "Tokens: {consumed:,} / {budget}",
        "header_token_unlimited": "Unbegrenzt",
        "header_token_tooltip": "Geschätzter Token-Verbrauch im aktuellen Durchlauf.",
        "header_lang_toggle_de": "DE",
        "header_lang_toggle_en": "EN",
        "header_lang_tooltip": "Sprache wechseln (Deutsch / English)",
        "header_btn_reset": "Cockpit zurücksetzen",
        "header_btn_reset_tooltip": "Setzt Logs, Zustände und Zwischenergebnisse auf Standardwerte zurück.",
        "header_btn_help": "Schnellstart & Hilfe",
        "header_btn_help_tooltip": "Öffnet die Onboarding-Anleitung und Schritt-für-Schritt-Hilfe.",

        # Modellkarten & Agenten-Konfiguration
        "model_card_title": "Agenten-Konfiguration",
        "model_card_subtitle": "Definieren Sie Modelle, Rollen und Werkzeuge der Crew",
        "model_label_name": "Modell",
        "model_placeholder_select": "-- Modell auswählen --",
        "model_label_role": "Agenten-Rolle",
        "model_role_planner": "Planer (Strategie & Aufgabenaufteilung)",
        "model_role_researcher": "Rechercheur (Informationen & Kontext)",
        "model_role_coder": "Entwickler (Code & Implementierung)",
        "model_role_reviewer": "Prüfer (Qualitätssicherung & Review)",
        "model_role_custom": "Benutzerdefinierte Rolle",
        "model_label_websearch": "DuckDuckGo Web-Recherche aktivieren",
        "model_tooltip_websearch": "Erlaubt diesem Agenten, Echtzeit-Informationen aus dem Internet abzufragen.",
        "model_btn_update_models": "Modelle aktualisieren",
        "model_tooltip_update_models": "Fragt lokal installierte Ollama-Modelle erneut ab.",
        "model_status_ready": "Bereit",
        "model_status_thinking": "Denkt nach...",
        "model_status_done": "Abgeschlossen",
        "model_status_error": "Fehler aufgetreten",
        "model_status_waiting": "Wartet auf Zuweisung",

        # Pipeline / 2-Zonen-Workflow
        "pipeline_pool_title": "Modell-Pool / Verfügbare Modelle",
        "pipeline_team_title": "Aktives Agenten-Team (Pipeline)",
        "pipeline_btn_add": "Zu Team hinzufügen",
        "pipeline_btn_remove": "Aus Team entfernen",
        "pipeline_assign_role": "Rolle zuweisen",
        "pipeline_write_permission": "Dateirechte (Write)",
        "pipeline_web_search": "Websuche",
        "pipeline_live_thoughts": "Live-Gedanken & Output",
        "pipeline_clear": "Leeren",
        "pipeline_in_action": "In Aktion...",
        "pipeline_ready": "Bereit",
        "pipeline_done": "Abgeschlossen",
        "pipeline_tooltip_tools_disabled": (
            "Reines Reasoning-/Vision-Modell ohne Tool-Calling-Support. "
            "Bitte ein Coder-/Allrounder-Modell wie Qwen oder Llama für Web- oder Dateizugriff nutzen."
        ),
        "pipeline_tooltip_write_disabled": (
            "Dieses Modell unterstützt kein zuverlässiges Tool-Calling (Read-Only / reines Reasoning). "
            "Datei-Schreibzugriff ist gesperrt."
        ),
        "pipeline_tooltip_web_disabled": (
            "Dieses Modell unterstützt keine Function-Calling-Werkzeuge für Websuchen. "
            "Websuche ist gesperrt."
        ),

        # Tabellen-Header
        "header_model": "[✓] Modell & Größe",
        "header_vram": "VRAM-Check",
        "header_info": "Info",
        "header_role": "Rolle (Auswahl / Freitext)",
        "header_web": "Web",
        "header_write": "Write",
        "header_update": "Update",
        "header_delete": "Löschen",
        "header_thoughts": "Gedanken",
        "header_setup": "Setup",
        "header_status": "Status",

        # Buttons Endergebnis
        "btn_clear_result": "Leeren",
        "btn_save_result": "Speichern...",
        "btn_copy_result": "Kopieren",

        # Install-Dock & Tooltips
        "placeholder_install": "Neues Modell installieren (z.B. llama3.2:3b)...",
        "btn_install": "⬇️ Installieren",
        "btn_refresh_models": "🔄 Aktualisieren",
        "undock_btn": "↗ Abdocken",
        "dock_btn": "↙ Andocken",
        "btn_clear": "Leeren",
        "thought_title": "🧠 Live Reasoning & Gedanken (<think>):",
        "thought_popout_title": "🧠 Gedanken: {model}",
        "thought_popout_header": "🧠 Live Reasoning & Gedanken: {model}",
        "tooltip_active": "Modell für die Crew aktivieren/deaktivieren",
        "tooltip_info": "Fähigkeiten und Kontextfenster anzeigen",
        "tooltip_role": "Rolle auswählen oder eigene Berufsbezeichnung eingeben",
        "tooltip_web": "Websuche aktivieren (erlaubt dem Agenten Online-Recherche)",
        "tooltip_write": "Erlaubt diesem Agenten, Dateien im Zielprojektordner anzulegen oder zu überschreiben.",
        "tooltip_write_disabled": "Dieses Modell unterstützt kein zuverlässiges Tool-Calling (Read-Only / reines Reasoning). Datei-Schreibzugriff ist gesperrt.",
        "tooltip_tools_disabled": "Reines Reasoning-/Vision-Modell ohne Tool-Calling-Support. Bitte ein Coder-/Allrounder-Modell wie Qwen oder Llama für Web oder Dateizugriff nutzen.",
        "tooltip_update": "Prüft auf Modell-Updates bei Ollama",
        "tooltip_delete": "Modell dauerhaft von der Festplatte löschen",
        "tooltip_thoughts": "Live-Reasoning & <think>-Monolog ein-/ausklappen",
        "tooltip_setup": "Agent-Goal, Backstory & Delegierung konfigurieren",
        "tooltip_undock": "Gedanken-Stream in separatem Fenster öffnen (Pop-out)",
        "tooltip_dock": "Gedanken-Stream wieder in die Modellkarte andocken",
        "tooltip_clear_thoughts": "Gedankengang leeren",
        "tooltip_install_help": "Hilfe zur Modell-Eingabe & Empfehlungen",
        "modal_install_help_title": "Modell-Download & Speicherort-Verwaltung",
        "modal_install_help_heading": "💡 Leitfaden für Modell-Downloads & Speicherort",
        "modal_install_help_intro": (
            "Geben Sie in das Download-Feld NUR den reinen Modellbezeichner ein (z. B. 'qwen2.5-coder:14b' "
            "oder 'deepseek-r1:8b') – verwenden Sie keine Terminal-Präfixe wie 'ollama run' oder 'ollama pull'."
        ),
        "modal_install_help_examples_title": "Beliebte Modell-Empfehlungen (Klick zum Übernehmen):",
        "modal_install_help_ex_coder": "qwen2.5-coder:14b – Führend für Code-Generierung, Refactoring & Tests",
        "modal_install_help_ex_reasoning": "deepseek-r1:8b – Starkes logisches Reasoning, Systementwürfe & Planung",
        "modal_install_help_ex_fast": "llama3.2:3b – Sehr schnell, ressourcenschonend & ideal für Standard-Workflows",
        "modal_install_help_tag_note": "Hinweis: Wird kein Tag angegeben (z. B. nur 'llama3.2'), lädt Ollama automatisch ':latest'.",
        "modal_install_btn_use": "Übernehmen",
        "modal_install_table_title": "Orientierungstabelle Modellgrößen & Hardware-Bedarf:",
        "modal_install_table_col_params": "Parametergröße",
        "modal_install_table_col_download": "Downloadgröße",
        "modal_install_table_col_hw": "Empfohlene Hardware / Einsatzbereich",
        "modal_install_size_small_range": "3B bis 8B",
        "modal_install_size_small_dl": "ca. 2 bis 5 GB",
        "modal_install_size_small_hw": "Kleinere GPUs (ab 4-8 GB VRAM) & Laptops / schnelle Workflows",
        "modal_install_size_med_range": "14B bis 32B",
        "modal_install_size_med_dl": "ca. 9 bis 19 GB",
        "modal_install_size_med_hw": "Ideal für RTX 3090 / 4090 / 5090 (16-24 GB VRAM) / Top-Qualität",
        "modal_install_size_large_range": "70B",
        "modal_install_size_large_dl": "ca. 40 GB",
        "modal_install_size_large_hw": "⚠️ Hoher Download- & VRAM-Bedarf (Dual-GPU / 48+ GB RAM)",
        "modal_install_storage_title": "Speicherort & Festplatten-Kapazität:",
        "modal_install_path_label": "Aktiver Ollama-Speicherpfad:",
        "modal_install_free_space": "Freier Speicherplatz auf Ziel-Laufwerk: {free_gb:.1f} GB",
        "modal_install_space_sufficient": "🟢 Ausreichend Speicherplatz vorhanden",
        "modal_install_space_low": "⚠️ Speicherplatz knapp (< 25 GB frei)!",
        "modal_install_disk_warning": (
            "Warnung vor vollen Systemfestplatten: Da KI-Modelle schnell Dutzende Gigabytes belegen, "
            "kann Laufwerk C:\\ rasch volllaufen. Bei Bedarf kann der Speicherort auf eine dedizierte "
            "SSD oder NVMe (z. B. D:\\OllamaModels) ausgelagert werden."
        ),
        "modal_install_move_instructions": (
            "Schritte zur Speicherort-Änderung (Auslagerung auf z. B. D:\\OllamaModels):\n"
            "1. Beende Ollama (Rechtsklick im Infobereich der Taskleiste -> 'Quit Ollama').\n"
            "2. Setze die Windows-Umgebungsvariable OLLAMA_MODELS auf z. B. 'D:\\OllamaModels'.\n"
            "3. Starte Ollama neu – alle zukünftigen Downloads landen auf der dedizierten SSD."
        ),
        "modal_install_btn_copy_guide": "📋 Pfad-Anleitung kopieren",
        "modal_install_guide_copied": "✅ Anleitung kopiert!",
        "modal_install_btn_open_advisor": "💡 Hardwareberater öffnen",
        "btn_install_help_close": "Verstanden",

        # Ordnerpicker & Dateibaum (Workspace-Kontext)
        "workspace_title": "Projektordner & Dateikontext",
        "workspace_btn_select": "Ordner auswählen",
        "workspace_btn_select_tooltip": "Wählen Sie das Projektverzeichnis, das die Agenten analysieren oder bearbeiten sollen.",
        "workspace_no_folder": "Kein Ordner ausgewählt (Arbeitsbereich inaktiv)",
        "workspace_selected_folder": "Aktiver Ordner: {path}",
        "filetree_title": "Dateibaum & Filter",
        "filetree_filter_placeholder": "Dateien filtern (z.B. *.py, *.md)...",
        "filetree_ignore_label": "Ausschlüsse / Ignorieren:",
        "filetree_ignore_placeholder": ".git, __pycache__, venv, node_modules, .env",
        "filetree_stats": "{selected} von {total} Dateien als Kontext ausgewählt",
        "filetree_btn_select_all": "Alle auswählen",
        "filetree_btn_deselect_all": "Auswahl aufheben",

        # Master-Prompt & Crew-Steuerung
        "prompt_title": "Master-Prompt & Zieldefinition",
        "prompt_label": "Aufgabenstellung für die Crew:",
        "prompt_placeholder": "Beschreiben Sie hier präzise die Aufgabe, das gewünschte Endprodukt und eventuelle Randbedingungen für die Agenten...",
        "btn_start_crew": "Crew starten",
        "btn_start_crew_tooltip": "Startet den orchestrierten CrewAI-Workflow mit den aktiven Agenten.",
        "btn_stop_crew": "Ausführung abbrechen",
        "btn_stop_crew_tooltip": "Stoppt die Ausführung der laufenden Agenten sicher.",
        "control_status_idle": "Status: Leerlauf - Bereit für neue Aufgaben",
        "control_status_running": "Status: Crew arbeitet aktiv...",
        "control_status_stopping": "Status: Abbruch angefordert...",
        "control_status_stopped": "Status: Ausführung abgebrochen",

        # Live-Log, Banner & Monitoring
        "tab_live_log": "Live-Aktivitätslog",
        "tab_final_result": "Endergebnis",
        "log_btn_clear": "Log leeren",
        "log_btn_auto_scroll": "Automatischer Bildlauf",
        "log_filter_all": "Alle Ereignisse",
        "log_filter_agent": "Agentenschritte",
        "log_filter_tools": "Werkzeugaufrufe",
        "log_filter_errors": "Nur Fehler",
        "banner_info_title": "Information",
        "banner_success_title": "Erfolg",
        "banner_warning_title": "Warnung",
        "banner_error_title": "Fehler",
        "banner_workflow_finished": "Der CrewAI-Workflow wurde erfolgreich abgeschlossen!",
        "banner_workflow_failed": "Der Workflow wurde mit einem Fehler beendet. Details finden Sie im Live-Log.",
        "banner_no_model_selected": "Bitte weisen Sie allen aktiven Agenten ein verfügbares Ollama-Modell zu.",
        "banner_no_prompt": "Bitte geben Sie einen Master-Prompt ein, bevor Sie die Crew starten.",

        # Human-in-the-Loop & Ergebnisüberprüfung
        "hitl_title": "Ergebnisprüfung (Human-in-the-Loop)",
        "hitl_description": "Begutachten Sie das Arbeitsergebnis der Agenten und entscheiden Sie über Freigabe oder Überarbeitung:",
        "hitl_btn_approve": "Ergebnis abnehmen",
        "hitl_btn_approve_tooltip": "Akzeptiert das Arbeitsergebnis und schließt den Workflow final ab.",
        "hitl_btn_revise": "Nachbessern anfordern",
        "hitl_btn_revise_tooltip": "Gibt das Ergebnis mit Ihrem Feedback zurück an die Crew zur Korrektur.",
        "hitl_feedback_placeholder": "Geben Sie hier konkrete Korrekturhinweise oder Ergänzungswünsche ein...",
        "hitl_feedback_btn_send": "Feedback an Agenten übergeben",

        # Onboarding-Hilfe & Schnelleinstieg
        "help_modal_title": "Onboarding & Schnelleinstieg",
        "help_step_1_title": "Schritt 1: Lokales LLM mit Ollama bereitstellen",
        "help_step_1_desc": "Starten Sie Ollama im Hintergrund ('ollama serve') und laden Sie empfohlene Modelle herunter (z.B. 'ollama pull llama3.2' oder 'ollama pull qwen2.5-coder').",
        "help_step_2_title": "Schritt 2: Arbeitsbereich & Agentenrollen konfigurieren",
        "help_step_2_desc": "Wählen Sie über 'Ordner auswählen' Ihr Projektverzeichnis und weisen Sie den Agentenkarten die gewünschten lokalen Modelle und Werkzeuge zu.",
        "help_step_3_title": "Schritt 3: Master-Prompt formulieren & Crew starten",
        "help_step_3_desc": "Geben Sie das Ziel der Crew ein oder nutzen Sie den vorgefertigten Beispiel-Prompt, um sofort loszulegen.",
        "help_example_prompt_title": "Beispiel-Prompt für den Schnellstart:",
        "help_example_prompt_content": "Analysiere das aktuelle Arbeitsverzeichnis, erstelle eine modulare Architekturübersicht im Markdown-Format und identifiziere potenzielle Verbesserungen bezüglich Code-Qualität und Sicherheit.",
        "help_btn_copy_prompt": "Beispiel-Prompt kopieren",
        "help_btn_copied": "Prompt in Zwischenablage kopiert!",
    },
    "en": {
        # App metadata & general
        "app_title": "Local Crew Cockpit",
        "app_subtitle": "Transparent Control for Local CrewAI Agent Workflows",
        "app_version": "v1.0.0",
        "loading": "Loading...",
        "cancel": "Cancel",
        "close": "Close",
        "confirm": "Confirm",
        "save": "Save",
        "copy": "Copy",
        "copied": "Copied to clipboard!",

        # Header: status indicators & global actions
        "header_ollama_title": "Ollama Service",
        "header_ollama_online": "Ollama: Online",
        "header_ollama_offline": "Ollama: Offline",
        "header_ollama_tooltip_online": "Local Ollama instance is reachable and ready to serve.",
        "header_ollama_tooltip_offline": "Ollama is not reachable. Please execute 'ollama serve' in your terminal.",
        "header_vram_title": "VRAM / GPU",
        "header_vram_status": "VRAM: {used:.1f} / {total:.1f} GB ({percent:.0f}%)",
        "header_vram_cpu_fallback": "RAM: {used:.1f} / {total:.1f} GB ({percent:.0f}%) [CPU Mode]",
        "header_vram_tooltip": "Current video memory utilization of your graphics card.",
        "header_token_budget_title": "Token Budget",
        "header_token_budget_status": "Tokens: {consumed:,} / {budget}",
        "header_token_unlimited": "Unlimited",
        "header_token_tooltip": "Estimated token usage in the current session.",
        "header_lang_toggle_de": "DE",
        "header_lang_toggle_en": "EN",
        "header_lang_tooltip": "Switch language (German / English)",
        "header_btn_reset": "Reset Cockpit",
        "header_btn_reset_tooltip": "Resets logs, internal state, and temporary results back to defaults.",
        "header_btn_help": "Quickstart & Help",
        "header_btn_help_tooltip": "Opens the onboarding walkthrough and step-by-step documentation.",

        # Model cards & agent configuration
        "model_card_title": "Agent Configuration",
        "model_card_subtitle": "Configure models, roles, and toolsets for the Crew",
        "model_label_name": "Model",
        "model_placeholder_select": "-- Select Model --",
        "model_label_role": "Agent Role",
        "model_role_planner": "Planner (Strategy & Task Breakdown)",
        "model_role_researcher": "Researcher (Information & Context Gathering)",
        "model_role_coder": "Developer (Code Implementation & Refactoring)",
        "model_role_reviewer": "Reviewer (Quality Assurance & Validation)",
        "model_role_custom": "Custom Role",
        "model_label_websearch": "Enable DuckDuckGo Web Search",
        "model_tooltip_websearch": "Permits this agent to perform live queries on DuckDuckGo.",
        "model_btn_update_models": "Refresh Models",
        "model_tooltip_update_models": "Reload the list of locally installed Ollama models.",
        "model_status_ready": "Ready",
        "model_status_thinking": "Thinking...",
        "model_status_done": "Completed",
        "model_status_error": "Error encountered",
        "model_status_waiting": "Waiting for assignment",

        # Pipeline / 2-Zone Workflow
        "pipeline_pool_title": "Model Pool / Available Models",
        "pipeline_team_title": "Active Agent Team (Pipeline)",
        "pipeline_btn_add": "Add to Team",
        "pipeline_btn_remove": "Remove from Team",
        "pipeline_assign_role": "Assign Role",
        "pipeline_write_permission": "File Permissions (Write)",
        "pipeline_web_search": "Web Search",
        "pipeline_live_thoughts": "Live Thoughts & Output",
        "pipeline_clear": "Clear",
        "pipeline_in_action": "In action...",
        "pipeline_ready": "Ready",
        "pipeline_done": "Completed",
        "pipeline_tooltip_tools_disabled": (
            "Pure reasoning/vision model without tool-calling support. "
            "Please use a coder or general model such as Qwen or Llama for web or file write access."
        ),
        "pipeline_tooltip_write_disabled": (
            "This model does not reliably support tool calling (Read-Only / pure reasoning). "
            "File writing is disabled."
        ),
        "pipeline_tooltip_web_disabled": (
            "This model does not reliably support tool calling for web queries. "
            "Web search is disabled."
        ),

        # Table Header
        "header_model": "[✓] Model & Size",
        "header_vram": "VRAM Check",
        "header_info": "Info",
        "header_role": "Role (Preset / Custom)",
        "header_web": "Web",
        "header_write": "Write",
        "header_update": "Update",
        "header_delete": "Delete",
        "header_thoughts": "Thoughts",
        "header_setup": "Setup",
        "header_status": "Status",

        # Buttons Final Deliverable
        "btn_clear_result": "Clear",
        "btn_save_result": "Save...",
        "btn_copy_result": "Copy",

        # Install Dock & Tooltips
        "placeholder_install": "Install new model (e.g. llama3.2:3b)...",
        "btn_install": "⬇️ Install",
        "btn_refresh_models": "🔄 Refresh",
        "undock_btn": "↗ Pop-out",
        "dock_btn": "↙ Dock back",
        "btn_clear": "Clear",
        "thought_title": "🧠 Live Reasoning & Thoughts (<think>):",
        "thought_popout_title": "🧠 Thoughts: {model}",
        "thought_popout_header": "🧠 Live Reasoning & Thoughts: {model}",
        "tooltip_active": "Enable/disable model for the crew",
        "tooltip_info": "View model capabilities and context window",
        "tooltip_role": "Select role preset or enter custom role",
        "tooltip_web": "Enable web search (permits live online research)",
        "tooltip_write": "Allows this agent to create or edit files in the target project folder.",
        "tooltip_write_disabled": "This model does not reliably support tool calling (Read-Only / pure reasoning). File writing is disabled.",
        "tooltip_tools_disabled": "Pure reasoning/vision model without tool-calling support. Please use a coder or general model such as Qwen or Llama for web or file access.",
        "tooltip_update": "Check for model updates on Ollama",
        "tooltip_delete": "Permanently delete model from disk",
        "tooltip_thoughts": "Toggle live reasoning & <think> stream",
        "tooltip_setup": "Configure agent goal, backstory & delegation",
        "tooltip_undock": "Open thought stream in separate pop-out window",
        "tooltip_dock": "Dock thought stream back into model card",
        "tooltip_clear_thoughts": "Clear thinking stream",
        "tooltip_install_help": "Help for model input & recommendations",
        "modal_install_help_title": "Model Download & Storage Management",
        "modal_install_help_heading": "💡 Model Download & Storage Location Guide",
        "modal_install_help_intro": (
            "Enter ONLY the pure model identifier into the download field (e.g. 'qwen2.5-coder:14b' "
            "or 'deepseek-r1:8b') – do not include terminal prefixes like 'ollama run' or 'ollama pull'."
        ),
        "modal_install_help_examples_title": "Popular Model Recommendations (Click to insert):",
        "modal_install_help_ex_coder": "qwen2.5-coder:14b – Top performer for code generation, refactoring & tests",
        "modal_install_help_ex_reasoning": "deepseek-r1:8b – Strong logical reasoning, system design & planning",
        "modal_install_help_ex_fast": "llama3.2:3b – Ultra-fast, lightweight & ideal for standard workflows",
        "modal_install_help_tag_note": "Note: If no tag is specified (e.g. just 'llama3.2'), Ollama automatically downloads ':latest'.",
        "modal_install_btn_use": "Use",
        "modal_install_table_title": "Model Scale & Hardware Reference Table:",
        "modal_install_table_col_params": "Parameter Scale",
        "modal_install_table_col_download": "Download Size",
        "modal_install_table_col_hw": "Recommended Hardware / Target Scenario",
        "modal_install_size_small_range": "3B to 8B",
        "modal_install_size_small_dl": "approx. 2 to 5 GB",
        "modal_install_size_small_hw": "Entry GPUs (4-8 GB VRAM), laptops & fast workflows",
        "modal_install_size_med_range": "14B to 32B",
        "modal_install_size_med_dl": "approx. 9 to 19 GB",
        "modal_install_size_med_hw": "Ideal for RTX 3090 / 4090 / 5090 (16-24 GB VRAM) / Top Quality",
        "modal_install_size_large_range": "70B",
        "modal_install_size_large_dl": "approx. 40 GB",
        "modal_install_size_large_hw": "⚠️ Heavy download & VRAM requirements (Dual-GPU / 48+ GB RAM)",
        "modal_install_storage_title": "Storage Location & Disk Capacity Warning:",
        "modal_install_path_label": "Active Ollama storage path:",
        "modal_install_free_space": "Free disk space on target drive: {free_gb:.1f} GB",
        "modal_install_space_sufficient": "🟢 Sufficient disk space available",
        "modal_install_space_low": "⚠️ Disk space running low (< 25 GB free)!",
        "modal_install_disk_warning": (
            "System disk warning: Because AI models easily consume tens of gigabytes, your C:\\ "
            "drive can fill up rapidly. Relocating your Ollama storage to a dedicated SSD or NVMe "
            "(e.g. D:\\OllamaModels) is highly recommended."
        ),
        "modal_install_move_instructions": (
            "Steps to relocate storage (e.g. to D:\\OllamaModels):\n"
            "1. Quit Ollama (Right-click system tray icon -> 'Quit Ollama').\n"
            "2. Set the Windows environment variable OLLAMA_MODELS to e.g. 'D:\\OllamaModels'.\n"
            "3. Restart Ollama – all future downloads will store to the dedicated drive."
        ),
        "modal_install_btn_copy_guide": "📋 Copy Migration Guide",
        "modal_install_guide_copied": "✅ Guide copied!",
        "modal_install_btn_open_advisor": "💡 Open Hardware Advisor",
        "btn_install_help_close": "Understood",

        # Folder picker & file tree (workspace context)
        "workspace_title": "Project Folder & File Context",
        "workspace_btn_select": "Select Directory",
        "workspace_btn_select_tooltip": "Choose the workspace directory that agents should analyze or modify.",
        "workspace_no_folder": "No folder selected (Workspace inactive)",
        "workspace_selected_folder": "Active Folder: {path}",
        "filetree_title": "File Tree & Filters",
        "filetree_filter_placeholder": "Filter files (e.g. *.py, *.md)...",
        "filetree_ignore_label": "Exclusions / Ignore:",
        "filetree_ignore_placeholder": ".git, __pycache__, venv, node_modules, .env",
        "filetree_stats": "{selected} of {total} files selected as context",
        "filetree_btn_select_all": "Select All",
        "filetree_btn_deselect_all": "Clear Selection",

        # Master prompt & crew control
        "prompt_title": "Master Prompt & Objectives",
        "prompt_label": "Mission Objective for the Crew:",
        "prompt_placeholder": "Detail the specific task, required deliverables, constraints, and instructions for your agents...",
        "btn_start_crew": "Start Crew",
        "btn_start_crew_tooltip": "Launches the orchestrated CrewAI workflow with the configured agents.",
        "btn_stop_crew": "Stop Execution",
        "btn_stop_crew_tooltip": "Gracefully interrupts and stops active agent processing.",
        "control_status_idle": "Status: Idle - Ready for mission",
        "control_status_running": "Status: Crew is actively working...",
        "control_status_stopping": "Status: Cancellation requested...",
        "control_status_stopped": "Status: Execution stopped",

        # Live log, banners & monitoring
        "tab_live_log": "Live Activity Log",
        "tab_final_result": "Final Deliverable",
        "log_btn_clear": "Clear Log",
        "log_btn_auto_scroll": "Auto-scroll",
        "log_filter_all": "All Events",
        "log_filter_agent": "Agent Steps",
        "log_filter_tools": "Tool Calls",
        "log_filter_errors": "Errors Only",
        "banner_info_title": "Information",
        "banner_success_title": "Success",
        "banner_warning_title": "Warning",
        "banner_error_title": "Error",
        "banner_workflow_finished": "The CrewAI workflow finished successfully!",
        "banner_workflow_failed": "The workflow terminated with an error. Review the Live Log for details.",
        "banner_no_model_selected": "Please assign an available Ollama model to all active agents.",
        "banner_no_prompt": "Please define a Master Prompt before starting the Crew.",

        # Human-in-the-Loop & result review
        "hitl_title": "Human-in-the-Loop Review",
        "hitl_description": "Review the agents' final output and decide whether to approve or request revisions:",
        "hitl_btn_approve": "Approve Deliverable",
        "hitl_btn_approve_tooltip": "Accepts the output as satisfactory and concludes the workflow.",
        "hitl_btn_revise": "Request Revisions",
        "hitl_btn_revise_tooltip": "Sends the deliverable back to the Crew with your feedback for iterative refinement.",
        "hitl_feedback_placeholder": "Describe what needs to be revised or improved...",
        "hitl_feedback_btn_send": "Send Feedback to Crew",

        # Onboarding help & quickstart
        "help_modal_title": "Onboarding & Quickstart Guide",
        "help_step_1_title": "Step 1: Start Local LLM with Ollama",
        "help_step_1_desc": "Ensure Ollama is running ('ollama serve') and download models of your choice (e.g. 'ollama pull llama3.2' or 'ollama pull qwen2.5-coder').",
        "help_step_2_title": "Step 2: Set Workspace & Configure Agent Roles",
        "help_step_2_desc": "Pick your project directory via 'Select Directory' and assign models and tools to the respective agent cards.",
        "help_step_3_title": "Step 3: Define Master Prompt & Launch Crew",
        "help_step_3_desc": "Provide the mission statement or copy the quickstart template prompt below to begin immediately.",
        "help_example_prompt_title": "Quickstart Example Prompt:",
        "help_example_prompt_content": "Analyze the active workspace directory, generate a modular architecture overview in Markdown format, and highlight potential improvements in code quality and security.",
        "help_btn_copy_prompt": "Copy Example Prompt",
        "help_btn_copied": "Prompt copied to clipboard!",
    },
}


def t(key: str, lang: str = "de", **kwargs: Any) -> str:
    """
    Safely retrieves a localized string by key and language code.
    Provides robust fallbacks:
      1. Returns text in requested language if key exists.
      2. If missing, attempts fallback to German ('de') or English ('en').
      3. If key is completely absent, returns the formatted key itself as a legible fallback.
      4. Safely applies optional format parameters (kwargs).

    Args:
        key: Unique translation identifier key.
        lang: Language identifier ('de' or 'en', defaults to 'de').
        **kwargs: Optional string formatting arguments (e.g., used=4.2, total=12.0).

    Returns:
        The formatted localized string or readable fallback.
    """
    selected_lang = lang.lower() if lang else "de"
    fallback_lang = "en" if selected_lang == "de" else "de"

    # 1. Look in requested language
    text = TEXTS.get(selected_lang, {}).get(key)

    # 2. Look in fallback language
    if text is None:
        text = TEXTS.get(fallback_lang, {}).get(key)

    # 3. Final fallback: Cleaned key name
    if text is None:
        text = f"[{key}]"

    # 4. Safely interpolate kwargs if provided
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError, IndexError):
            # If placeholders do not match kwargs, return raw text
            return text

    return text


# =========================================================================
# Canonical Role Presets & Multilingual Role System
# =========================================================================

ROLE_PRESETS_DE: List[str] = [
    "Architekt",
    "Senior-Entwickler",
    "Rechercheur",
    "Prüfer / Reviewer",
]

ROLE_PRESETS_EN: List[str] = [
    "Architect",
    "Senior Coder",
    "Researcher",
    "Reviewer",
]

# Descriptions / Subtitles for tooltips or role info
ROLE_DESCRIPTIONS_DE: Dict[str, str] = {
    "Architekt": "Software-Architektur & Systemplanung",
    "Senior-Entwickler": "Code-Implementierung & Refactoring",
    "Rechercheur": "Dokumentations- & Fakten-Recherche",
    "Prüfer / Reviewer": "Code-Review, Qualitätskontrolle & Sicherheit",
}

ROLE_DESCRIPTIONS_EN: Dict[str, str] = {
    "Architect": "Software Architecture & System Design",
    "Senior Coder": "Code Implementation & Refactoring",
    "Researcher": "Documentation & Fact Research",
    "Reviewer": "Code Review, Quality Assurance & Security",
}

# Bidirectional role translation lookup
ROLE_TRANSLATION_MAP: Dict[str, Dict[str, str]] = {
    # DE -> EN
    "de_to_en": {
        "Architekt": "Architect",
        "Senior-Entwickler": "Senior Coder",
        "Senior Coder": "Senior Coder",
        "Entwickler": "Senior Coder",
        "Coder": "Senior Coder",
        "Rechercheur": "Researcher",
        "Researcher": "Researcher",
        "Prüfer / Reviewer": "Reviewer",
        "Prüfer": "Reviewer",
        "Reviewer": "Reviewer",
    },
    # EN -> DE
    "en_to_de": {
        "Architect": "Architekt",
        "Architekt": "Architekt",
        "Senior Coder": "Senior-Entwickler",
        "Senior-Entwickler": "Senior-Entwickler",
        "Developer": "Senior-Entwickler",
        "Coder": "Senior-Entwickler",
        "Entwickler": "Senior-Entwickler",
        "Researcher": "Rechercheur",
        "Rechercheur": "Rechercheur",
        "Reviewer": "Prüfer / Reviewer",
        "Prüfer / Reviewer": "Prüfer / Reviewer",
        "Prüfer": "Prüfer / Reviewer",
        "Auditor": "Prüfer / Reviewer",
        "Tester": "Prüfer / Reviewer",
    },
}

# Predefined Goal & Backstory templates per language and role
ROLE_TEMPLATES: Dict[str, Dict[str, Dict[str, str]]] = {
    "de": {
        "Architekt": {
            "key": "architect",
            "goal": "Entwerfe eine saubere, skalierbare und modulare Systemarchitektur.",
            "backstory": "Erfahrener Enterprise-Softwarearchitekt mit Fokus auf Wartbarkeit, saubere Schnittstellen und Robustheit.",
        },
        "Senior-Entwickler": {
            "key": "coder",
            "goal": "Implementiere fehlerfreien, performanten und standardkonformen Python-Code.",
            "backstory": "Pragmatischer Senior-Entwickler mit tiefem Verständnis für Systemintegration, Refactoring und Best Practices.",
        },
        "Rechercheur": {
            "key": "researcher",
            "goal": "Sammle präzise Hintergrundinformationen, Best Practices und relevante Code-Referenzen.",
            "backstory": "Analytischer Rechercheur mit Zugriff auf Web-Recherche und lokale Projektdateien.",
        },
        "Prüfer / Reviewer": {
            "key": "reviewer",
            "goal": "Prüfe Code und Architektur gründlich auf Fehler, Sicherheitslücken und Inkonsistenzen.",
            "backstory": "Akribischer QA- und Code-Review-Lead mit kritischem Blick für Details und Edge Cases.",
        },
    },
    "en": {
        "Architect": {
            "key": "architect",
            "goal": "Design a clean, scalable, and modular system architecture.",
            "backstory": "Experienced enterprise software architect focused on maintainability, robust interfaces, and system integrity.",
        },
        "Senior Coder": {
            "key": "coder",
            "goal": "Implement bug-free, high-performance, and compliant Python code.",
            "backstory": "Pragmatic senior developer with deep expertise in system integration, refactoring, and clean code best practices.",
        },
        "Researcher": {
            "key": "researcher",
            "goal": "Gather accurate background context, best practices, and documentation references.",
            "backstory": "Analytical researcher equipped with web search and deep workspace file inspection tools.",
        },
        "Reviewer": {
            "key": "reviewer",
            "goal": "Thoroughly review code and system architecture for defects, security vulnerabilities, and inconsistencies.",
            "backstory": "Meticulous QA and code review lead with an eagle eye for edge cases and reliability standards.",
        },
    },
}


def get_role_presets(lang: str = "de") -> List[str]:
    """Returns the list of standard role presets for the given language."""
    return list(ROLE_PRESETS_DE) if (lang or "de").lower() == "de" else list(ROLE_PRESETS_EN)


def translate_role(role_name: str, target_lang: str = "de") -> Optional[str]:
    """
    Translates a known role preset between DE and EN.
    If the role is a user-defined custom role (e.g. 'Biologe', 'Strafverteidiger'),
    returns None to indicate that the custom text should remain unchanged.
    """
    if not role_name:
        return None

    role_clean = role_name.strip()
    is_target_de = (target_lang or "de").lower() == "de"
    mapping_key = "en_to_de" if is_target_de else "de_to_en"
    mapping = ROLE_TRANSLATION_MAP.get(mapping_key, {})

    # Check direct match in mapping
    if role_clean in mapping:
        return mapping[role_clean]

    # Check case-insensitive match
    for source_key, target_val in mapping.items():
        if source_key.lower() == role_clean.lower():
            return target_val

    # If it is already a valid preset in the target language, keep it
    target_presets = ROLE_PRESETS_DE if is_target_de else ROLE_PRESETS_EN
    for p in target_presets:
        if p.lower() == role_clean.lower():
            return p

    # Custom freetext role: return None to signify no preset translation exists
    return None


def get_canonical_role_key(role_name: str) -> str:
    """
    Maps any role string (DE, EN, alias, or custom) to a canonical key:
    'architect', 'coder', 'researcher', 'reviewer', or 'custom'.
    """
    if not role_name:
        return "custom"

    r = role_name.lower().strip()
    if any(k in r for k in ("architekt", "architect", "planner", "planer")):
        return "architect"
    if any(k in r for k in ("coder", "entwickler", "developer", "programmierer")):
        return "coder"
    if any(k in r for k in ("recherche", "research", "search", "analyst")):
        return "researcher"
    if any(k in r for k in ("review", "prüf", "pruef", "qa", "audit", "tester")):
        return "reviewer"

    return "custom"


def get_role_template(role_name: str, lang: str = "de") -> Dict[str, str]:
    """
    Returns {'goal': ..., 'backstory': ...} for a given role name and target language.
    If the role is a known preset or maps to one, returns its localized preset template.
    If it is a custom role, generates a grammatically clean dynamic template in target language.
    """
    lang_code = "de" if (lang or "de").lower() == "de" else "en"
    role_clean = (role_name or "").strip()
    templates = ROLE_TEMPLATES.get(lang_code, {})

    # 1. Direct template match
    if role_clean in templates:
        return templates[role_clean]

    # 2. Check translated role match
    translated = translate_role(role_clean, target_lang=lang_code)
    if translated and translated in templates:
        return templates[translated]

    # 3. Check canonical role key match
    canon = get_canonical_role_key(role_clean)
    for p_name, t_data in templates.items():
        if t_data.get("key") == canon:
            return t_data

    # 4. Custom freetext role fallback
    if lang_code == "de":
        return {
            "key": "custom",
            "goal": f"Führe professionelle Analysen, Aufgaben und Beratungen in der Rolle als {role_clean} durch.",
            "backstory": (
                f"Ausgewiesener Fachexperte als {role_clean}. Arbeitet methodisch, detailgenau "
                f"und orientiert sich an professionellen Standards."
            ),
        }
    else:
        return {
            "key": "custom",
            "goal": f"Execute professional analysis, tasks, and consulting in the role of {role_clean}.",
            "backstory": (
                f"Dedicated domain specialist acting as {role_clean}. Works methodically, with attention "
                f"to detail and strict adherence to professional standards."
            ),
        }
