"""
Local Crew Cockpit - High-Performance Project File Tree (PyQt6)
Hierarchical file explorer with cascading checkboxes, extension-based filtering,
automatic exclusion of noise folders, active file statistics, and runner signal integration.
"""

from fnmatch import fnmatch
import logging
import os
from pathlib import Path
import platform
import subprocess
from typing import Any, List, Optional, Set, Union

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.locales import t

logger = logging.getLogger(__name__)

# Standard automatic exclusion list for developer workspaces
AUTOMATIC_IGNORE_DIRS: Set[str] = {
    ".git",
    ".svn",
    ".hg",
    "__pycache__",
    "venv",
    ".venv",
    "env",
    "node_modules",
    "build",
    "dist",
    ".idea",
    ".vscode",
    ".next",
    ".cache",
    "target",
    "out",
    "bin",
    "obj",
    ".dart_tool",
    ".gradle",
    "assets",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "coverage",
}

AUTOMATIC_IGNORE_EXTENSIONS: Set[str] = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".dll",
    ".dylib",
    ".exe",
    ".bin",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".webp",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".rar",
    ".parquet",
    ".db",
    ".sqlite",
    ".mp3",
    ".mp4",
    ".mov",
    ".avi",
    ".wav",
    ".DS_Store",
}


def _format_size(size_bytes: int) -> str:
    """Formats file size into human-readable representation."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


class ProjectFileTree(QWidget):
    """
    High-performance PyQt6 workspace file tree with cascading checkboxes,
    fast pattern filtering, file count stats, and selection changed signals.
    """

    selection_changed = pyqtSignal(list)
    workspace_changed = pyqtSignal(str)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        workspace_path: Optional[Union[str, Path]] = None,
        lang: str = "de",
    ) -> None:
        super().__init__(parent)
        self.lang = lang
        self.workspace_path: Optional[Path] = Path(workspace_path).resolve() if workspace_path else None

        self._is_updating_checks = False
        self._all_file_items: List[QTreeWidgetItem] = []

        self._build_ui()
        if self.workspace_path and self.workspace_path.is_dir():
            self.load_directory(self.workspace_path)
        else:
            self.lbl_path.setText("⚠️ Kein Projektordner gewählt" if self.lang == "de" else "⚠️ No folder selected")
            self.lbl_stats.setText("0 / 0 Dateien aktiv" if self.lang == "de" else "0 / 0 files active")

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # 1. Top bar: Workspace path & action buttons
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.setSpacing(6)

        self.lbl_path = QLabel()
        self.lbl_path.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_path.setStyleSheet("color: #60a5fa;")
        top_bar.addWidget(self.lbl_path, stretch=1)

        self.btn_browse = QPushButton("📁 " + ("Ordner..." if self.lang == "de" else "Browse..."))
        self.btn_browse.setStyleSheet(
            "background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; "
            "border-radius: 4px; padding: 4px 8px; font-size: 11px;"
        )
        self.btn_browse.setToolTip(
            "Anderen Projektordner auswählen"
            if self.lang == "de"
            else "Select a different workspace folder"
        )
        self.btn_browse.clicked.connect(self._on_browse_clicked)
        top_bar.addWidget(self.btn_browse)

        self.btn_explorer = QPushButton("↗ " + ("Explorer" if self.lang == "de" else "Open"))
        self.btn_explorer.setStyleSheet(
            "background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; "
            "border-radius: 4px; padding: 4px 8px; font-size: 11px;"
        )
        self.btn_explorer.setToolTip(
            "Projektverzeichnis im Dateimanager öffnen"
            if self.lang == "de"
            else "Open folder in file manager"
        )
        self.btn_explorer.clicked.connect(self._open_in_file_manager)
        top_bar.addWidget(self.btn_explorer)

        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setStyleSheet(
            "background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; "
            "border-radius: 4px; padding: 4px 8px; font-size: 11px;"
        )
        self.btn_refresh.setToolTip(
            "Dateibaum neu laden" if self.lang == "de" else "Refresh file tree"
        )
        self.btn_refresh.clicked.connect(lambda: self.load_directory(self.workspace_path))
        top_bar.addWidget(self.btn_refresh)

        layout.addLayout(top_bar)

        # 2. Filter & Selection Control Row
        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setSpacing(6)

        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText(
            "🔍 Filter (z. B. *.py, *.md, core/)..."
            if self.lang == "de"
            else "🔍 Filter (e.g. *.py, *.md, core/)..."
        )
        self.txt_filter.setStyleSheet(
            "background-color: #0f172a; color: #f8fafc; border: 1px solid #334155; "
            "border-radius: 4px; padding: 4px 8px; font-size: 11px;"
        )
        self.txt_filter.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self.txt_filter, stretch=1)

        self.btn_select_all = QPushButton("✓ " + ("Alle" if self.lang == "de" else "All"))
        self.btn_select_all.setStyleSheet(
            "background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; "
            "border-radius: 4px; padding: 4px 8px; font-size: 11px;"
        )
        self.btn_select_all.setToolTip(
            "Alle Dateien aktivieren" if self.lang == "de" else "Select all files"
        )
        self.btn_select_all.clicked.connect(self.select_all)
        filter_row.addWidget(self.btn_select_all)

        self.btn_select_none = QPushButton("✗ " + ("Keine" if self.lang == "de" else "None"))
        self.btn_select_none.setStyleSheet(
            "background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; "
            "border-radius: 4px; padding: 4px 8px; font-size: 11px;"
        )
        self.btn_select_none.setToolTip(
            "Alle Dateien abwählen" if self.lang == "de" else "Deselect all files"
        )
        self.btn_select_none.clicked.connect(self.deselect_all)
        filter_row.addWidget(self.btn_select_none)

        layout.addLayout(filter_row)

        # 3. High-Performance Tree Widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(
            ["Name", "Größe"] if self.lang == "de" else ["Name", "Size"]
        )
        self.tree.setColumnCount(2)
        self.tree.setAlternatingRowColors(True)
        self.tree.setAnimated(True)
        self.tree.setStyleSheet(
            "QTreeWidget {"
            "  background-color: #0b0f19;"
            "  color: #e2e8f0;"
            "  border: 1px solid #1e293b;"
            "  border-radius: 6px;"
            "  padding: 2px;"
            "}"
            "QTreeWidget::item {"
            "  padding: 2px 4px;"
            "  border-radius: 3px;"
            "}"
            "QTreeWidget::item:hover {"
            "  background-color: #1e293b;"
            "}"
            "QTreeWidget::item:selected {"
            "  background-color: #2563eb;"
            "  color: #ffffff;"
            "}"
            "QHeaderView::section {"
            "  background-color: #0f172a;"
            "  color: #94a3b8;"
            "  border: none;"
            "  border-bottom: 1px solid #1e293b;"
            "  padding: 4px 6px;"
            "  font-size: 11px;"
            "  font-weight: bold;"
            "}"
        )

        header = self.tree.header()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

        self.tree.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.tree, stretch=1)

        # 4. Bottom Stats Row: "X / Y Dateien aktiv"
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)

        self.lbl_stats = QLabel("0 / 0 Dateien aktiv" if self.lang == "de" else "0 / 0 files active")
        self.lbl_stats.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold;")
        bottom_row.addWidget(self.lbl_stats)
        bottom_row.addStretch()

        layout.addLayout(bottom_row)

    def load_directory(self, dir_path: Union[str, Path]) -> None:
        """
        Scans workspace directory, excludes noise and binary files,
        and builds the hierarchical tree.
        """
        self.workspace_path = Path(dir_path).resolve()
        self.lbl_path.setText(f"📁 {self.workspace_path.name}")
        self.lbl_path.setToolTip(str(self.workspace_path))

        self.tree.blockSignals(True)
        self.tree.clear()
        self._all_file_items.clear()

        if self.workspace_path.is_dir():
            self._populate_dir(self.workspace_path, parent_item=None)

        self.tree.blockSignals(False)
        self._update_stats()
        self.selection_changed.emit(self.get_included_files())

    def _populate_dir(self, directory: Path, parent_item: Optional[QTreeWidgetItem]) -> None:
        """Recursively populates folders and files."""
        try:
            entries = sorted(
                list(directory.iterdir()),
                key=lambda p: (not p.is_dir(), p.name.lower()),
            )
        except (PermissionError, FileNotFoundError) as exc:
            logger.debug("Cannot access folder %s: %s", directory, exc)
            return

        for entry in entries:
            name = entry.name

            # Check noise exclusion
            if entry.is_dir():
                if name in AUTOMATIC_IGNORE_DIRS or name.startswith("."):
                    continue

                item = QTreeWidgetItem()
                item.setText(0, f"📁 {name}")
                item.setText(1, "")
                item.setFlags(
                    item.flags()
                    | Qt.ItemFlag.ItemIsUserCheckable
                    | Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsAutoTristate
                )
                item.setCheckState(0, Qt.CheckState.Checked)
                item.setData(0, Qt.ItemDataRole.UserRole, str(entry.resolve()))
                item.setData(0, Qt.ItemDataRole.UserRole + 1, True)  # is_dir

                if parent_item:
                    parent_item.addChild(item)
                else:
                    self.tree.addTopLevelItem(item)

                self._populate_dir(entry, parent_item=item)

            else:
                ext = entry.suffix.lower()
                if ext in AUTOMATIC_IGNORE_EXTENSIONS or name.startswith("."):
                    continue

                try:
                    size_bytes = entry.stat().st_size
                    size_str = _format_size(size_bytes)
                except Exception:
                    size_str = ""

                item = QTreeWidgetItem()
                item.setText(0, f"📄 {name}")
                item.setText(1, size_str)
                item.setFlags(
                    item.flags()
                    | Qt.ItemFlag.ItemIsUserCheckable
                    | Qt.ItemFlag.ItemIsEnabled
                )
                item.setCheckState(0, Qt.CheckState.Checked)
                item.setData(0, Qt.ItemDataRole.UserRole, str(entry.resolve()))
                item.setData(0, Qt.ItemDataRole.UserRole + 1, False)  # is_file

                if parent_item:
                    parent_item.addChild(item)
                else:
                    self.tree.addTopLevelItem(item)

                self._all_file_items.append(item)

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        """Handles cascading checkbox changes."""
        if column != 0 or self._is_updating_checks:
            return

        self._is_updating_checks = True
        state = item.checkState(0)

        # 1. If folder, cascade to all descendants
        is_dir = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if is_dir:
            self._set_descendants_checked(item, state)

        # 2. Update parents up to root
        parent = item.parent()
        while parent:
            self._update_parent_check_state(parent)
            parent = parent.parent()

        self._is_updating_checks = False
        self._update_stats()
        self.selection_changed.emit(self.get_included_files())

    def _set_descendants_checked(self, parent_item: QTreeWidgetItem, state: Qt.CheckState) -> None:
        """Cascades check state recursively down the sub-tree."""
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            if child:
                child.setCheckState(0, state)
                self._set_descendants_checked(child, state)

    def _update_parent_check_state(self, parent_item: QTreeWidgetItem) -> None:
        """Computes partial, checked, or unchecked state for a parent item."""
        count = parent_item.childCount()
        if count == 0:
            return

        checked_count = 0
        partially_checked_count = 0

        for i in range(count):
            child = parent_item.child(i)
            if child:
                st = child.checkState(0)
                if st == Qt.CheckState.Checked:
                    checked_count += 1
                elif st == Qt.CheckState.PartiallyChecked:
                    partially_checked_count += 1

        if checked_count == count:
            parent_item.setCheckState(0, Qt.CheckState.Checked)
        elif checked_count > 0 or partially_checked_count > 0:
            parent_item.setCheckState(0, Qt.CheckState.PartiallyChecked)
        else:
            parent_item.setCheckState(0, Qt.CheckState.Unchecked)

    def _apply_filter(self, filter_text: str) -> None:
        """
        Filters items by extension or substring query (e.g. '*.py', '*.md, test').
        Automatically keeps matching hierarchy visible and expanded.
        """
        raw_text = (filter_text or "").strip().lower()
        if not raw_text:
            # Show all items
            self._set_all_visible(self.tree.invisibleRootItem())
            return

        tokens = [t.strip() for t in raw_text.replace(";", ",").split(",") if t.strip()]

        def item_matches(item: QTreeWidgetItem) -> bool:
            name = item.text(0).replace("📁 ", "").replace("📄 ", "").lower()
            for tok in tokens:
                if tok.startswith("*."):
                    if fnmatch(name, tok):
                        return True
                elif tok.startswith("."):
                    if name.endswith(tok):
                        return True
                else:
                    if tok in name:
                        return True
            return False

        def filter_node(item: QTreeWidgetItem) -> bool:
            is_dir = item.data(0, Qt.ItemDataRole.UserRole + 1)
            any_child_matches = False

            for i in range(item.childCount()):
                child = item.child(i)
                if child and filter_node(child):
                    any_child_matches = True

            matches = any_child_matches or item_matches(item)
            item.setHidden(not matches)

            if any_child_matches:
                item.setExpanded(True)

            return matches

        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            child = root.child(i)
            if child:
                filter_node(child)

    def _set_all_visible(self, item: QTreeWidgetItem) -> None:
        item.setHidden(False)
        for i in range(item.childCount()):
            child = item.child(i)
            if child:
                self._set_all_visible(child)

    def select_all(self) -> None:
        """Selects all items in the tree."""
        self._is_updating_checks = True
        root = self.tree.invisibleRootItem()
        self._set_tree_checked_state(root, Qt.CheckState.Checked)
        self._is_updating_checks = False
        self._update_stats()
        self.selection_changed.emit(self.get_included_files())

    def deselect_all(self) -> None:
        """Deselects all items in the tree."""
        self._is_updating_checks = True
        root = self.tree.invisibleRootItem()
        self._set_tree_checked_state(root, Qt.CheckState.Unchecked)
        self._is_updating_checks = False
        self._update_stats()
        self.selection_changed.emit(self.get_included_files())

    def _set_tree_checked_state(self, item: QTreeWidgetItem, state: Qt.CheckState) -> None:
        item.setCheckState(0, state)
        for i in range(item.childCount()):
            child = item.child(i)
            if child:
                self._set_tree_checked_state(child, state)

    def _update_stats(self) -> None:
        """Updates 'X / Y Dateien aktiv' stats label."""
        total = len(self._all_file_items)
        active = sum(
            1
            for item in self._all_file_items
            if item.checkState(0) == Qt.CheckState.Checked
        )
        if self.lang == "de":
            self.lbl_stats.setText(f"{active} / {total} Dateien aktiv")
        else:
            self.lbl_stats.setText(f"{active} / {total} files active")

    def _on_browse_clicked(self) -> None:
        """Opens directory selection dialog."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Projektordner auswählen oder neuen Ordner erstellen" if self.lang == "de" else "Select or create workspace directory",
            str(self.workspace_path) if self.workspace_path else str(Path.home()),
        )
        if folder:
            self.load_directory(folder)
            self.workspace_changed.emit(folder)

    def _open_in_file_manager(self) -> None:
        """Launches native file manager for current workspace."""
        if not self.workspace_path:
            return
        folder_str = str(self.workspace_path)
        system = platform.system()
        try:
            if system == "Windows":
                os.startfile(folder_str)
            elif system == "Darwin":
                subprocess.run(["open", folder_str], check=False)
            else:
                subprocess.run(["xdg-open", folder_str], check=False)
        except Exception as exc:
            logger.warning("Could not open file manager for %s: %s", folder_str, exc)

    def get_included_files(self) -> List[str]:
        """Returns list of absolute file paths currently selected (checked)."""
        result: List[str] = []
        for item in self._all_file_items:
            if item.checkState(0) == Qt.CheckState.Checked:
                path_str = item.data(0, Qt.ItemDataRole.UserRole)
                if path_str:
                    result.append(path_str)
        return result

    def get_workspace_path(self) -> str:
        """Returns current workspace path string."""
        return str(self.workspace_path) if self.workspace_path else ""

    def set_workspace(self, path: Union[str, Path]) -> None:
        """Changes workspace directory."""
        self.load_directory(path)

    def set_language(self, lang: str) -> None:
        """Updates localized labels and tooltips."""
        self.lang = lang
        self.btn_browse.setText("📁 " + ("Ordner..." if self.lang == "de" else "Browse..."))
        self.btn_explorer.setText("↗ " + ("Explorer" if self.lang == "de" else "Open"))
        self.btn_select_all.setText("✓ " + ("Alle" if self.lang == "de" else "All"))
        self.btn_select_none.setText("✗ " + ("Keine" if self.lang == "de" else "None"))
        self.tree.setHeaderLabels(
            ["Name", "Größe"] if self.lang == "de" else ["Name", "Size"]
        )
        self.txt_filter.setPlaceholderText(
            "🔍 Filter (z. B. *.py, *.md, core/)..."
            if self.lang == "de"
            else "🔍 Filter (e.g. *.py, *.md, core/)..."
        )
        self._update_stats()


# Backward compatibility alias for main_window
FileTreeFilter = ProjectFileTree
