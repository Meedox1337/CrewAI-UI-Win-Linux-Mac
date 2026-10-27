"""
Local Crew Cockpit - Cyber/Pro Dark Theme & Stylesheet Module (PyQt6)
Provides cohesive palette colors, full QSS stylesheet rules, and an apply_dark_theme helper.
"""

from typing import Any, Union
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import QApplication, QWidget

# Design System Color Tokens
COLOR_BG_DARKEST = "#0b0f19"
COLOR_BG_DARK = "#0f172a"
COLOR_BG_CARD = "#1e293b"
COLOR_BG_CARD_HOVER = "#243248"
COLOR_BORDER = "#334155"
COLOR_BORDER_LIGHT = "#475569"
COLOR_TEXT_PRIMARY = "#f8fafc"
COLOR_TEXT_SECONDARY = "#94a3b8"
COLOR_TEXT_MUTED = "#64748b"

COLOR_ACCENT = "#2563eb"
COLOR_ACCENT_HOVER = "#3b82f6"
COLOR_ACCENT_PRESSED = "#1d4ed8"

COLOR_SUCCESS = "#22c55e"
COLOR_SUCCESS_BG = "#052e16"
COLOR_SUCCESS_BORDER = "#16a34a"

COLOR_WARNING = "#eab308"
COLOR_WARNING_BG = "#422006"
COLOR_WARNING_BORDER = "#ca8a04"

COLOR_DANGER = "#ef4444"
COLOR_DANGER_BG = "#450a0a"
COLOR_DANGER_BORDER = "#dc2626"

COLOR_INFO = "#38bdf8"
COLOR_INFO_BG = "#082f49"
COLOR_INFO_BORDER = "#0284c7"

