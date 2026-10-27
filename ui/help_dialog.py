"""
Local Crew Cockpit - Help & Quickstart Dialog (PyQt6)
Provides an onboarding 3-step guide and example prompt for beginners.
"""

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.locales import t


class CockpitHelpDialog(QDialog):
    """
    Comprehensive Onboarding and Help Guide modal dialog (PyQt6).
    """

    def __init__(self, parent: Optional[QWidget] = None, lang: str = "de") -> None:
        super().__init__(parent)
        self.lang = lang
        self.resize(720, 600)
        self.setMinimumSize(560, 480)
        self.setWindowTitle(t("help_modal_title", lang=self.lang))
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel(
            "🚀 Local Crew Cockpit - Schnellstart & Anleitung"
            if self.lang == "de"
            else "🚀 Local Crew Cockpit - Quickstart Guide"
        )
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #60a5fa;")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(14)

        # Step 1
        s1_title = QLabel(t("help_step_1_title", lang=self.lang))
        s1_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #38bdf8;")
        s1_desc = QLabel(t("help_step_1_desc", lang=self.lang))
        s1_desc.setWordWrap(True)
        content_layout.addWidget(s1_title)
        content_layout.addWidget(s1_desc)

        # Step 2
        s2_title = QLabel(t("help_step_2_title", lang=self.lang))
        s2_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #38bdf8;")
        s2_desc = QLabel(t("help_step_2_desc", lang=self.lang))
        s2_desc.setWordWrap(True)
        content_layout.addWidget(s2_title)
        content_layout.addWidget(s2_desc)

        # Step 3
        s3_title = QLabel(t("help_step_3_title", lang=self.lang))
        s3_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #38bdf8;")
        s3_desc = QLabel(t("help_step_3_desc", lang=self.lang))
        s3_desc.setWordWrap(True)
        content_layout.addWidget(s3_title)
        content_layout.addWidget(s3_desc)

        # Example prompt
        ex_title = QLabel(t("help_example_prompt_title", lang=self.lang))
        ex_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #facc15;")
        self.txt_example = QTextEdit()
        self.txt_example.setReadOnly(True)
        self.txt_example.setMaximumHeight(80)
        self.txt_example.setText(t("help_example_prompt_content", lang=self.lang))
        content_layout.addWidget(ex_title)
        content_layout.addWidget(self.txt_example)

        content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        # Close button
        btn_close = QPushButton(t("close", lang=self.lang))
        btn_close.setStyleSheet(
            "background-color: #2563eb; color: #ffffff; font-weight: bold; "
            "padding: 6px 16px; border-radius: 4px;"
        )
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)


# Backwards compatibility alias
HelpDialog = CockpitHelpDialog
