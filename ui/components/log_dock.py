"""
Local Crew Cockpit - Log Dock & Deliverable Component (Right Pane)
Integrates the Live Activity Log with HTML color coding, Final Deliverable viewer with file export
and clipboard copy, and Human-in-the-Loop review & approval bar.
"""

import logging
from pathlib import Path
import time
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.locales import t

logger = logging.getLogger(__name__)


class LogDockWidget(QSplitter):
    """
    Right Pane Component:
    1. Live Activity Log (autoscroll, timestamps, ANSI/HTML color coding)
    2. Final Deliverable Result Viewer (Clear, Save, Copy)
    3. Human-in-the-Loop (HITL) Revision & Approval Bar
    """

    revision_requested = pyqtSignal(str)
    approval_given = pyqtSignal()
    result_accepted = pyqtSignal()
    log_cleared = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None, lang: str = "de") -> None:
        super().__init__(Qt.Orientation.Vertical, parent)
        self.lang = lang

        self.setHandleWidth(4)
        self.setChildrenCollapsible(False)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        self._build_ui()
        self.setSizes([380, 420, 120])

    def _build_ui(self) -> None:
        # 1. Live Activity Log Panel
        log_panel = self._build_live_log_panel()
        self.addWidget(log_panel)

        # 2. Final Result Panel
        result_panel = self._build_result_panel()
        self.addWidget(result_panel)

        # 3. Human-in-the-Loop Review Panel
        hitl_panel = self._build_hitl_panel()
        self.addWidget(hitl_panel)

    def _build_live_log_panel(self) -> QWidget:
        container = QFrame()
        container.setStyleSheet(
            "QFrame { background-color: #0b0f19; border: 1px solid #1e293b; border-radius: 6px; }"
        )
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header row
        header = QHBoxLayout()
        self.lbl_log_title = QLabel(
            "📜 " + ("Live-Aktivitätslog" if self.lang == "de" else "Live Activity Log")
        )
        self.lbl_log_title.setStyleSheet("font-weight: bold; font-size: 12px; color: #93c5fd;")
        header.addWidget(self.lbl_log_title)
        header.addStretch()

        self.chk_autoscroll = QCheckBox("Autoscroll")
        self.chk_autoscroll.setChecked(True)
        self.chk_autoscroll.setStyleSheet("color: #94a3b8; font-size: 11px;")
        header.addWidget(self.chk_autoscroll)

        self.btn_clear_log = QPushButton("🗑 " + t("btn_clear", lang=self.lang))
        self.btn_clear_log.setStyleSheet(
            "background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; "
            "border-radius: 4px; padding: 2px 8px; font-size: 11px;"
        )
        self.btn_clear_log.clicked.connect(self.clear_log)
        header.addWidget(self.btn_clear_log)

        layout.addLayout(header)

        # Log output text
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setFont(QFont("Consolas", 10))
        self.txt_log.setStyleSheet(
            "background-color: #05080e; color: #e2e8f0; border: 1px solid #1e293b; "
            "border-radius: 4px; padding: 6px;"
        )
        layout.addWidget(self.txt_log, stretch=1)

        return container

    def _build_result_panel(self) -> QWidget:
        container = QFrame()
        container.setStyleSheet(
            "QFrame { background-color: #0b0f19; border: 1px solid #1e293b; border-radius: 6px; }"
        )
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header row
        header = QHBoxLayout()
        self.lbl_result_title = QLabel(
            "🏁 " + ("Endergebnis" if self.lang == "de" else "Final Deliverable")
        )
        self.lbl_result_title.setStyleSheet("font-weight: bold; font-size: 12px; color: #86efac;")
        header.addWidget(self.lbl_result_title)
        header.addStretch()

        self.btn_clear_result = QPushButton("🗑 " + t("btn_clear", lang=self.lang))
        self.btn_clear_result.setStyleSheet(
            "background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; "
            "border-radius: 4px; padding: 2px 8px; font-size: 11px;"
        )
        self.btn_clear_result.clicked.connect(self.clear_result)
        header.addWidget(self.btn_clear_result)

        self.btn_save_result = QPushButton("💾 " + t("save", lang=self.lang))
        self.btn_save_result.setStyleSheet(
            "background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; "
            "border-radius: 4px; padding: 2px 8px; font-size: 11px;"
        )
        self.btn_save_result.clicked.connect(self.save_result_to_file)
        header.addWidget(self.btn_save_result)

        self.btn_copy_result = QPushButton("📋 " + t("copy", lang=self.lang))
        self.btn_copy_result.setStyleSheet(
            "background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; "
            "border-radius: 4px; padding: 2px 8px; font-size: 11px;"
        )
        self.btn_copy_result.clicked.connect(self.copy_result_to_clipboard)
        header.addWidget(self.btn_copy_result)

        layout.addLayout(header)

        # Result output text
        self.txt_result = QTextEdit()
        self.txt_result.setReadOnly(True)
        self.txt_result.setFont(QFont("Consolas", 10))
        self.txt_result.setStyleSheet(
            "background-color: #05080e; color: #f8fafc; border: 1px solid #1e293b; "
            "border-radius: 4px; padding: 8px;"
        )
        layout.addWidget(self.txt_result, stretch=1)

        return container

    def _build_hitl_panel(self) -> QWidget:
        container = QFrame()
        container.setStyleSheet(
            "QFrame { background-color: #0b0f19; border: 1px solid #1e293b; border-radius: 6px; }"
        )
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Title
        self.lbl_hitl_title = QLabel("🤝 " + t("hitl_title", lang=self.lang))
        self.lbl_hitl_title.setStyleSheet("font-weight: bold; font-size: 11px; color: #fbbf24;")
        layout.addWidget(self.lbl_hitl_title)

        # Action row
        action_row = QHBoxLayout()
        action_row.setSpacing(6)

        self.txt_hitl_feedback = QLineEdit()
        self.txt_hitl_feedback.setPlaceholderText(
            t("hitl_feedback_placeholder", lang=self.lang)
        )
        self.txt_hitl_feedback.setStyleSheet(
            "background-color: #0f172a; color: #f8fafc; border: 1px solid #334155; "
            "border-radius: 4px; padding: 5px 8px; font-size: 11px;"
        )
        action_row.addWidget(self.txt_hitl_feedback, stretch=1)

        self.btn_revise = QPushButton("🔄 " + t("hitl_btn_revise", lang=self.lang))
        self.btn_revise.setStyleSheet(
            "background-color: #854d0e; color: #fef08a; border: 1px solid #ca8a04; "
            "border-radius: 4px; padding: 5px 10px; font-weight: bold; font-size: 11px;"
        )
        self.btn_revise.clicked.connect(self._on_hitl_revise)
        action_row.addWidget(self.btn_revise)

        approve_text = "Ergebnis abnehmen" if self.lang == "de" else "Accept Deliverable"
        self.btn_approve = QPushButton("✓ " + approve_text)
        self.btn_approve.setStyleSheet(
            "background-color: #15803d; color: #ffffff; border: 1px solid #16a34a; "
            "border-radius: 4px; padding: 5px 10px; font-weight: bold; font-size: 11px;"
        )
        self.btn_approve.clicked.connect(self._on_hitl_approve)
        action_row.addWidget(self.btn_approve)

        layout.addLayout(action_row)
        return container

    def append_log(self, text: str, tag: str = "INFO") -> None:
        """Appends formatted HTML log line with timestamp and colored level badge."""
        now_str = time.strftime("%H:%M:%S")
        prefix = f"[{now_str}]"

        color_map = {
            "SYSTEM": "#38bdf8",
            "INFO": "#94a3b8",
            "AGENT": "#e2e8f0",
            "TOOL": "#facc15",
            "ERROR": "#ef4444",
            "WARNING": "#f59e0b",
        }
        color = color_map.get(tag.upper(), "#94a3b8")

        html_line = (
            f"<span style='color: #64748b;'>{prefix}</span> "
            f"<span style='color: {color}; font-weight: bold;'>[{tag.upper()}]</span> "
            f"<span style='color: #e2e8f0;'>{text}</span>"
        )

        self.txt_log.moveCursor(QTextCursor.MoveOperation.End)
        self.txt_log.insertHtml(html_line + "<br>")
        if self.chk_autoscroll.isChecked():
            self.txt_log.moveCursor(QTextCursor.MoveOperation.End)

    def clear_log(self) -> None:
        self.txt_log.clear()
        self.log_cleared.emit()

    def set_result(self, text: str) -> None:
        self.txt_result.setPlainText(text)

    def get_result(self) -> str:
        return self.txt_result.toPlainText()

    def clear_result(self) -> None:
        self.txt_result.clear()

    def save_result_to_file(self) -> None:
        """Opens file dialog and saves current result to markdown/text file."""
        content = self.txt_result.toPlainText()
        if not content:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Ergebnis speichern" if self.lang == "de" else "Save Result",
            "crew_deliverable.md",
            "Markdown Files (*.md);;Text Files (*.txt);;All Files (*.*)",
        )
        if file_path:
            try:
                Path(file_path).write_text(content, encoding="utf-8")
                self.append_log(f"Ergebnis gespeichert unter: {file_path}", "INFO")
            except Exception as exc:
                QMessageBox.critical(self, "Fehler", f"Speichern fehlgeschlagen:\n{exc}")

    def copy_result_to_clipboard(self) -> None:
        """Copies final result into system clipboard with visual button confirmation."""
        content = self.txt_result.toPlainText()
        if not content:
            return

        cb = QApplication.clipboard()
        if cb:
            cb.setText(content)
            orig_text = self.btn_copy_result.text()
            self.btn_copy_result.setText("✓ " + t("copied", lang=self.lang))
            QTimer.singleShot(1500, lambda: self.btn_copy_result.setText(orig_text))

    def _on_hitl_revise(self) -> None:
        feedback = self.txt_hitl_feedback.text().strip()
        if not feedback:
            QMessageBox.information(
                self,
                "Feedback erforderlich" if self.lang == "de" else "Feedback Required",
                "Bitte gib Hinweise für die Überarbeitung ein."
                if self.lang == "de"
                else "Please provide instructions for the revision.",
            )
            return

        self.append_log(f"Human-in-the-Loop Feedback: '{feedback}'", "SYSTEM")
        self.txt_hitl_feedback.clear()
        self.revision_requested.emit(feedback)

    def _on_hitl_approve(self) -> None:
        self.clear_result()
        self.txt_hitl_feedback.clear()
        self.result_accepted.emit()
        self.approval_given.emit()

    def set_language(self, lang: str) -> None:
        """Retranslates all text labels and buttons."""
        self.lang = lang
        self.lbl_log_title.setText(
            "📜 " + ("Live-Aktivitätslog" if self.lang == "de" else "Live Activity Log")
        )
        self.btn_clear_log.setText("🗑 " + t("btn_clear", lang=self.lang))

        self.lbl_result_title.setText(
            "🏁 " + ("Endergebnis" if self.lang == "de" else "Final Deliverable")
        )
        self.btn_clear_result.setText("🗑 " + t("btn_clear", lang=self.lang))
        self.btn_save_result.setText("💾 " + t("save", lang=self.lang))
        self.btn_copy_result.setText("📋 " + t("copy", lang=self.lang))

        self.lbl_hitl_title.setText("🤝 " + t("hitl_title", lang=self.lang))
        self.txt_hitl_feedback.setPlaceholderText(
            t("hitl_feedback_placeholder", lang=self.lang)
        )
        self.btn_revise.setText("🔄 " + t("hitl_btn_revise", lang=self.lang))
        approve_text = "Ergebnis abnehmen" if self.lang == "de" else "Accept Deliverable"
        self.btn_approve.setText("✓ " + approve_text)