# Full Comprehensive Qt Style Sheet (QSS)
DARK_QSS = f"""
/* Global Widget Defaults */
QWidget {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_PRIMARY};
    font-family: 'Segoe UI', 'Inter', system-ui, -apple-system, sans-serif;
    font-size: 12px;
    selection-background-color: {COLOR_ACCENT};
    selection-color: #ffffff;
}}

/* Main Containers & Frames */
QFrame {{
    background-color: transparent;
    border: none;
}}

QFrame[frameShape="1"], QFrame[frameShape="2"], QFrame[frameShape="3"],
QFrame#cardFrame, .cardFrame {{
    background-color: {COLOR_BG_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
}}

/* Buttons */
QPushButton {{
    background-color: {COLOR_BG_CARD};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 600;
    min-height: 22px;
}}

QPushButton:hover {{
    background-color: {COLOR_ACCENT};
    border-color: {COLOR_ACCENT_HOVER};
    color: #ffffff;
}}

QPushButton:pressed {{
    background-color: {COLOR_ACCENT_PRESSED};
    border-color: #1e40af;
}}

QPushButton:disabled {{
    background-color: {COLOR_BG_DARKEST};
    color: {COLOR_TEXT_MUTED};
    border-color: {COLOR_BORDER};
}}

QPushButton#btnPrimary, .btn-primary {{
    background-color: {COLOR_ACCENT};
    border-color: {COLOR_ACCENT_HOVER};
    color: #ffffff;
}}

QPushButton#btnPrimary:hover, .btn-primary:hover {{
    background-color: {COLOR_ACCENT_HOVER};
    border-color: #60a5fa;
}}

QPushButton#btnSuccess, .btn-success {{
    background-color: #16a34a;
    border-color: {COLOR_SUCCESS};
    color: #ffffff;
}}

QPushButton#btnSuccess:hover, .btn-success:hover {{
    background-color: {COLOR_SUCCESS};
    border-color: #4ade80;
}}

QPushButton#btnDanger, .btn-danger {{
    background-color: #dc2626;
    border-color: {COLOR_DANGER};
    color: #ffffff;
}}

QPushButton#btnDanger:hover, .btn-danger:hover {{
    background-color: {COLOR_DANGER};
    border-color: #f87171;
}}

/* Line Inputs */
QLineEdit {{
    background-color: {COLOR_BG_DARKEST};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: {COLOR_ACCENT};
}}

QLineEdit:focus {{
    border: 1px solid {COLOR_ACCENT_HOVER};
    background-color: #020617;
}}

QLineEdit:disabled {{
    background-color: {COLOR_BG_CARD};
    color: {COLOR_TEXT_MUTED};
    border-color: {COLOR_BORDER};
}}

/* Multi-line Text Displays */
QTextEdit, QPlainTextEdit {{
    background-color: {COLOR_BG_DARKEST};
    color: #e2e8f0;
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 8px;
    font-family: 'Consolas', 'Cascadia Code', 'Fira Code', monospace;
    font-size: 11px;
    line-height: 1.4;
    selection-background-color: {COLOR_ACCENT};
}}

QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {COLOR_ACCENT_HOVER};
}}

/* Dropdowns (ComboBox) */
QComboBox {{
    background-color: {COLOR_BG_CARD};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 5px 10px;
    min-height: 24px;
}}

QComboBox:hover {{
    border-color: {COLOR_ACCENT_HOVER};
}}

QComboBox:on {{
    border-color: {COLOR_ACCENT};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid {COLOR_BORDER};
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}}

QComboBox::down-arrow {{
    width: 8px;
    height: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLOR_BG_CARD};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    selection-background-color: {COLOR_ACCENT};
    selection-color: #ffffff;
    padding: 4px;
    outline: none;
}}

/* Checkboxes */
QCheckBox {{
    color: {COLOR_TEXT_PRIMARY};
    spacing: 7px;
    font-weight: 500;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {COLOR_BORDER_LIGHT};
    border-radius: 4px;
    background-color: {COLOR_BG_DARKEST};
}}

QCheckBox::indicator:hover {{
    border-color: {COLOR_ACCENT_HOVER};
}}

QCheckBox::indicator:checked {{
    background-color: {COLOR_ACCENT};
    border-color: {COLOR_ACCENT_HOVER};
}}

QCheckBox::indicator:disabled {{
    background-color: {COLOR_BG_CARD};
    border-color: {COLOR_BORDER};
}}

QCheckBox:disabled {{
    color: {COLOR_TEXT_MUTED};
}}

/* Splitters: Subtle 2px divider with interactive glow */
QSplitter {{
    background-color: transparent;
}}

QSplitter::handle {{
    background-color: {COLOR_BORDER};
}}

QSplitter::handle:horizontal {{
    width: 2px;
}}

QSplitter::handle:vertical {{
    height: 2px;
}}

QSplitter::handle:hover {{
    background-color: {COLOR_ACCENT_HOVER};
}}

/* ScrollBars */
QScrollBar:vertical {{
    border: none;
    background: {COLOR_BG_DARK};
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background: {COLOR_BORDER};
    min-height: 28px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLOR_ACCENT_HOVER};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
    background: none;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    border: none;
    background: {COLOR_BG_DARK};
    height: 8px;
    margin: 0px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal {{
    background: {COLOR_BORDER};
    min-width: 28px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {COLOR_ACCENT_HOVER};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
    background: none;
}}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}

/* Progress Bar */
QProgressBar {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    text-align: center;
    color: #ffffff;
    font-weight: bold;
    font-size: 11px;
    background-color: {COLOR_BG_DARKEST};
    height: 16px;
}}

QProgressBar::chunk {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLOR_ACCENT}, stop:1 {COLOR_ACCENT_HOVER});
    border-radius: 5px;
}}

/* Tooltips */
QToolTip {{
    background-color: #020617;
    color: #f8fafc;
    border: 1px solid {COLOR_ACCENT};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 11px;
}}

/* Lists & Trees */
QListWidget, QListView, QTreeWidget, QTreeView {{
    background-color: {COLOR_BG_DARKEST};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    color: {COLOR_TEXT_PRIMARY};
    padding: 4px;
}}

QListWidget::item, QTreeWidget::item {{
    padding: 6px 8px;
    border-radius: 4px;
}}

QListWidget::item:hover, QTreeWidget::item:hover {{
    background-color: {COLOR_BG_CARD};
}}

QListWidget::item:selected, QTreeWidget::item:selected {{
    background-color: {COLOR_ACCENT};
    color: #ffffff;
}}

/* Badges / Status Labels */
.badge-ready {{
    color: {COLOR_SUCCESS};
    background-color: {COLOR_SUCCESS_BG};
    border: 1px solid {COLOR_SUCCESS_BORDER};
    border-radius: 6px;
    padding: 2px 8px;
    font-weight: bold;
}}

.badge-thinking {{
    color: {COLOR_INFO};
    background-color: {COLOR_INFO_BG};
    border: 1px solid {COLOR_INFO_BORDER};
    border-radius: 6px;
    padding: 2px 8px;
    font-weight: bold;
}}

.badge-warning {{
    color: {COLOR_WARNING};
    background-color: {COLOR_WARNING_BG};
    border: 1px solid {COLOR_WARNING_BORDER};
    border-radius: 6px;
    padding: 2px 8px;
    font-weight: bold;
}}

.badge-error {{
    color: {COLOR_DANGER};
    background-color: {COLOR_DANGER_BG};
    border: 1px solid {COLOR_DANGER_BORDER};
    border-radius: 6px;
    padding: 2px 8px;
    font-weight: bold;
}}
"""


def apply_dark_theme(app_or_widget: Union[QApplication, QWidget]) -> None:
    """
    Applies the modern Cyber/Pro Dark theme and palette to a QApplication or QWidget.

    Args:
        app_or_widget: The target QApplication instance or root QWidget.
    """
    if isinstance(app_or_widget, QApplication):
        app_or_widget.setStyle("Fusion")

        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(15, 23, 42))          # #0f172a
        palette.setColor(QPalette.ColorRole.WindowText, QColor(248, 250, 252))   # #f8fafc
        palette.setColor(QPalette.ColorRole.Base, QColor(11, 15, 25))            # #0b0f19
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(30, 41, 59))   # #1e293b
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(2, 6, 23))       # #020617
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(248, 250, 252))
        palette.setColor(QPalette.ColorRole.Text, QColor(248, 250, 252))
        palette.setColor(QPalette.ColorRole.Button, QColor(30, 41, 59))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(248, 250, 252))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(239, 68, 68))
        palette.setColor(QPalette.ColorRole.Link, QColor(59, 130, 246))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(37, 99, 235))      # #2563eb
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        app_or_widget.setPalette(palette)

    app_or_widget.setStyleSheet(DARK_QSS)
