"""
Local Crew Cockpit - Main Application Window (PyQt6)
Lean coordinator orchestrating ModelPoolWidget, PipelineWidget, WorkspaceWidget,
and LogDockWidget with real-time background CrewRunner and SystemMonitorThread.
"""

import logging
import os
import threading
from typing import Any, Dict, List, Optional
import requests

from PyQt6.QtCore import QObject, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.crew_runner import CrewRunner
from core.locales import t
from core.ollama_client import OllamaClient
from core.system_monitor import SystemMonitorThread
from ui.components import (
    CrewWorkerThread,
    LogDockWidget,
    ModelPoolWidget,
    PipelineWidget,
    RunnerBridgeSignals,
    WorkspaceWidget,
)
from ui.help_dialog import CockpitHelpDialog
from ui.pipeline_card import PipelineCard
from ui.styles import apply_dark_theme

logger = logging.getLogger(__name__)


class CrewMainWindow(QMainWindow):
    """
    Main Cockpit Window (PyQt6 Coordinator).
    Orchestrates:
      - Zone 1: ModelPoolWidget
      - Zone 2: PipelineWidget
      - Zone 3: WorkspaceWidget
      - Zone 4: Master Prompt & Execution Controls
      - Right Pane: LogDockWidget
    """

    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.ollama_host = ollama_host
        self.lang = "de"

        # Core Engines & Signals
        self.ollama_client = OllamaClient(host=self.ollama_host)
        self.runner: Optional[CrewRunner] = CrewRunner(ollama_host=self.ollama_host)
        self.runner_signals = RunnerBridgeSignals()
        self.worker_thread: Optional[CrewWorkerThread] = None
        self.accumulated_tokens: int = 0
        self.current_max_tokens: int = 65536

        # Window Setup & Styling
        self.setWindowTitle("Local Crew Cockpit (PyQt6)")
        self.resize(1440, 920)
        self.setMinimumSize(1080, 720)
        apply_dark_theme(self)

        # UI & Signal Assembly
        self._build_ui()
        self._wire_signals()

        # Background Monitor Thread (Ollama status & VRAM)
        self.monitor_thread = SystemMonitorThread(
            ollama_host=self.ollama_host,
            interval=2.0,
            parent=self,
        )
        self.monitor_thread.status_updated.connect(self._on_status_updated)
        self.monitor_thread.vram_updated.connect(self._on_vram_updated)
        self.monitor_thread.start()

        QTimer.singleShot(50, self.model_pool.load_installed_models)
        QTimer.singleShot(150, self._update_dynamic_token_limit)

    # -------------------------------------------------------------------------
    # UI Construction
    # -------------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(10, 8, 10, 10)
        root_layout.setSpacing(8)

        # Top Header Bar
        root_layout.addWidget(self._build_header_bar())

        # Main Horizontal Splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(4)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        # Left Column Splitter (Zones 1-4)
        self.left_splitter = QSplitter(Qt.Orientation.Vertical)
        self.left_splitter.setHandleWidth(4)
        self.left_splitter.setChildrenCollapsible(False)
        self.left_splitter.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        self.model_pool = ModelPoolWidget(
            parent=self,
            ollama_client=self.ollama_client,
            ollama_host=self.ollama_host,
            lang=self.lang,
        )
        self.pipeline_widget = PipelineWidget(parent=self, lang=self.lang)
        self.workspace_widget = WorkspaceWidget(parent=self, lang=self.lang)
        self.zone4_master_prompt = self._build_zone4_master_prompt()

        self.left_splitter.addWidget(self.model_pool)
        self.left_splitter.addWidget(self.pipeline_widget)
        self.left_splitter.addWidget(self.workspace_widget)
        self.left_splitter.addWidget(self.zone4_master_prompt)
        self.left_splitter.setSizes([200, 260, 220, 220])

        # Right Column (LogDockWidget)
        self.log_dock = LogDockWidget(parent=self, lang=self.lang)

        self.main_splitter.addWidget(self.left_splitter)
        self.main_splitter.addWidget(self.log_dock)
        self.main_splitter.setSizes([780, 660])

        root_layout.addWidget(self.main_splitter, stretch=1)

    def _build_header_bar(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 6px; padding: 4px; }"
        )
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(10)

        self.lbl_brand = QLabel("🛸 Local Crew Cockpit")
        self.lbl_brand.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.lbl_brand.setStyleSheet("color: #60a5fa;")
        layout.addWidget(self.lbl_brand)

        self.lbl_ollama_status = QLabel("Ollama: Prüfe...")
        self.lbl_ollama_status.setStyleSheet(
            "background-color: #334155; color: #cbd5e1; border: 1px solid #475569; "
            "border-radius: 4px; padding: 2px 8px; font-weight: bold; font-size: 11px;"
        )
        layout.addWidget(self.lbl_ollama_status)

        self.lbl_vram = QLabel("VRAM: -- / -- GB")
        self.lbl_vram.setStyleSheet(
            "background-color: #0f172a; color: #38bdf8; border: 1px solid #1e293b; "
            "border-radius: 4px; padding: 2px 8px; font-weight: bold; font-size: 11px;"
        )
        layout.addWidget(self.lbl_vram)

        self.lbl_tokens = QLabel("Tokens: 0 / 64k")
        self.lbl_tokens.setStyleSheet(
            "background-color: #0f172a; color: #a78bfa; border: 1px solid #1e293b; "
            "border-radius: 4px; padding: 2px 8px; font-weight: bold; font-size: 11px;"
        )
        layout.addWidget(self.lbl_tokens)

        layout.addStretch()

        self.btn_lang = QPushButton("🌐 DE" if self.lang == "de" else "🌐 EN")
        self.btn_lang.setStyleSheet(
            "background-color: #1e293b; color: #f8fafc; border: 1px solid #334155; "
            "border-radius: 4px; padding: 4px 10px; font-weight: bold; font-size: 11px;"
        )
        self.btn_lang.setToolTip(t("header_lang_tooltip", lang=self.lang))
        self.btn_lang.clicked.connect(self._toggle_language)
        layout.addWidget(self.btn_lang)

        self.btn_reset = QPushButton("🔄 " + t("header_btn_reset", lang=self.lang))
        self.btn_reset.setStyleSheet(
            "background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; "
            "border-radius: 4px; padding: 4px 10px; font-size: 11px;"
        )
        self.btn_reset.setToolTip(t("header_btn_reset_tooltip", lang=self.lang))
        self.btn_reset.clicked.connect(self._on_reset_cockpit)
        layout.addWidget(self.btn_reset)

        self.btn_help = QPushButton("ℹ️ " + t("header_btn_help", lang=self.lang))
        self.btn_help.setStyleSheet(
            "background-color: #1e293b; color: #38bdf8; border: 1px solid #0284c7; "
            "border-radius: 4px; padding: 4px 10px; font-weight: bold; font-size: 11px;"
        )
        self.btn_help.setToolTip(t("header_btn_help_tooltip", lang=self.lang))
        self.btn_help.clicked.connect(self._open_help_dialog)
        layout.addWidget(self.btn_help)

        return frame

    def _build_zone4_master_prompt(self) -> QWidget:
        container = QFrame()
        container.setStyleSheet(
            "QFrame { background-color: #0b0f19; border: 1px solid #1e293b; border-radius: 6px; }"
        )
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.lbl_zone4_title = QLabel(
            "🎯 " + ("Master-Prompt & Zieldefinition" if self.lang == "de" else "Master Prompt & Mission Objective")
        )
        self.lbl_zone4_title.setStyleSheet("font-weight: bold; font-size: 12px; color: #facc15;")
        layout.addWidget(self.lbl_zone4_title)

        self.txt_prompt = QTextEdit()
        default_prompt = (
            "1. [Architekt]: Analysiere die Projektstruktur und erstelle einen modularen Architekturplan.\n"
            "2. [Senior-Entwickler]: Implementiere die fehlenden Kernfunktionen und Module.\n"
            "3. [Senior-Entwickler]: Optimiere und dokumentiere die Codebasis sowie Schnittstellen.\n"
            "4. [Prüfer / Reviewer]: Führe eine Qualitäts- und Sicherheitsprüfung durch."
        )
        self.txt_prompt.setPlaceholderText(
            "Beschreibe die Mission für deine Crew...\n"
            "Tipp: Nummerierte Abschnitte wie '1. [Architekt]: ... 2. [Entwickler]: ...' werden automatisch den Agenten zugewiesen!"
            if self.lang == "de"
            else "Define the mission objective for your crew..."
        )
        self.txt_prompt.setPlainText(default_prompt)
        self.txt_prompt.setStyleSheet(
            "background-color: #05080e; color: #f8fafc; border: 1px solid #334155; border-radius: 4px; padding: 6px;"
        )
        layout.addWidget(self.txt_prompt, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_start = QPushButton("▶ " + t("btn_start_crew", lang=self.lang))
        self.btn_start.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.btn_start.setEnabled(False)
        self.btn_start.setStyleSheet(
            "QPushButton { background-color: #16a34a; color: #ffffff; border-radius: 5px; padding: 8px 16px; font-weight: bold; } "
            "QPushButton:disabled { background-color: #1e293b; color: #64748b; border: 1px solid #334155; }"
        )
        self.btn_start.setToolTip(
            "⚠️ Bitte zuerst einen Projektordner auswählen!"
            if self.lang == "de"
            else "⚠️ Please select a workspace directory first!"
        )
        self.btn_start.clicked.connect(self._start_workflow)
        btn_row.addWidget(self.btn_start, stretch=2)

        self.btn_stop = QPushButton("⏹ " + t("btn_stop_crew", lang=self.lang))
        self.btn_stop.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(
            "background-color: #7f1d1d; color: #fca5a5; border-radius: 5px; padding: 8px 14px; font-weight: bold;"
        )
        self.btn_stop.clicked.connect(self._stop_workflow)
        btn_row.addWidget(self.btn_stop, stretch=1)

        layout.addLayout(btn_row)
        return container

    # -------------------------------------------------------------------------
    # Signal Wiring & Event Dispatching
    # -------------------------------------------------------------------------

    def _wire_signals(self) -> None:
        # Cross-component wiring
        self.model_pool.model_add_requested.connect(self.pipeline_widget.add_pipeline_card)
        self.model_pool.log_emitted.connect(self.log_dock.append_log)

        self.pipeline_widget.log_emitted.connect(self.log_dock.append_log)

        self.workspace_widget.workspace_changed.connect(self._on_workspace_changed)
        self.workspace_widget.log_emitted.connect(self.log_dock.append_log)

        self.pipeline_widget.order_changed.connect(self._update_dynamic_token_limit)
        self.model_pool.model_add_requested.connect(lambda _: QTimer.singleShot(60, self._update_dynamic_token_limit))

        self.log_dock.revision_requested.connect(lambda fb: self._start_workflow(revision_feedback=fb))
        self.log_dock.result_accepted.connect(self._on_result_accepted)

        # Runner bridge signals to GUI slots
        self.runner_signals.log_received.connect(self.log_dock.append_log)
        self.runner_signals.step_received.connect(self._on_step_received)
        self.runner_signals.card_status_received.connect(self.pipeline_widget.update_card_status)
        self.runner_signals.card_thought_received.connect(self.pipeline_widget.append_card_thought)
        self.runner_signals.task_completed.connect(self._on_task_completed)
        self.runner_signals.banner_received.connect(
            lambda msg, typ: self.log_dock.append_log(f"[{typ.upper()}] {msg}", typ)
        )
        self.runner_signals.result_received.connect(self._on_result_received)
        self.runner_signals.tokens_updated.connect(self._on_tokens_updated)
        self.runner_signals.cancelled.connect(self._on_workflow_cancelled)
        self.runner_signals.finished.connect(self._on_runner_finished)

    def _on_workspace_changed(self, path: str) -> None:
        self._update_start_button_state()

    def _update_start_button_state(self) -> None:
        is_running = (
            (self.runner and getattr(self.runner, "is_running", False))
            or (self.worker_thread is not None and self.worker_thread.isRunning())
        )
        if is_running:
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            return

        has_ws = self.workspace_widget.has_valid_workspace()
        self.btn_start.setEnabled(has_ws)
        self.btn_stop.setEnabled(False)
        self.btn_start.setToolTip(
            "Orchestrierte CrewAI-Pipeline ausführen"
            if has_ws
            else ("⚠️ Bitte zuerst einen Projektordner auswählen!" if self.lang == "de" else "⚠️ Please select a workspace directory first!")
        )

    # -------------------------------------------------------------------------
    # Workflow Execution & Thread Lifecycle
    # -------------------------------------------------------------------------

    def _start_workflow(self, revision_feedback: Optional[str] = None) -> None:
        if not self.workspace_widget.has_valid_workspace():
            QMessageBox.warning(
                self,
                "Projektordner erforderlich" if self.lang == "de" else "Workspace Required",
                "⚠️ Bitte wähle zuerst einen Projektordner aus oder erstelle einen neuen Ordner!"
                if self.lang == "de"
                else "⚠️ Please select or create a project workspace first!",
            )
            self.workspace_widget.choose_workspace_dialog()
            return

        if self.pipeline_widget.is_empty():
            QMessageBox.warning(
                self,
                "Kein Team definiert" if self.lang == "de" else "No Team Configured",
                "Bitte füge mindestens einen Agenten über Zone 1 zum Team hinzu!"
                if self.lang == "de"
                else "Please add at least one agent from Zone 1 to your pipeline team!",
            )
            return

        prompt = self.txt_prompt.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(
                self,
                "Prompt erforderlich" if self.lang == "de" else "Prompt Required",
                "Bitte formuliere ein Ziel oder eine Aufgabenstellung im Master-Prompt."
                if self.lang == "de"
                else "Please define a mission objective in the Master Prompt field.",
            )
            return

        configs = self.pipeline_widget.get_pipeline_configs()
        workspace = self.workspace_widget.get_workspace() or ""
        included_files = self.workspace_widget.get_included_files()

        if self.worker_thread is not None and self.worker_thread.isRunning():
            if self.runner:
                self.runner.cancel()
            self.worker_thread.quit()
            if not self.worker_thread.wait(300):
                self.worker_thread.terminate()
                self.worker_thread.wait(200)

        self.runner = CrewRunner(ollama_host=self.ollama_host)
        self.accumulated_tokens = 0
        self._update_dynamic_token_limit()

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.pipeline_widget.reset_card_statuses("Bereit" if self.lang == "de" else "Ready", color_key="gray")

        callbacks = {
            "on_log": lambda text, tag="": self.runner_signals.log_received.emit(text, tag),
            "on_step": lambda a, st, det, tok: self.runner_signals.step_received.emit(a, st, det, tok),
            "on_card_status": lambda m, st, det="": self.runner_signals.card_status_received.emit(m, st, det),
            "on_card_thought": lambda m, th: self.runner_signals.card_thought_received.emit(m, th),
            "on_task_completed": lambda m, out: self.runner_signals.task_completed.emit(m, out),
            "on_banner": lambda msg, typ="info": self.runner_signals.banner_received.emit(msg, typ),
            "on_result": lambda res: self.runner_signals.result_received.emit(res),
            "on_tokens": lambda used, max_t=None: self.runner_signals.tokens_updated.emit(
                used, max_t if max_t is not None else self.current_max_tokens
            ),
            "on_cancelled": lambda: self.runner_signals.cancelled.emit(),
            "on_finish": lambda ok, msg="": self.runner_signals.finished.emit(ok, msg),
        }

        self.log_dock.append_log("=" * 60, "SYSTEM")
        self.log_dock.append_log("🚀 CrewAI Workflow wird gestartet...", "SYSTEM")

        self.worker_thread = CrewWorkerThread(
            runner=self.runner,
            model_configs=configs,
            master_prompt=prompt,
            workspace_path=workspace,
            included_files=included_files,
            callbacks=callbacks,
            revision_feedback=revision_feedback,
            parent=self,
        )
        self.worker_thread.start()

    def _stop_workflow(self) -> None:
        self.log_dock.append_log(
            "[ABBRUCH] Ausführung wurde vom Benutzer abgebrochen. System ist wieder startklar.", "WARNING"
        )
        if self.runner:
            self.runner.cancel()
        if self.worker_thread is not None and self.worker_thread.isRunning():
            self.worker_thread.quit()
            if not self.worker_thread.wait(400):
                self.worker_thread.terminate()
                self.worker_thread.wait(200)
        self._reset_ui_after_cancellation()

    def _reset_ui_after_cancellation(self) -> None:
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.pipeline_widget.reset_card_statuses("Bereit" if self.lang == "de" else "Ready", color_key="gray")

    def _on_workflow_cancelled(self) -> None:
        if self.worker_thread is not None and self.worker_thread.isRunning():
            self.worker_thread.quit()
            if not self.worker_thread.wait(400):
                self.worker_thread.terminate()
                self.worker_thread.wait(200)
        self._reset_ui_after_cancellation()

    def _on_step_received(self, agent_name: str, step_type: str, details: str, tokens: int) -> None:
        if tokens > 0:
            self._on_tokens_updated(tokens)

    def _on_task_completed(self, model_name: str, task_output: str) -> None:
        if self.pipeline_widget.set_task_completed(model_name, task_output):
            self.log_dock.append_log(f"Drawer für Agent '{model_name}' mit Task-Ergebnis befüllt.", "AGENT")

    def _on_result_received(self, result_text: str) -> None:
        self.log_dock.set_result(result_text)
        self.log_dock.append_log("Finales Ergebnis empfangen und eingetragen.", "INFO")

    def _on_tokens_updated(self, used_tokens: int, max_tokens: int = 65536) -> None:
        if max_tokens > 0:
            self.current_max_tokens = max_tokens
        self.accumulated_tokens = used_tokens
        formatted_tokens = f"{used_tokens:,}".replace(",", ".")
        max_k = self.current_max_tokens // 1024 if self.current_max_tokens >= 1024 else self.current_max_tokens
        self.lbl_tokens.setText(f"Tokens: {formatted_tokens} / {max_k}k")

    def _on_runner_finished(self, success: bool, message: str) -> None:
        self.btn_stop.setEnabled(False)
        self._update_start_button_state()

        if not success and ("abgebrochen" in message.lower() or "cancel" in message.lower()):
            self._reset_ui_after_cancellation()
            return

        self.pipeline_widget.reset_card_statuses("✓ Fertig" if success else "Bereit", color_key="green" if success else "gray")
        self.pipeline_widget.ensure_fallback_output(
            success, fallback_text=self.log_dock.get_result().strip(), error_msg=message
        )

        status_text = "Erfolgreich abgeschlossen" if success else f"Beendet ({message})"
        self.log_dock.append_log(f"🏁 Workflow {status_text}.", "INFO" if success else "ERROR")

    # -------------------------------------------------------------------------
    # Backward Compatibility Delegates & Properties
    # -------------------------------------------------------------------------

    def add_pipeline_card(self, model_name: str, role: Optional[str] = None) -> PipelineCard:
        card = self.pipeline_widget.add_pipeline_card(model_name, role)
        QTimer.singleShot(60, self._update_dynamic_token_limit)
        return card

    @property
    def current_workspace(self) -> Optional[str]:
        return self.workspace_widget.get_workspace()

    @current_workspace.setter
    def current_workspace(self, val: Optional[str]) -> None:
        if val:
            self.workspace_widget.set_workspace(val)

    @property
    def pipeline_cards(self) -> List[PipelineCard]:
        return self.pipeline_widget.pipeline_cards

    @property
    def file_tree(self) -> Any:
        return self.workspace_widget.file_tree

    @property
    def txt_log(self) -> QTextEdit:
        return self.log_dock.txt_log

    @property
    def txt_result(self) -> QTextEdit:
        return self.log_dock.txt_result

    @property
    def master_prompt_text(self) -> QTextEdit:
        return self.txt_prompt

    @property
    def installed_models(self) -> List[Dict[str, Any]]:
        return self.model_pool.installed_models

    # -------------------------------------------------------------------------
    # Monitor Slots & UI Utilities
    # -------------------------------------------------------------------------

    def _on_status_updated(self, is_online: bool) -> None:
        if is_online:
            self.lbl_ollama_status.setText(t("header_ollama_online", lang=self.lang))
            self.lbl_ollama_status.setStyleSheet(
                "background-color: #14532d; color: #86efac; border: 1px solid #16a34a; "
                "border-radius: 4px; padding: 2px 8px; font-weight: bold; font-size: 11px;"
            )
            self.lbl_ollama_status.setToolTip(t("header_ollama_tooltip_online", lang=self.lang))
        else:
            self.lbl_ollama_status.setText(t("header_ollama_offline", lang=self.lang))
            self.lbl_ollama_status.setStyleSheet(
                "background-color: #7f1d1d; color: #fca5a5; border: 1px solid #ef4444; "
                "border-radius: 4px; padding: 2px 8px; font-weight: bold; font-size: 11px;"
            )
            self.lbl_ollama_status.setToolTip(t("header_ollama_tooltip_offline", lang=self.lang))

    def _on_vram_updated(self, used_gb: float, total_gb: float, percent: int) -> None:
        self.lbl_vram.setText(f"VRAM: {used_gb:.1f} / {total_gb:.1f} GB ({percent}%)")

    def _on_result_accepted(self) -> None:
        """
        Handler when user clicks [✓ Ergebnis abnehmen] in LogDockWidget.
        1. Clears master prompt text input.
        2. Clears live activity log and sets initial message.
        3. Clears thoughts/drawers and resets card status to 'Bereit'.
        4. Resets token budget badge to dynamic limit.
        5. Sends asynchronous POST to Ollama (/api/generate with keep_alive: 0)
           to unload model weights from GPU VRAM.
        Pipeline team cards and workspace path remain intact.
        """
        self.txt_prompt.clear()
        self.log_dock.clear_log()
        self.log_dock.append_log(
            "[SYSTEM] Ergebnis abgenommen. Arbeitsbereich und Speicher wurden für die nächste Aufgabe zurückgesetzt.",
            "SYSTEM",
        )
        self.pipeline_widget.clear_agent_states()
        self.accumulated_tokens = 0
        self._update_dynamic_token_limit()

        def _unload_vram() -> None:
            models_to_unload = set()
            for cfg in self.pipeline_widget.get_pipeline_configs():
                m = cfg.get("model_name")
                if m:
                    models_to_unload.add(m)
            try:
                ps_url = f"{self.ollama_host.rstrip('/')}/api/ps"
                ps_resp = requests.get(ps_url, timeout=2.0)
                if ps_resp.status_code == 200:
                    for item in ps_resp.json().get("models", []):
                        name = item.get("model") or item.get("name")
                        if name:
                            models_to_unload.add(name)
            except Exception as e:
                logger.debug("Failed querying /api/ps: %s", e)

            for model_name in models_to_unload:
                try:
                    requests.post(
                        f"{self.ollama_host.rstrip('/')}/api/generate",
                        json={"model": model_name, "keep_alive": 0},
                        timeout=3.0,
                    )
                    logger.info("Unloaded model '%s' from VRAM (keep_alive: 0).", model_name)
                except Exception as e:
                    logger.debug("Failed unloading model '%s': %s", model_name, e)

        threading.Thread(target=_unload_vram, daemon=True, name="Ollama-VRAM-Unload").start()

    def _on_reset_cockpit(self) -> None:
        self.log_dock.clear_log()
        self.log_dock.clear_result()
        self.accumulated_tokens = 0
        self.pipeline_widget.reset_card_statuses("Bereit" if self.lang == "de" else "Ready", color_key="gray")
        self.pipeline_widget.clear_agent_states()
        self._update_dynamic_token_limit()
        self.log_dock.append_log("Cockpit-Zustände wurden zurückgesetzt.", "SYSTEM")

    def _update_dynamic_token_limit(self) -> None:
        """
        Dynamically calculates and updates the token limit badge based on:
        1. Detected GPU VRAM from monitor_thread / NVML.
        2. Configured agents in the pipeline and their KV-cache headroom.
        """
        configs = self.pipeline_widget.get_pipeline_configs()
        from core.crew_runner import calculate_hardware_context_limit

        vram_total = None
        if hasattr(self, "monitor_thread") and self.monitor_thread and hasattr(self.monitor_thread, "monitor"):
            mem = self.monitor_thread.monitor.get_memory_status()
            if mem.get("total_gb", 0) > 0:
                vram_total = float(mem["total_gb"])

        limit = calculate_hardware_context_limit(configs, host=self.ollama_host, vram_total_override=vram_total)
        self.current_max_tokens = limit
        max_k = self.current_max_tokens // 1024 if self.current_max_tokens >= 1024 else self.current_max_tokens
        if self.accumulated_tokens == 0:
            self.lbl_tokens.setText(f"Tokens: 0 / {max_k}k")
        else:
            formatted = f"{self.accumulated_tokens:,}".replace(",", ".")
            self.lbl_tokens.setText(f"Tokens: {formatted} / {max_k}k")

    def _open_help_dialog(self) -> None:
        dlg = CockpitHelpDialog(parent=self, lang=self.lang)
        dlg.exec()

    def _toggle_language(self) -> None:
        self.lang = "en" if self.lang == "de" else "de"
        self.btn_lang.setText("🌐 DE" if self.lang == "de" else "🌐 EN")
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.btn_lang.setToolTip(t("header_lang_tooltip", lang=self.lang))
        self.btn_reset.setText("🔄 " + t("header_btn_reset", lang=self.lang))
        self.btn_reset.setToolTip(t("header_btn_reset_tooltip", lang=self.lang))
        self.btn_help.setText("ℹ️ " + t("header_btn_help", lang=self.lang))
        self.btn_help.setToolTip(t("header_btn_help_tooltip", lang=self.lang))

        self.model_pool.set_language(self.lang)
        self.pipeline_widget.set_language(self.lang)
        self.workspace_widget.set_language(self.lang)
        self.log_dock.set_language(self.lang)

        self.lbl_zone4_title.setText(
            "🎯 " + ("Master-Prompt & Zieldefinition" if self.lang == "de" else "Master Prompt & Mission Objective")
        )
        self.btn_start.setText("▶ " + t("btn_start_crew", lang=self.lang))
        self.btn_stop.setText("⏹ " + t("btn_stop_crew", lang=self.lang))
        self._update_start_button_state()

    def closeEvent(self, event) -> None:
        if hasattr(self, "monitor_thread") and self.monitor_thread is not None:
            self.monitor_thread.stop()
        if hasattr(self, "model_pool") and self.model_pool is not None:
            self.model_pool.stop()
        if hasattr(self, "worker_thread") and self.worker_thread is not None and self.worker_thread.isRunning():
            if hasattr(self, "runner") and self.runner:
                self.runner.cancel()
            self.worker_thread.quit()
            if not self.worker_thread.wait(400):
                self.worker_thread.terminate()
        elif hasattr(self, "runner") and self.runner and getattr(self.runner, "is_running", False):
            self.runner.cancel()
        super().closeEvent(event)


# Forward-compatible alias
MainWindow = CrewMainWindow
