"""
Local Crew Cockpit - Thought and Live Output Drawer (PyQt6)
Collapsible and undockable live streaming console for reasoning streams and agent logs.
"""

from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.locales import t
from core.model_knowledge import has_thinking_mode


class ThoughtPopoutDialog(QDialog):
    """
    Separate undocked pop-out window for streaming thoughts and agent outputs.
    """

    dock_requested = pyqtSignal()
    cleared = pyqtSignal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        model_name: str = "",
        initial_text: str = "",
        has_thinking: bool = True,
        lang: str = "de",
    ) -> None:
        super().__init__(parent)
        self.model_name = model_name
        self.has_thinking = has_thinking
        self.lang = lang

        self.resize(720, 500)
        self.setMinimumSize(480, 320)
        self._update_title()

        self._build_ui()
        if initial_text:
            self.txt_output.setPlainText(initial_text)
            self.txt_output.moveCursor(QTextCursor.MoveOperation.End)

    def _update_title(self) -> None:
        title_prefix = "🧠 Gedanken" if self.has_thinking else "📄 Live-Output"
        if self.lang == "en":
            title_prefix = "🧠 Thoughts" if self.has_thinking else "📄 Live Output"
        self.setWindowTitle(f"{title_prefix}: {self.model_name}")

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Header bar
        header_bar = QHBoxLayout()
        header_bar.setContentsMargins(0, 0, 0, 0)

        header_text = (
            f"🧠 Live Reasoning & Gedanken: {self.model_name}"
            if self.has_thinking
            else f"📄 Live Agent-Output & Logs: {self.model_name}"
        )
        self.lbl_title = QLabel(header_text)
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #60a5fa;")
        header_bar.addWidget(self.lbl_title)

        header_bar.addStretch()

        self.btn_clear = QPushButton("🗑 " + t("btn_clear", lang=self.lang))
        self.btn_clear.clicked.connect(self._on_clear_clicked)
        header_bar.addWidget(self.btn_clear)

        self.btn_dock = QPushButton("↙ " + t("dock_btn", lang=self.lang))
        self.btn_dock.setObjectName("btnPrimary")
        self.btn_dock.clicked.connect(self._on_dock_clicked)
        header_bar.addWidget(self.btn_dock)

        layout.addLayout(header_bar)

        # Output text area
        self.txt_output = QTextEdit()
        self.txt_output.setReadOnly(True)
        self.txt_output.setFont(QFont("Consolas", 10))
        self.txt_output.setStyleSheet(
            "background-color: #0b0f19; color: #e2e8f0; border: 1px solid #334155; border-radius: 6px;"
        )
        layout.addWidget(self.txt_output)

    def _on_clear_clicked(self) -> None:
        self.txt_output.clear()
        self.cleared.emit()

    def _on_dock_clicked(self) -> None:
        self.dock_requested.emit()
        self.close()

    def append_text(self, text: str) -> None:
        self.txt_output.moveCursor(QTextCursor.MoveOperation.End)
        self.txt_output.insertPlainText(text)
        self.txt_output.moveCursor(QTextCursor.MoveOperation.End)

    def set_language(self, lang: str) -> None:
        self.lang = lang
        self._update_title()
        self.btn_clear.setText("🗑 " + t("btn_clear", lang=self.lang))
        self.btn_dock.setText("↙ " + t("dock_btn", lang=self.lang))
        header_text = (
            f"🧠 Live Reasoning & Gedanken: {self.model_name}"
            if self.has_thinking
            else f"📄 Live Agent-Output & Logs: {self.model_name}"
        )
        self.lbl_title.setText(header_text)


