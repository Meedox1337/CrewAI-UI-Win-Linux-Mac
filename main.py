"""
Local Crew Cockpit - Application Entry Point (PyQt6)
High-performance desktop cockpit for transparent local CrewAI agent workflows.
"""

import logging
import os
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

try:
    from ui.main_window import CrewMainWindow
except ImportError:
    # Forward-compatible placeholder for upcoming PyQt6 main window
    from PyQt6.QtWidgets import QMainWindow, QWidget

    class CrewMainWindow(QMainWindow):  # type: ignore[no-redef]
        """Placeholder for CrewMainWindow until ui/main_window.py PyQt6 conversion."""

        def __init__(self, ollama_host: str = "http://localhost:11434", parent: QWidget = None) -> None:
            super().__init__(parent)
            self.ollama_host = ollama_host
            self.setWindowTitle("Local Crew Cockpit (PyQt6)")
            self.resize(1360, 860)

from core.logger import setup_logging, is_debug

# Global Logging Setup (supports --debug and COCKPIT_DEBUG=1)
setup_logging()
logger = logging.getLogger("LocalCrewCockpit")


def apply_dark_theme(app: QApplication) -> None:
    """Configures Fusion style with dark palette for maximum desktop readability."""
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(24, 27, 33))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(226, 232, 240))
    palette.setColor(QPalette.ColorRole.Base, QColor(15, 17, 23))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(30, 35, 45))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(15, 23, 42))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(241, 245, 249))
    palette.setColor(QPalette.ColorRole.Text, QColor(226, 232, 240))
    palette.setColor(QPalette.ColorRole.Button, QColor(31, 41, 55))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(241, 245, 249))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(239, 68, 68))
    palette.setColor(QPalette.ColorRole.Link, QColor(59, 130, 246))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(37, 99, 235))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)


def main() -> None:
    """Initializes and runs the Local Crew Cockpit PyQt6 application."""
    logger.info("Starting Local Crew Cockpit (PyQt6)...")

    # High-DPI Scaling & Dark Mode Flags for Windows
    if sys.platform == "win32":
        os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
        os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")
        os.environ.setdefault("QT_QPA_PLATFORM", "windows:darkmode=2")

    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except AttributeError:
        pass

    app = QApplication(sys.argv)
    app.setApplicationName("Local Crew Cockpit")
    app.setApplicationDisplayName("Local Crew Cockpit")

    apply_dark_theme(app)

    try:
        window = CrewMainWindow(ollama_host="http://localhost:11434")
        window.show()
        sys.exit(app.exec())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user. Exiting cleanly.")
        sys.exit(0)
    except Exception as exc:
        logger.critical("Fatal application error: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
