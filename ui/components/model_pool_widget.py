"""
Local Crew Cockpit - Model Pool Component (Zone 1)
Manages the model library, asynchronous model listing, live model pull/download with progress,
strict tabular column layout with header legend, and capability/VRAM badges.
"""

import logging
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QObject, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.locales import t
from core.model_knowledge import (
    estimate_model_vram_gb,
    get_capability_badge,
    get_role_recommendation_badge,
)
from core.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class ModelPullWorker(QThread):
    """Background worker thread for downloading/pulling Ollama models without blocking the UI."""

    progress = pyqtSignal(str, int, int)
    progress_updated = pyqtSignal(str, int, float, float)
    finished_pull = pyqtSignal(bool, str, str)

    def __init__(self, client: OllamaClient, model_name: str, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.client = client
        self.model_name = model_name

    def run(self) -> None:
        def callback(status: str, completed: int, total: int) -> None:
            self.progress.emit(status, completed, total)

        try:
            result = self.client.pull_model_stream(self.model_name, callback=callback)
            if result:
                self.finished_pull.emit(True, self.model_name, result)
            else:
                self.finished_pull.emit(False, self.model_name, "Download failed.")
        except Exception as exc:
            self.finished_pull.emit(False, self.model_name, str(exc))


class SingleModelPullWorker(QThread):
    """
    Background worker thread executing an inline update pull for a specific model.
    """

    progress_updated = pyqtSignal(str, int, float, float)
    finished_pull = pyqtSignal(bool, str, str)

    def __init__(
        self,
        client: OllamaClient,
        model_name: str,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.client = client
        self.model_name = model_name

    def run(self) -> None:
        try:
            res = self.client.pull_model_stream(self.model_name)
            if res:
                self.finished_pull.emit(True, self.model_name, res)
            else:
                self.finished_pull.emit(False, self.model_name, "Download failed")
        except Exception as exc:
            self.finished_pull.emit(False, self.model_name, str(exc))


class ModelUpdateCheckWorker(QThread):
    """
    Background worker thread checking remote Ollama registry manifests
    for model updates without blocking the UI.
    """

    model_checked = pyqtSignal(str, bool)

    def __init__(
        self,
        client: OllamaClient,
        models: List[Dict[str, Any]],
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.client = client
        self.models = list(models)
        self._is_stopped = False

    def stop(self) -> None:
        self._is_stopped = True

    def run(self) -> None:
        for m in self.models:
            if self._is_stopped:
                break
            name = m.get("name")
            if not name:
                continue
            digest = m.get("digest")
            has_update = self.client.check_model_update(name, local_digest=digest)
            if not self._is_stopped:
                self.model_checked.emit(name, has_update)


class ModelListWorker(QThread):
    """
    Background worker thread fetching installed Ollama models asynchronously
    to prevent GUI freezes during model library queries.
    """

    models_loaded = pyqtSignal(list)

    def __init__(self, client: OllamaClient, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.client = client

    def run(self) -> None:
        try:
            models = self.client.get_installed_models()
            self.models_loaded.emit(models)
        except Exception as exc:
            logger.debug("Async model fetch error: %s", exc)
            self.models_loaded.emit([])


class ModelPoolWidget(QFrame):
    """
    Zone 1: Model Pool & Library Component.
    Displays local installed Ollama models in a strict tabular layout with fixed column widths,
    legend header, live model pull/download, and asynchronous refresh button.
    """

    model_add_requested = pyqtSignal(str)
    log_emitted = pyqtSignal(str, str)
    models_updated = pyqtSignal(list)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        ollama_client: Optional[OllamaClient] = None,
        ollama_host: str = "http://localhost:11434",
        lang: str = "de",
    ) -> None:
        super().__init__(parent)
        self.ollama_host = ollama_host
        self.ollama_client = ollama_client or OllamaClient(host=self.ollama_host)
        self.lang = lang

        # Connect client signals for streaming progress and logs
        self.ollama_client.progress_updated.connect(self._on_progress_updated)
        self.ollama_client.log_emitted.connect(self._on_client_log_emitted)

        self.installed_models: List[Dict[str, Any]] = []
        self._model_rows: Dict[str, Dict[str, Any]] = {}
        self._update_check_worker: Optional[ModelUpdateCheckWorker] = None
        self._active_pull_workers: List[SingleModelPullWorker] = []
        self.is_pulling: bool = False
        self.pull_worker: Optional[ModelPullWorker] = None
        self.model_list_worker: Optional[ModelListWorker] = None

        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet(
            "QFrame { background-color: #0b0f19; border: 1px solid #1e293b; border-radius: 6px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header row
        top_header = QHBoxLayout()
        self.lbl_title = QLabel("📦 " + t("pipeline_pool_title", lang=self.lang))
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 12px; color: #38bdf8;")
        top_header.addWidget(self.lbl_title)
        top_header.addStretch()
        layout.addLayout(top_header)

        # Model pull & reload action row
        pull_row = QHBoxLayout()
        pull_row.setSpacing(6)

        self.txt_pull_model = QLineEdit()
        self.txt_pull_model.setPlaceholderText(
            "Modellbezeichner eingeben (z. B. qwen2.5-coder:14b, deepseek-r1:8b)..."
            if self.lang == "de"
            else "Enter model tag (e.g. qwen2.5-coder:14b, deepseek-r1:8b)..."
        )
        self.txt_pull_model.setStyleSheet(
            "background-color: #0f172a; color: #f8fafc; border: 1px solid #334155; "
            "border-radius: 4px; padding: 4px 8px; font-size: 11px;"
        )
        self.txt_pull_model.returnPressed.connect(self.start_model_pull)
        pull_row.addWidget(self.txt_pull_model, stretch=1)

        self.btn_pull = QPushButton("⬇️ " + ("Installieren" if self.lang == "de" else "Pull"))
        self.btn_pull.setStyleSheet(
            "QPushButton { background-color: #15803d; color: #ffffff; font-weight: bold; "
            "border-radius: 4px; padding: 4px 10px; font-size: 11px; } "
            "QPushButton:hover { background-color: #16a34a; }"
        )
        self.btn_pull.clicked.connect(self.start_model_pull)
        pull_row.addWidget(self.btn_pull)

        # Reload / Refresh button
        self.btn_refresh = QPushButton("🔄 " + ("Modelle neu laden" if self.lang == "de" else "Reload Models"))
        self.btn_refresh.setToolTip(
            "Installierte Modelle asynchron aus Ollama abrufen"
            if self.lang == "de"
            else "Asynchronously refresh installed models from Ollama"
        )
        self.btn_refresh.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; "
            "border-radius: 4px; padding: 4px 10px; font-weight: bold; font-size: 11px; } "
            "QPushButton:hover { background-color: #334155; color: #60a5fa; border-color: #60a5fa; }"
        )
        self.btn_refresh.clicked.connect(self.load_installed_models)
        pull_row.addWidget(self.btn_refresh)

        self.btn_pull_info = QPushButton("ℹ️")
        self.btn_pull_info.setToolTip(
            "Hilfe zu Ollama-Modellnamen & Speicherort"
            if self.lang == "de"
            else "Help on Ollama model tags"
        )
        self.btn_pull_info.setStyleSheet(
            "background-color: #1e293b; color: #38bdf8; border: 1px solid #334155; "
            "border-radius: 4px; padding: 4px 8px; font-size: 11px;"
        )
        self.btn_pull_info.clicked.connect(self._show_pull_help)
        pull_row.addWidget(self.btn_pull_info)

        layout.addLayout(pull_row)

        # Pull progress bar (hidden by default)
        self.pull_progress_bar = QProgressBar()
        self.pull_progress_bar.setStyleSheet(
            "QProgressBar { background-color: #1e293b; color: #f8fafc; border: 1px solid #334155; "
            "border-radius: 4px; text-align: center; } "
            "QProgressBar::chunk { background-color: #2563eb; }"
        )
        self.pull_progress_bar.setRange(0, 100)
        self.pull_progress_bar.setValue(0)
        self.pull_progress_bar.hide()
        layout.addWidget(self.pull_progress_bar)

        # Tabular Column Legend Header
        legend_frame = QFrame()
        legend_frame.setStyleSheet(
            "QFrame { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 4px; }"
        )
        legend_layout = QHBoxLayout(legend_frame)
        legend_layout.setContentsMargins(8, 4, 8, 4)
        legend_layout.setSpacing(6)

        # Spalte 1: Modellname (flexible Restbreite)
        self.lbl_hdr_name = QLabel("Modellname" if self.lang == "de" else "Model Name")
        self.lbl_hdr_name.setStyleSheet("color: #64748b; font-size: 11px; font-weight: bold;")
        legend_layout.addWidget(self.lbl_hdr_name, stretch=1)

        # Spalte 2: Update-Status (feste Breite ~140px, zentriert)
        self.lbl_hdr_update = QLabel("Update-Status" if self.lang == "de" else "Update Status")
        self.lbl_hdr_update.setFixedWidth(140)
        self.lbl_hdr_update.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_hdr_update.setStyleSheet("color: #64748b; font-size: 11px; font-weight: bold;")
        legend_layout.addWidget(self.lbl_hdr_update)

        # Spalte 3: Festplattengröße (~75px, zentriert)
        self.lbl_hdr_size = QLabel("Größe" if self.lang == "de" else "Size")
        self.lbl_hdr_size.setFixedWidth(75)
        self.lbl_hdr_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_hdr_size.setStyleSheet("color: #64748b; font-size: 11px; font-weight: bold;")
        legend_layout.addWidget(self.lbl_hdr_size)

        # Spalte 3: VRAM-Bedarf (~110px, zentriert)
        self.lbl_hdr_vram = QLabel("VRAM-Bedarf" if self.lang == "de" else "VRAM Est.")
        self.lbl_hdr_vram.setFixedWidth(110)
        self.lbl_hdr_vram.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_hdr_vram.setStyleSheet("color: #64748b; font-size: 11px; font-weight: bold;")
        legend_layout.addWidget(self.lbl_hdr_vram)

        # Spalte 4: Primäre Fähigkeit (~120px, zentriert)
        self.lbl_hdr_cap = QLabel("Fähigkeiten" if self.lang == "de" else "Capabilities")
        self.lbl_hdr_cap.setFixedWidth(120)
        self.lbl_hdr_cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_hdr_cap.setStyleSheet("color: #64748b; font-size: 11px; font-weight: bold;")
        legend_layout.addWidget(self.lbl_hdr_cap)

        # Spalte 5: Rollen-Badge (~115px, zentriert)
        self.lbl_hdr_role = QLabel("Empfohlene Rolle" if self.lang == "de" else "Recommended Role")
        self.lbl_hdr_role.setFixedWidth(115)
        self.lbl_hdr_role.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_hdr_role.setStyleSheet("color: #64748b; font-size: 11px; font-weight: bold;")
        legend_layout.addWidget(self.lbl_hdr_role)

        # Spalte 6: Aktions-Button (~145px, zentriert)
        self.lbl_hdr_action = QLabel("Aktion" if self.lang == "de" else "Action")
        self.lbl_hdr_action.setFixedWidth(145)
        self.lbl_hdr_action.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_hdr_action.setStyleSheet("color: #64748b; font-size: 11px; font-weight: bold;")
        legend_layout.addWidget(self.lbl_hdr_action)

        layout.addWidget(legend_frame)

        # Scrollable pool list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        if scroll.viewport():
            scroll.viewport().setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        self.pool_list_widget = QWidget()
        self.pool_list_layout = QVBoxLayout(self.pool_list_widget)
        self.pool_list_layout.setContentsMargins(0, 0, 0, 0)
        self.pool_list_layout.setSpacing(4)
        self.pool_list_layout.addStretch()

        scroll.setWidget(self.pool_list_widget)
        layout.addWidget(scroll, stretch=1)

    def load_installed_models(self) -> None:
        """Initiates asynchronous fetching of installed Ollama models without blocking GUI."""
        if self.model_list_worker is not None and self.model_list_worker.isRunning():
            return

        self.btn_refresh.setEnabled(False)
        self.model_list_worker = ModelListWorker(self.ollama_client, parent=self)
        self.model_list_worker.models_loaded.connect(self._on_models_loaded)
        self.model_list_worker.start()

    def _on_models_loaded(self, models: List[Dict[str, Any]]) -> None:
        self.btn_refresh.setEnabled(True)
        self.populate_model_pool(models)

    def populate_model_pool(self, models: List[Dict[str, Any]]) -> None:
        """
        Populates scroll list with strict tabular rows corresponding exactly
        to the legend column header layout.
        """
        self.installed_models = models
        self.models_updated.emit(models)

        if self._update_check_worker is not None and self._update_check_worker.isRunning():
            self._update_check_worker.stop()
            self._update_check_worker.wait(200)
        self._model_rows.clear()

        self.pool_list_widget.setUpdatesEnabled(False)
        try:
            # Clear existing items
            while self.pool_list_layout.count() > 1:
                child = self.pool_list_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            if not self.installed_models:
                empty_lbl = QLabel(
                    "Keine Modelle gefunden. Bitte stelle sicher, dass Ollama läuft."
                    if self.lang == "de"
                    else "No models found. Make sure Ollama daemon is running."
                )
                empty_lbl.setStyleSheet("color: #64748b; padding: 12px;")
                self.pool_list_layout.insertWidget(0, empty_lbl)
                return

            for model in self.installed_models:
                name = model.get("name", "unknown")
                size_gb = model.get("size_gb", 0.0)
                vram_gb = estimate_model_vram_gb(name)

                row = QFrame()
                row.setStyleSheet(
                    "QFrame { background-color: #1e293b; border: 1px solid #334155; "
                    "border-radius: 4px; padding: 2px; } "
                    "QFrame:hover { border-color: #60a5fa; }"
                )
                r_layout = QHBoxLayout(row)
                r_layout.setContentsMargins(8, 4, 8, 4)
                r_layout.setSpacing(6)

                # Spalte 1: Modellname (linksbündig, flexible Restbreite)
                lbl_name = QLabel(name)
                lbl_name.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                lbl_name.setStyleSheet("color: #f8fafc;")
                lbl_name.setToolTip(name)
                r_layout.addWidget(lbl_name, stretch=1)

                # Spalte 2: Update-Status (feste Breite ~140px, zentriert)
                btn_update = QPushButton("Prüfe..." if self.lang == "de" else "Checking...")
                btn_update.setFixedWidth(140)
                btn_update.setStyleSheet(
                    "QPushButton { background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; "
                    "border-radius: 3px; padding: 3px 6px; font-weight: bold; font-size: 10px; } "
                    "QPushButton:hover { background-color: #334155; color: #cbd5e1; }"
                )
                btn_update.setToolTip(
                    "Prüfe auf Remote-Updates..." if self.lang == "de" else "Checking remote updates..."
                )
                btn_update.clicked.connect(lambda checked, n=name, b=btn_update: self._on_update_clicked(n, b))
                r_layout.addWidget(btn_update)

                # Spalte 3: Festplattengröße (feste Breite ~75px, zentriert)
                lbl_size = QLabel(f"{size_gb:.1f} GB")
                lbl_size.setFixedWidth(75)
                lbl_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_size.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: bold;")
                r_layout.addWidget(lbl_size)

                # Spalte 4: VRAM-Bedarf (feste Breite ~110px, zentriert)
                lbl_vram = QLabel(f"~{vram_gb:.1f} GB VRAM")
                lbl_vram.setFixedWidth(110)
                lbl_vram.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_vram.setStyleSheet(
                    "background-color: #0f172a; color: #38bdf8; font-size: 10px; "
                    "padding: 2px 4px; border-radius: 3px; font-weight: bold;"
                )
                r_layout.addWidget(lbl_vram)

                # Spalte 5: Primäre Fähigkeit (feste Breite ~120px, zentriert)
                cap_badge = get_capability_badge(name, host=self.ollama_host)
                lbl_cap = QLabel(cap_badge["text"])
                lbl_cap.setFixedWidth(120)
                lbl_cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_cap.setStyleSheet(
                    f"background-color: {cap_badge['bg']}; color: {cap_badge['fg']}; "
                    f"border: 1px solid {cap_badge['border']}; border-radius: 3px; "
                    f"padding: 2px 4px; font-size: 10px; font-weight: bold;"
                )
                lbl_cap.setToolTip(cap_badge["tooltip"])
                r_layout.addWidget(lbl_cap)

                # Spalte 6: Rollen-Badge (feste Breite ~115px, zentriert)
                role_badge = get_role_recommendation_badge(name, host=self.ollama_host)
                lbl_role = QLabel(role_badge["text"])
                lbl_role.setFixedWidth(115)
                lbl_role.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_role.setStyleSheet(
                    f"background-color: {role_badge['bg']}; color: {role_badge['fg']}; "
                    f"border: 1px solid {role_badge['border']}; border-radius: 3px; "
                    f"padding: 2px 4px; font-size: 10px; font-weight: bold;"
                )
                lbl_role.setToolTip(role_badge["tooltip"])
                r_layout.addWidget(lbl_role)

                # Spalte 7: Aktions-Button (feste Breite ~145px)
                btn_add = QPushButton("➕ " + t("pipeline_btn_add", lang=self.lang))
                btn_add.setFixedWidth(145)
                btn_add.setStyleSheet(
                    "QPushButton { background-color: #2563eb; color: #ffffff; border-radius: 3px; "
                    "padding: 4px 8px; font-weight: bold; font-size: 11px; } "
                    "QPushButton:hover { background-color: #1d4ed8; }"
                )
                btn_add.setToolTip(f"'{name}' als neuen Agenten zur Pipeline hinzufügen")
                btn_add.clicked.connect(lambda checked, n=name: self.model_add_requested.emit(n))
                r_layout.addWidget(btn_add)

                self._model_rows[name] = {
                    "btn_update": btn_update,
                    "lbl_size": lbl_size,
                    "lbl_vram": lbl_vram,
                    "model": model,
                }

                self.pool_list_layout.insertWidget(self.pool_list_layout.count() - 1, row)

            self._start_update_checks()
        finally:
            self.pool_list_widget.setUpdatesEnabled(True)

    def start_model_pull(self) -> None:
        """Initiates background model pull."""
        if self.is_pulling:
            return

        tag = self.txt_pull_model.text().strip()
        if not tag:
            QMessageBox.warning(
                self,
                "Eingabe erforderlich" if self.lang == "de" else "Input Required",
                "Bitte gib einen Modellnamen ein (z. B. 'qwen2.5-coder:14b')."
                if self.lang == "de"
                else "Please enter a model name tag (e.g. 'qwen2.5-coder:14b').",
            )
            return

        self.is_pulling = True
        self.btn_pull.setEnabled(False)
        self.pull_progress_bar.setValue(0)
        self.pull_progress_bar.show()
        self.log_emitted.emit(f"Starte Download von Modell '{tag}'...", "SYSTEM")

        self.pull_worker = ModelPullWorker(self.ollama_client, tag, parent=self)
        self.pull_worker.progress.connect(self._on_pull_progress)
        self.pull_worker.finished_pull.connect(self._on_pull_finished)
        self.pull_worker.start()

    def _on_pull_progress(self, status: str, completed: int, total: int) -> None:
        if total > 0:
            pct = int((completed / total) * 100)
            self.pull_progress_bar.setValue(pct)
            self.pull_progress_bar.setFormat(f"{status}: {pct}%")
        else:
            self.pull_progress_bar.setFormat(status)

    def _on_client_log_emitted(self, msg: str, level: str) -> None:
        self.log_emitted.emit(msg, level)

    def _on_progress_updated(
        self,
        model_name: str,
        percent: int,
        completed_gb: float,
        total_gb: float,
    ) -> None:
        """
        Updates the inline button text to: '⏳ {percent}% ({completed_gb:.1f} GB)'
        and syncs the top pull bar if matching.
        """
        row_data = self._model_rows.get(model_name)
        if not row_data:
            # Fallback check without tag suffix
            for k, val in self._model_rows.items():
                if k.lower() == model_name.lower() or k.split(":")[0].lower() == model_name.split(":")[0].lower():
                    row_data = val
                    break

        if row_data:
            btn: QPushButton = row_data["btn_update"]
            btn.setEnabled(False)
            if completed_gb > 0:
                btn_text = f"⏳ {percent}% ({completed_gb:.1f} GB)"
            else:
                btn_text = f"⏳ {percent}%"
            btn.setText(btn_text)
            btn.setStyleSheet(
                "QPushButton { background-color: #1e3a8a; color: #93c5fd; border: 1px solid #3b82f6; "
                "border-radius: 3px; padding: 3px 6px; font-weight: bold; font-size: 10px; }"
            )

        if self.is_pulling:
            cur_input = self.txt_pull_model.text().strip().lower()
            clean_m = model_name.lower()
            if cur_input in (clean_m, clean_m.split(":")[0]):
                self.pull_progress_bar.setValue(percent)
                self.pull_progress_bar.setFormat(f"{model_name}: {percent}% ({completed_gb:.1f} / {total_gb:.1f} GB)")

    def _on_pull_finished(self, success: bool, model_name: str, message: str) -> None:
        self.is_pulling = False
        self.btn_pull.setEnabled(True)
        self.pull_progress_bar.hide()

        if success:
            self.log_emitted.emit(
                f"[SUCCESS] Modell '{model_name}' vollständig geladen und einsatzbereit.", "INFO"
            )
            self.txt_pull_model.clear()
            self.load_installed_models()
        else:
            self.log_emitted.emit(
                f"[FEHLER] Update für '{model_name}' fehlgeschlagen: {message}", "ERROR"
            )
            QMessageBox.critical(
                self,
                "Download-Fehler" if self.lang == "de" else "Pull Error",
                f"Modell '{model_name}' konnte nicht geladen werden:\n{message}",
            )

    def _show_pull_help(self) -> None:
        """Displays guidance for Ollama model names and directories."""
        msg = (
            "<b>Ollama Modell-Installation:</b><br><br>"
            "Gib den genauen Modellbezeichner ein, z. B.:<br>"
            "&bull; <code>qwen2.5-coder:14b</code> (Hervorragend für Code)<br>"
            "&bull; <code>deepseek-r1:8b</code> (Reasoning & Logik)<br>"
            "&bull; <code>llama3.2:3b</code> (Kompakt & schnell)<br><br>"
            "<i>Hinweis: Ohne Tag wird automatisch ':latest' angehängt. Der Befehl 'ollama pull' ist nicht nötig.</i>"
            if self.lang == "de"
            else "<b>Ollama Model Installation:</b><br><br>"
            "Enter exact model tag, e.g.:<br>"
            "&bull; <code>qwen2.5-coder:14b</code> (Great for code)<br>"
            "&bull; <code>deepseek-r1:8b</code> (Reasoning & architecture)<br>"
            "&bull; <code>llama3.2:3b</code> (Fast & compact)<br><br>"
            "<i>Prefix 'ollama pull' is not required.</i>"
        )
        QMessageBox.information(
            self,
            "Modell-Installation & Info" if self.lang == "de" else "Model Pull Info",
            msg,
        )

    def _start_update_checks(self) -> None:
        """Starts asynchronous check against Ollama registry for each installed model."""
        if not self.installed_models:
            return
        if self._update_check_worker is not None and self._update_check_worker.isRunning():
            self._update_check_worker.stop()
            self._update_check_worker.wait(200)
        self._update_check_worker = ModelUpdateCheckWorker(self.ollama_client, self.installed_models, parent=self)
        self._update_check_worker.model_checked.connect(self._on_update_status_checked)
        self._update_check_worker.start()

    def _on_update_status_checked(self, model_name: str, has_update: bool) -> None:
        row_data = self._model_rows.get(model_name)
        if not row_data:
            return
        btn: QPushButton = row_data["btn_update"]
        if not btn.isEnabled() or "Lädt" in btn.text() or "Pulling" in btn.text():
            return

        if has_update:
            btn.setText("⚡ Update verfügbar" if self.lang == "de" else "⚡ Update available")
            btn.setStyleSheet(
                "QPushButton { background-color: #7c2d12; color: #fed7aa; border: 1px solid #f97316; "
                "border-radius: 3px; padding: 3px 6px; font-weight: bold; font-size: 10px; } "
                "QPushButton:hover { background-color: #9a3412; color: #ffedd5; border-color: #fb923c; }"
            )
            btn.setToolTip(
                "Neuere Version in der Ollama Registry verfügbar. Klicke zum Aktualisieren."
                if self.lang == "de"
                else "Newer version available on Ollama registry. Click to update."
            )
        else:
            btn.setText("✓ Aktuell" if self.lang == "de" else "✓ Up to date")
            btn.setStyleSheet(
                "QPushButton { background-color: #0f172a; color: #86efac; border: 1px solid #166534; "
                "border-radius: 3px; padding: 3px 6px; font-weight: bold; font-size: 10px; } "
                "QPushButton:hover { background-color: #14532d; color: #bbf7d0; }"
            )
            btn.setToolTip(
                "Modell ist auf dem neuesten Stand. Klicke, um erneut zu prüfen."
                if self.lang == "de"
                else "Model is up to date. Click to recheck."
            )

    def _on_update_clicked(self, model_name: str, btn: QPushButton) -> None:
        """
        Handler when user clicks the update button on a model row.
        1. Disables button and sets text to '⏳ Lädt...'.
        2. Starts single model pull worker in background thread.
        """
        btn.setEnabled(False)
        btn.setText("⏳ Lädt..." if self.lang == "de" else "⏳ Pulling...")
        btn.setStyleSheet(
            "QPushButton { background-color: #1e3a8a; color: #93c5fd; border: 1px solid #3b82f6; "
            "border-radius: 3px; padding: 3px 6px; font-weight: bold; font-size: 10px; }"
        )
        self.log_emitted.emit(f"Starte Update für '{model_name}'...", "SYSTEM")

        worker = SingleModelPullWorker(self.ollama_client, model_name, parent=self)
        self._active_pull_workers.append(worker)

        def on_finished(success: bool, m_name: str, res: str) -> None:
            if worker in self._active_pull_workers:
                self._active_pull_workers.remove(worker)
            self._handle_single_pull_result(success, m_name, res, btn)

        worker.finished_pull.connect(on_finished)
        worker.start()

    def _handle_single_pull_result(
        self,
        success: bool,
        model_name: str,
        result: str,
        btn: QPushButton,
    ) -> None:
        if success and (result == "updated" or result == "success"):
            btn.setText("✓ Aktualisiert!" if self.lang == "de" else "✓ Updated!")
            btn.setStyleSheet(
                "QPushButton { background-color: #14532d; color: #86efac; border: 1px solid #22c55e; "
                "border-radius: 3px; padding: 3px 6px; font-weight: bold; font-size: 10px; }"
            )
            self.log_emitted.emit(
                f"[SUCCESS] Modell '{model_name}' vollständig geladen und einsatzbereit.",
                "INFO",
            )
            # Update local model size and VRAM in table row
            try:
                models = self.ollama_client.get_installed_models()
                for m in models:
                    m_name = (m.get("name") or "").lower()
                    tgt_name = model_name.lower()
                    if (
                        m_name == tgt_name
                        or m_name.startswith(tgt_name + ":")
                        or tgt_name.startswith(m_name + ":")
                        or m_name.split(":")[0] == tgt_name.split(":")[0]
                    ):
                        row_data = self._model_rows.get(model_name)
                        if row_data:
                            new_gb = m.get("size_gb", 0.0)
                            new_vram = estimate_model_vram_gb(model_name)
                            row_data["lbl_size"].setText(f"{new_gb:.1f} GB")
                            row_data["lbl_vram"].setText(f"~{new_vram:.1f} GB VRAM")
                            row_data["model"] = m
                        break
            except Exception as e:
                logger.debug("Failed updating row size after pull: %s", e)

            # Revert to '✓ Aktuell' after 4 seconds
            QTimer.singleShot(4000, lambda: self._set_button_up_to_date(btn, model_name))

        elif success and result == "up_to_date":
            btn.setText("✓ Bereits aktuell" if self.lang == "de" else "✓ Already up to date")
            btn.setStyleSheet(
                "QPushButton { background-color: #0f172a; color: #86efac; border: 1px solid #166534; "
                "border-radius: 3px; padding: 3px 6px; font-weight: bold; font-size: 10px; }"
            )
            self.log_emitted.emit(f"Modell '{model_name}' ist bereits auf dem neuesten Stand.", "INFO")
            QTimer.singleShot(3000, lambda: self._set_button_up_to_date(btn, model_name))

        else:
            btn.setText("⚠️ Fehler" if self.lang == "de" else "⚠️ Error")
            btn.setStyleSheet(
                "QPushButton { background-color: #7f1d1d; color: #fca5a5; border: 1px solid #ef4444; "
                "border-radius: 3px; padding: 3px 6px; font-weight: bold; font-size: 10px; }"
            )
            self.log_emitted.emit(f"[FEHLER] Update für '{model_name}' fehlgeschlagen.", "ERROR")
            QTimer.singleShot(4000, lambda: self._set_button_neutral(btn, model_name))

    def _set_button_up_to_date(self, btn: QPushButton, model_name: str) -> None:
        btn.setEnabled(True)
        btn.setText("✓ Aktuell" if self.lang == "de" else "✓ Up to date")
        btn.setStyleSheet(
            "QPushButton { background-color: #0f172a; color: #86efac; border: 1px solid #166534; "
            "border-radius: 3px; padding: 3px 6px; font-weight: bold; font-size: 10px; } "
            "QPushButton:hover { background-color: #14532d; color: #bbf7d0; }"
        )
        btn.setToolTip(
            "Modell ist auf dem neuesten Stand. Klicke, um erneut zu prüfen."
            if self.lang == "de"
            else "Model is up to date. Click to recheck."
        )

    def _set_button_neutral(self, btn: QPushButton, model_name: str) -> None:
        btn.setEnabled(True)
        btn.setText("🔄 Update")
        btn.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; "
            "border-radius: 3px; padding: 3px 6px; font-weight: bold; font-size: 10px; } "
            "QPushButton:hover { background-color: #334155; color: #cbd5e1; }"
        )
        btn.setToolTip("Klicke, um nach Updates zu suchen." if self.lang == "de" else "Click to check for updates.")

    def set_language(self, lang: str) -> None:
        """Updates all strings according to new language code."""
        self.lang = lang
        self.lbl_title.setText("📦 " + t("pipeline_pool_title", lang=self.lang))
        self.btn_pull.setText("⬇️ " + ("Installieren" if self.lang == "de" else "Pull"))
        self.btn_refresh.setText("🔄 " + ("Modelle neu laden" if self.lang == "de" else "Reload Models"))
        self.btn_refresh.setToolTip(
            "Installierte Modelle asynchron aus Ollama abrufen"
            if self.lang == "de"
            else "Asynchronously refresh installed models from Ollama"
        )
        self.btn_pull_info.setToolTip(
            "Hilfe zu Ollama-Modellnamen & Speicherort"
            if self.lang == "de"
            else "Help on Ollama model tags"
        )
        self.txt_pull_model.setPlaceholderText(
            "Modellbezeichner eingeben (z. B. qwen2.5-coder:14b, deepseek-r1:8b)..."
            if self.lang == "de"
            else "Enter model tag (e.g. qwen2.5-coder:14b, deepseek-r1:8b)..."
        )

        self.lbl_hdr_name.setText("Modellname" if self.lang == "de" else "Model Name")
        self.lbl_hdr_update.setText("Update-Status" if self.lang == "de" else "Update Status")
        self.lbl_hdr_size.setText("Größe" if self.lang == "de" else "Size")
        self.lbl_hdr_vram.setText("VRAM-Bedarf" if self.lang == "de" else "VRAM Est.")
        self.lbl_hdr_cap.setText("Fähigkeiten" if self.lang == "de" else "Capabilities")
        self.lbl_hdr_role.setText("Empfohlene Rolle" if self.lang == "de" else "Recommended Role")
        self.lbl_hdr_action.setText("Aktion" if self.lang == "de" else "Action")

        self.populate_model_pool(self.installed_models)

    def stop(self) -> None:
        """Terminates active pull, check, and list threads cleanly."""
        if self._update_check_worker is not None and self._update_check_worker.isRunning():
            self._update_check_worker.stop()
            self._update_check_worker.wait(200)
        for w in list(self._active_pull_workers):
            if w.isRunning():
                w.terminate()
        self._active_pull_workers.clear()
        if self.pull_worker is not None and self.pull_worker.isRunning():
            self.pull_worker.terminate()
        if self.model_list_worker is not None and self.model_list_worker.isRunning():
            self.model_list_worker.terminate()