class ThoughtDrawer(QFrame):
    """
    Collapsible drawer widget embedded beneath a PipelineCard.
    Supports thinking reasoning stream as well as normal token fallback output.
    """

    cleared = pyqtSignal()
    undocked = pyqtSignal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        model_name: str = "",
        lang: str = "de",
    ) -> None:
        super().__init__(parent)
        self.model_name = model_name
        self.lang = lang
        self.has_thinking = has_thinking_mode(model_name)
        self.popout_dialog: Optional[ThoughtPopoutDialog] = None

        self.setObjectName("thoughtDrawerFrame")
        self.setStyleSheet(
            "QFrame#thoughtDrawerFrame { background-color: #111827; border: 1px solid #2d3748; border-radius: 8px; }"
        )

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Header row
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        self.lbl_title = QLabel()
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 11px; color: #93c5fd;")
        self._refresh_header_text()
        header.addWidget(self.lbl_title)

        header.addStretch()

        self.btn_clear = QPushButton("🗑 " + t("btn_clear", lang=self.lang))
        self.btn_clear.setToolTip(t("tooltip_clear_thoughts", lang=self.lang))
        self.btn_clear.clicked.connect(self.clear)
        header.addWidget(self.btn_clear)

        self.btn_undock = QPushButton("↗ " + t("undock_btn", lang=self.lang))
        self.btn_undock.setToolTip(t("tooltip_undock", lang=self.lang))
        self.btn_undock.clicked.connect(self.undock)
        header.addWidget(self.btn_undock)

        layout.addLayout(header)

        # Output text area
        self.txt_output = QTextEdit()
        self.txt_output.setReadOnly(True)
        self.txt_output.setFont(QFont("Consolas", 10))
        self.txt_output.setMinimumHeight(130)
        self.txt_output.setStyleSheet(
            "background-color: #05080e; color: #e2e8f0; border: 1px solid #1e293b; border-radius: 6px; padding: 6px;"
        )
        layout.addWidget(self.txt_output)

    def _refresh_header_text(self) -> None:
        if self.has_thinking:
            text = "🧠 " + (
                "Live Reasoning & Gedanken (<think>):"
                if self.lang == "de"
                else "Live Reasoning & Thoughts (<think>):"
            )
        else:
            text = "📄 " + (
                "Live Agent-Output & Logs:"
                if self.lang == "de"
                else "Live Agent Output & Logs:"
            )
        self.lbl_title.setText(text)

    def set_model(self, model_name: str) -> None:
        """Updates model configuration and dynamically adapts thinking vs output mode."""
        self.model_name = model_name
        self.has_thinking = has_thinking_mode(model_name)
        self._refresh_header_text()
        if self.popout_dialog and self.popout_dialog.isVisible():
            self.popout_dialog.model_name = model_name
            self.popout_dialog.has_thinking = self.has_thinking
            self.popout_dialog._update_title()

    def append_text(self, text: str, is_thought: bool = False) -> None:
        """
        Appends streamed token or log chunk and auto-scrolls to the end.
        Syncs seamlessly with undocked pop-out dialog if open.
        """
        if not text:
            return

        formatted = text if text.endswith("\n") else text + "\n"

        self.txt_output.moveCursor(QTextCursor.MoveOperation.End)
        self.txt_output.insertPlainText(formatted)
        self.txt_output.moveCursor(QTextCursor.MoveOperation.End)

        if self.popout_dialog and self.popout_dialog.isVisible():
            self.popout_dialog.append_text(formatted)

    def clear(self) -> None:
        """Clears text in both embedded drawer and pop-out dialog."""
        self.txt_output.clear()
        if self.popout_dialog and self.popout_dialog.isVisible():
            self.popout_dialog.txt_output.clear()
        self.cleared.emit()

    def undock(self) -> None:
        """Pops out the drawer into a separate window."""
        if self.popout_dialog and self.popout_dialog.isVisible():
            self.popout_dialog.raise_()
            self.popout_dialog.activateWindow()
            return

        current_text = self.txt_output.toPlainText()
        self.popout_dialog = ThoughtPopoutDialog(
            parent=self.window(),
            model_name=self.model_name,
            initial_text=current_text,
            has_thinking=self.has_thinking,
            lang=self.lang,
        )
        self.popout_dialog.dock_requested.connect(self.dock)
        self.popout_dialog.cleared.connect(self.clear)
        self.popout_dialog.show()

        self.btn_undock.setEnabled(False)
        self.undocked.emit()

    def dock(self) -> None:
        """Docks content back from pop-out dialog into this embedded drawer."""
        if self.popout_dialog:
            popout_text = self.popout_dialog.txt_output.toPlainText()
            self.txt_output.setPlainText(popout_text)
            self.txt_output.moveCursor(QTextCursor.MoveOperation.End)
            self.popout_dialog.close()
            self.popout_dialog = None

        self.btn_undock.setEnabled(True)
        if not self.isVisible():
            self.show()

    def set_language(self, lang: str) -> None:
        """Updates localized labels and buttons."""
        self.lang = lang
        self._refresh_header_text()
        self.btn_clear.setText("🗑 " + t("btn_clear", lang=self.lang))
        self.btn_clear.setToolTip(t("tooltip_clear_thoughts", lang=self.lang))
        self.btn_undock.setText("↗ " + t("undock_btn", lang=self.lang))
        self.btn_undock.setToolTip(t("tooltip_undock", lang=self.lang))
        if self.popout_dialog and self.popout_dialog.isVisible():
            self.popout_dialog.set_language(self.lang)
