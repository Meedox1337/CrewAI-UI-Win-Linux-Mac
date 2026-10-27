"""
Local Crew Cockpit - Workspace & File Context Component (Zone 3)
Manages the active project directory selection with a unified modern QComboBox,
quick action buttons (Choose Folder, Open in Explorer), compact filter bar,
and file tree with integrated workspace status reporting.
"""

import json
import logging
import os
from pathlib import Path
import platform
import subprocess
from typing import Any, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.file_tree import ProjectFileTree

logger = logging.getLogger(__name__)


class WorkspaceWidget(QFrame):
    """
    Zone 3: Consolidated Workspace & File Context Component.
    Features:
      1. Consolidated header: QComboBox (display & history) + [📁 Ordner wählen...] + [📂 Im Explorer öffnen]
      2. Compact filter bar with [✓ Alle] and [✗ Keine]
      3. File tree with live status bar ("X / Y Dateien ausgewählt | Workspace: <name>")
    """

    workspace_changed = pyqtSignal(str)
    log_emitted = pyqtSignal(str, str)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        initial_workspace: Optional[str] = None,
        lang: str = "de",
    ) -> None:
        super().__init__(parent)
        self.lang = lang
        self.current_workspace: Optional[str] = None
        self.recent_workspaces: List[str] = self._load_recent_workspaces()

        self._build_ui()

        if initial_workspace and os.path.isdir(initial_workspace):
            self.set_workspace(initial_workspace)
        elif self.recent_workspaces and os.path.isdir(self.recent_workspaces[0]):
            pass

    def _build_ui(self) -> None:
        self.setStyleSheet(
            "QFrame { background-color: #0b0f19; border: 1px solid #1e293b; border-radius: 6px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Title
        self.lbl_title = QLabel(
            "📂 " + ("Projektordner & Dateikontext" if self.lang == "de" else "Workspace & File Context")
        )
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 12px; color: #38bdf8;")
        layout.addWidget(self.lbl_title)

        # 1. Consolidated Workspace Header: QComboBox + Action Buttons
        ws_header_row = QHBoxLayout()
        ws_header_row.setContentsMargins(0, 0, 0, 0)
        ws_header_row.setSpacing(6)

        self.cb_workspace = QComboBox()
        self.cb_workspace.activated.connect(self._on_workspace_selected)
        ws_header_row.addWidget(self.cb_workspace, stretch=1)

        # Backwards compatibility alias
        self.cb_recent_workspaces = self.cb_workspace

        self.btn_browse_workspace = QPushButton(
            "📁 " + ("Ordner wählen..." if self.lang == "de" else "Select Folder...")
        )
        self.btn_browse_workspace.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; "
            "border-radius: 4px; padding: 5px 10px; font-weight: bold; font-size: 11px; } "
            "QPushButton:hover { background-color: #334155; color: #ffffff; border-color: #60a5fa; }"
        )
        self.btn_browse_workspace.setToolTip(
            "Projektordner auswählen oder neuen Ordner erstellen"
            if self.lang == "de"
            else "Select or create workspace directory"
        )
        self.btn_browse_workspace.clicked.connect(self.choose_workspace_dialog)
        ws_header_row.addWidget(self.btn_browse_workspace)

        self.btn_open_explorer = QPushButton(
            "📂 " + ("Im Explorer öffnen" if self.lang == "de" else "Open in Explorer")
        )
        self.btn_open_explorer.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; "
            "border-radius: 4px; padding: 5px 10px; font-weight: bold; font-size: 11px; } "
            "QPushButton:hover { background-color: #334155; color: #ffffff; border-color: #60a5fa; }"
        )
        self.btn_open_explorer.setToolTip(
            "Aktiven Projektordner im Betriebssystem-Explorer öffnen"
            if self.lang == "de"
            else "Open active workspace in system file explorer"
        )
        self.btn_open_explorer.clicked.connect(self.open_in_explorer)
        ws_header_row.addWidget(self.btn_open_explorer)

        layout.addLayout(ws_header_row)

        # 2. High-Performance ProjectFileTree (Hide its duplicate top bar)
        self.file_tree = ProjectFileTree(self, workspace_path=None, lang=self.lang)
        self.file_tree.lbl_path.hide()
        self.file_tree.btn_browse.hide()
        self.file_tree.btn_explorer.hide()
        self.file_tree.btn_refresh.hide()

        # Connect signals and override stats update with enhanced status message
        self.file_tree.workspace_changed.connect(self.set_workspace)
        self.file_tree._update_stats = self._update_stats_label
        self.file_tree.selection_changed.connect(lambda files: self._update_stats_label())

        layout.addWidget(self.file_tree, stretch=1)

        self._refresh_workspace_ui()

    def _get_config_path(self) -> Path:
        cfg_dir = Path.home() / ".local_crew_cockpit"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        return cfg_dir / "recent_workspaces.json"

    def _load_recent_workspaces(self) -> List[str]:
        try:
            p = self._get_config_path()
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return [
                        str(Path(d).resolve())
                        for d in data
                        if isinstance(d, str) and os.path.isdir(d)
                    ]
        except Exception as exc:
            logger.debug("Could not load recent workspaces: %s", exc)
        return []

    def _save_recent_workspaces(self) -> None:
        try:
            p = self._get_config_path()
            p.write_text(
                json.dumps(self.recent_workspaces[:10], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.debug("Could not save recent workspaces: %s", exc)

    def _add_recent_workspace(self, path: str) -> None:
        abs_p = str(Path(path).resolve())
        if abs_p in self.recent_workspaces:
            self.recent_workspaces.remove(abs_p)
        self.recent_workspaces.insert(0, abs_p)
        self.recent_workspaces = self.recent_workspaces[:10]
        self._save_recent_workspaces()
        self._refresh_workspace_ui()

    def choose_workspace_dialog(self) -> None:
        """Opens QFileDialog with exact required caption."""
        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        fallback_dir = desktop_dir if os.path.isdir(desktop_dir) else str(Path.home())
        initial_dir = (
            self.current_workspace
            or (self.recent_workspaces[0] if self.recent_workspaces else fallback_dir)
        )
        caption = (
            "Projektordner auswählen oder neuen Ordner erstellen"
            if self.lang == "de"
            else "Select or create workspace directory"
        )
        folder = QFileDialog.getExistingDirectory(self, caption, initial_dir)
        if folder and os.path.isdir(folder):
            self.set_workspace(folder)

    def set_workspace(self, folder: str) -> None:
        """Sets and verifies workspace path, loads file tree, and emits changes."""
        if not folder or not os.path.isdir(folder):
            return
        abs_folder = str(Path(folder).resolve())
        self.current_workspace = abs_folder
        self._add_recent_workspace(abs_folder)
        self.file_tree.load_directory(abs_folder)
        self._refresh_workspace_ui()
        self.log_emitted.emit(f"Projektordner ausgewählt: {self.current_workspace}", "SYSTEM")
        self.workspace_changed.emit(self.current_workspace)

    def open_in_explorer(self) -> None:
        """Opens active workspace in operating system file manager (e.g. via os.startfile on Windows)."""
        if not self.current_workspace or not os.path.isdir(self.current_workspace):
            QMessageBox.information(
                self,
                "Kein Projektordner" if self.lang == "de" else "No Workspace",
                "⚠️ Bitte wähle zuerst einen Projektordner aus!"
                if self.lang == "de"
                else "⚠️ Please select a workspace directory first!",
            )
            return

        folder_str = str(self.current_workspace)
        try:
            if platform.system() == "Windows":
                os.startfile(folder_str)
            elif platform.system() == "Darwin":
                subprocess.run(["open", folder_str], check=False)
            else:
                subprocess.run(["xdg-open", folder_str], check=False)
        except Exception as exc:
            logger.warning("Could not open explorer for %s: %s", folder_str, exc)

    def _on_workspace_selected(self, index: int) -> None:
        path = self.cb_workspace.itemData(index)
        if path and os.path.isdir(path):
            self.set_workspace(path)
        elif path:
            QMessageBox.warning(
                self,
                "Ordner nicht gefunden" if self.lang == "de" else "Folder Not Found",
                f"Der Ordner '{path}' existiert nicht mehr."
                if self.lang == "de"
                else f"Folder '{path}' no longer exists.",
            )
            if path in self.recent_workspaces:
                self.recent_workspaces.remove(path)
                self._save_recent_workspaces()
                self._refresh_workspace_ui()

    def _refresh_workspace_ui(self) -> None:
        """Consolidates current workspace and recent history in the QComboBox."""
        self.cb_workspace.blockSignals(True)
        self.cb_workspace.clear()

        if self.current_workspace and os.path.isdir(self.current_workspace):
            folder_name = os.path.basename(self.current_workspace.rstrip(r"\/")) or self.current_workspace
            self.cb_workspace.addItem(
                f"📁 {folder_name} ({self.current_workspace})",
                userData=self.current_workspace,
            )
            self.cb_workspace.setStyleSheet(
                "QComboBox { background-color: #0f172a; color: #38bdf8; border: 1px solid #334155; "
                "border-radius: 4px; padding: 5px 8px; font-weight: bold; font-size: 11px; } "
                "QComboBox::drop-down { border: none; } "
                "QComboBox QAbstractItemView { background-color: #0f172a; color: #f8fafc; "
                "selection-background-color: #2563eb; }"
            )
            self.cb_workspace.setToolTip(f"Aktiver Projektordner: {self.current_workspace}")
        else:
            placeholder = (
                "⚠️ Bitte Projektordner wählen..."
                if self.lang == "de"
                else "⚠️ Please select workspace folder..."
            )
            self.cb_workspace.addItem(placeholder, userData="")
            self.cb_workspace.setStyleSheet(
                "QComboBox { background-color: #2a1b0a; color: #facc15; border: 1px solid #eab308; "
                "border-radius: 4px; padding: 5px 8px; font-weight: bold; font-size: 11px; } "
                "QComboBox::drop-down { border: none; } "
                "QComboBox QAbstractItemView { background-color: #0f172a; color: #f8fafc; "
                "selection-background-color: #2563eb; }"
            )
            self.cb_workspace.setToolTip(
                "Klicke hier oder auf [📁 Ordner wählen...], um einen Projektordner festzulegen."
            )

        # Populate dropdown history
        for p in self.recent_workspaces:
            if os.path.isdir(p) and (not self.current_workspace or p != self.current_workspace):
                name = os.path.basename(p.rstrip(r"\/")) or p
                self.cb_workspace.addItem(f"🕒 {name} ({p})", userData=p)

        self.cb_workspace.setCurrentIndex(0)
        self.cb_workspace.blockSignals(False)

        self._update_stats_label()

    def _update_stats_label(self) -> None:
        """Updates bottom stats label in format: 'X / Y Dateien ausgewählt | Workspace: <name>'."""
        if not hasattr(self, "file_tree") or not hasattr(self.file_tree, "lbl_stats"):
            return
        total = len(getattr(self.file_tree, "_all_file_items", []))
        active = sum(
            1
            for item in getattr(self.file_tree, "_all_file_items", [])
            if item.checkState(0) == Qt.CheckState.Checked
        )
        ws_name = (
            os.path.basename(self.current_workspace.rstrip(r"\/"))
            if self.current_workspace and os.path.isdir(self.current_workspace)
            else ("Kein Projektordner gewählt" if self.lang == "de" else "No workspace selected")
        )
        if self.lang == "de":
            self.file_tree.lbl_stats.setText(f"{active} / {total} Dateien ausgewählt | Workspace: {ws_name}")
        else:
            self.file_tree.lbl_stats.setText(f"{active} / {total} files selected | Workspace: {ws_name}")

    def get_workspace(self) -> Optional[str]:
        return self.current_workspace

    def has_valid_workspace(self) -> bool:
        return bool(self.current_workspace and os.path.isdir(self.current_workspace))

    def get_included_files(self) -> List[str]:
        return self.file_tree.get_included_files()

    def set_language(self, lang: str) -> None:
        """Retranslates header labels, buttons, and file tree."""
        self.lang = lang
        self.lbl_title.setText(
            "📂 " + ("Projektordner & Dateikontext" if self.lang == "de" else "Workspace & File Context")
        )
        self.btn_browse_workspace.setText(
            "📁 " + ("Ordner wählen..." if self.lang == "de" else "Select Folder...")
        )
        self.btn_open_explorer.setText(
            "📂 " + ("Im Explorer öffnen" if self.lang == "de" else "Open in Explorer")
        )
        self._refresh_workspace_ui()
        self.file_tree.set_language(self.lang)
