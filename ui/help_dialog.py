"""
Local Crew Cockpit - Help & Hardware Advisor Dialog (PyQt6)
Provides an onboarding 3-step guide and dynamic hardware-tailored prompt generation
for external AI assistants (ChatGPT, Claude, etc.) to get model recommendations.
"""

import logging
import os
import platform
import sys
from typing import Any, Dict, Optional

import psutil
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.locales import t
from core.system_monitor import get_system_monitor

logger = logging.getLogger(__name__)


def get_system_hardware_specs() -> Dict[str, str]:
    """
    Dynamically probes host hardware specifications:
    - GPU device name (e.g. 'NVIDIA GeForce RTX 4070' / 'NVIDIA GeForce RTX 5090')
    - Dedicated GPU VRAM in GB (e.g. '12.0 GB' / '31.8 GB')
    - System RAM in GB (e.g. '32.0 GB' / '61.6 GB')
    - CPU model name (e.g. 'AMD Ryzen 7 9800X3D 8-Core Processor')
    - Operating System (e.g. 'Windows 11 (64-Bit)')

    Falls back cleanly if no dedicated NVIDIA GPU is found or NVML is unavailable.
    """
    # 1. CPU Detection
    cpu_name = ""
    if platform.system() == "Windows":
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            )
            raw_cpu = winreg.QueryValueEx(key, "ProcessorNameString")[0]
            if raw_cpu:
                cpu_name = str(raw_cpu).strip()
        except Exception as exc:
            logger.debug("Winreg CPU query fallback: %s", exc)

    if not cpu_name:
        cpu_name = platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", "Unbekannte CPU")

    # 2. System RAM Detection
    try:
        ram_gb = round(psutil.virtual_memory().total / (1024.0 ** 3), 1)
        ram_str = f"{ram_gb:.1f} GB"
    except Exception:
        ram_str = "Unbekannt"

    # 3. Operating System Detection
    system = platform.system()
    if system == "Windows":
        try:
            ver = sys.getwindowsversion()
            os_name = "Windows 11" if getattr(ver, "build", 0) >= 22000 else "Windows 10"
        except Exception:
            os_name = f"Windows {platform.release()}"
        arch = "64-Bit" if platform.architecture()[0] == "64bit" else "32-Bit"
        os_str = f"{os_name} ({arch})"
    elif system == "Darwin":
        os_str = f"macOS {platform.mac_ver()[0]} ({platform.machine()})"
    elif system == "Linux":
        os_str = f"Linux {platform.release()} ({platform.machine()})"
    else:
        os_str = f"{system} ({platform.machine()})"

    # 4. GPU & Physical VRAM Detection via SystemMonitor / NVML
    gpu_name = "Keine dedizierte NVIDIA-GPU erkannt (CPU-Only-Betrieb)"
    vram_str = "Kein dedizierter VRAM (Shared Memory)"

    try:
        mon = get_system_monitor()
        mem = mon.get_memory_status()
        if mem.get("is_gpu"):
            dev_name = mem.get("device_name")
            if dev_name:
                gpu_name = str(dev_name)
            total_vram = float(mem.get("total_gb", 0.0))
            if total_vram > 0:
                vram_str = f"{total_vram:.1f} GB"
    except Exception as exc:
        logger.debug("Hardware query GPU check failed: %s", exc)

    return {
        "gpu": gpu_name,
        "vram": vram_str,
        "ram": ram_str,
        "cpu": cpu_name,
        "os": os_str,
    }


def generate_ai_hardware_prompt(lang: str = "de") -> str:
    """
    Generates a ready-to-copy AI recommendation prompt for ChatGPT, Claude,
    Perplexity, etc. with exact, dynamically detected host hardware metrics.
    """
    specs = get_system_hardware_specs()

    if lang == "en":
        return (
            "Hello! I am using the Local Crew Cockpit (CrewAI + Ollama) and would like to know which "
            "local LLMs are best suited for my system.\n\n"
            "My hardware specifications:\n"
            f"- GPU: {specs['gpu']}\n"
            f"- GPU-VRAM: {specs['vram']}\n"
            f"- System-RAM: {specs['ram']}\n"
            f"- CPU: {specs['cpu']}\n"
            f"- Operating System: {specs['os']}\n\n"
            "Please recommend suitable Ollama models (including parameter scale and quantization, e.g. q4_K_M) "
            "for a 3-agent team:\n"
            "1. A model for Architecture & Reasoning (Planning)\n"
            "2. A model for Code Generation (Development)\n"
            "3. A lightweight model for Research & Documentation\n\n"
            "Important: The models must fit reliably into my GPU VRAM without causing Out-of-Memory errors."
        )

    # German standard prompt template
    return (
        "Hallo! Ich nutze das Local Crew Cockpit (CrewAI + Ollama) und möchte wissen, welche "
        "lokalen LLMs für mein System optimal geeignet sind.\n\n"
        "Meine Hardware-Spezifikationen:\n"
        f"- GPU: {specs['gpu']}\n"
        f"- GPU-VRAM: {specs['vram']}\n"
        f"- System-RAM: {specs['ram']}\n"
        f"- CPU: {specs['cpu']}\n"
        f"- Betriebssystem: {specs['os']}\n\n"
        "Bitte empfiehl mir passende Ollama-Modelle (inkl. Parametergröße und Quantisierung, z. B. q4_K_M) "
        "für ein 3er-Team:\n"
        "1. Ein Modell für Architektur & Reasoning (Planung)\n"
        "2. Ein Modell für Code-Generierung (Entwicklung)\n"
        "3. Ein leichtgewichtiges Modell für Recherche & Dokumentation\n\n"
        "Wichtig: Die Modelle müssen stabil in meinen GPU-VRAM passen, ohne Out-of-Memory-Fehler zu verursachen."
    )


class CockpitHelpDialog(QDialog):
    """
    Comprehensive Onboarding and Hardware Advisor modal dialog (PyQt6).
    Displays real-time hardware specifications and provides a 1-click dynamic AI prompt.
    """

    def __init__(self, parent: Optional[QWidget] = None, lang: str = "de") -> None:
        super().__init__(parent)
        self.lang = lang
        self.specs = get_system_hardware_specs()
        self.prompt_text = generate_ai_hardware_prompt(lang=self.lang)

        self.resize(780, 680)
        self.setMinimumSize(620, 520)
        self.setWindowTitle(
            "🚀 Local Crew Cockpit - Schnellstart & System-Empfehlungen"
            if self.lang == "de"
            else "🚀 Local Crew Cockpit - Quickstart & Hardware Advisor"
        )
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet(
            "QDialog { background-color: #0b0f19; color: #f8fafc; font-family: 'Segoe UI', sans-serif; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header Title & Subtitle
        header_box = QVBoxLayout()
        header_box.setSpacing(4)
        title = QLabel(
            "🚀 Local Crew Cockpit - Schnellstart & Hardware-Berater"
            if self.lang == "de"
            else "🚀 Local Crew Cockpit - Quickstart & Hardware Advisor"
        )
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #38bdf8;")
        header_box.addWidget(title)

        subtitle = QLabel(
            "Leitfaden für Multi-Agenten-Workflows und KI-Kopierprompt mit deinen echten Hardwaredaten."
            if self.lang == "de"
            else "Guide for multi-agent workflows and tailored AI prompt with your live system metrics."
        )
        subtitle.setStyleSheet("color: #94a3b8; font-size: 11px;")
        header_box.addWidget(subtitle)
        layout.addLayout(header_box)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(4, 4, 8, 4)
        content_layout.setSpacing(16)

        # --- Card 1: Dynamically Detected Hardware Overview ---
        hw_card = QFrame()
        hw_card.setStyleSheet(
            "QFrame { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 6px; padding: 6px; }"
        )
        hw_layout = QVBoxLayout(hw_card)
        hw_layout.setSpacing(8)

        hw_title = QLabel(
            "🖥️ Erkannte System-Hardware:"
            if self.lang == "de"
            else "🖥️ Detected Workstation Hardware:"
        )
        hw_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        hw_title.setStyleSheet("color: #38bdf8; border: none;")
        hw_layout.addWidget(hw_title)

        hw_grid = QVBoxLayout()
        hw_grid.setSpacing(4)

        # Row 1: GPU & VRAM
        row_gpu = QLabel(
            f"<b>GPU:</b> <span style='color: #86efac;'>{self.specs['gpu']}</span> "
            f"| <b>VRAM:</b> <span style='color: #38bdf8;'>{self.specs['vram']}</span>"
        )
        row_gpu.setStyleSheet("color: #cbd5e1; font-size: 11px; border: none;")
        hw_grid.addWidget(row_gpu)

        # Row 2: RAM & CPU
        row_cpu = QLabel(
            f"<b>CPU:</b> <span style='color: #f1f5f9;'>{self.specs['cpu']}</span> "
            f"| <b>System-RAM:</b> <span style='color: #fbbf24;'>{self.specs['ram']}</span>"
        )
        row_cpu.setStyleSheet("color: #cbd5e1; font-size: 11px; border: none;")
        hw_grid.addWidget(row_cpu)

        # Row 3: OS
        row_os = QLabel(f"<b>Betriebssystem:</b> <span style='color: #94a3b8;'>{self.specs['os']}</span>")
        row_os.setStyleSheet("color: #cbd5e1; font-size: 11px; border: none;")
        hw_grid.addWidget(row_os)

        hw_layout.addLayout(hw_grid)
        content_layout.addWidget(hw_card)

        # --- Card 2: AI Copy-Paste Prompt Section ---
        prompt_card = QFrame()
        prompt_card.setStyleSheet(
            "QFrame { background-color: #0f172a; border: 1px solid #334155; border-radius: 6px; padding: 6px; }"
        )
        p_layout = QVBoxLayout(prompt_card)
        p_layout.setSpacing(8)

        p_title = QLabel(
            "💡 KI-Prompt für individuelle Modell-Empfehlungen (Hardware-basiert)"
            if self.lang == "de"
            else "💡 AI Prompt for Tailored Model Recommendations"
        )
        p_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        p_title.setStyleSheet("color: #facc15; border: none;")
        p_layout.addWidget(p_title)

        p_desc = QLabel(
            "Kopiere diesen Prompt und füge ihn in ChatGPT, Claude oder Perplexity ein, um sofort "
            "perfekt abgestimmte Ollama-Modell-Empfehlungen für deine genaue Hardware zu erhalten:"
            if self.lang == "de"
            else "Copy and paste this prompt into ChatGPT, Claude, or Perplexity to receive "
            "optimally tailored Ollama model recommendations for your exact hardware:"
        )
        p_desc.setWordWrap(True)
        p_desc.setStyleSheet("color: #94a3b8; font-size: 11px; border: none;")
        p_layout.addWidget(p_desc)

        self.txt_prompt = QTextEdit()
        self.txt_prompt.setReadOnly(True)
        self.txt_prompt.setFixedHeight(150)
        self.txt_prompt.setPlainText(self.prompt_text)
        self.txt_prompt.setStyleSheet(
            "QTextEdit { background-color: #05080e; color: #f8fafc; border: 1px solid #334155; "
            "border-radius: 4px; padding: 8px; font-family: 'Consolas', 'Courier New', monospace; "
            "font-size: 11px; line-height: 1.4; }"
        )
        p_layout.addWidget(self.txt_prompt)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_copy_prompt = QPushButton(
            "📋 In Zwischenablage kopieren"
            if self.lang == "de"
            else "📋 Copy to Clipboard"
        )
        self.btn_copy_prompt.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_copy_prompt.setStyleSheet(
            "QPushButton { background-color: #2563eb; color: #ffffff; font-weight: bold; "
            "padding: 7px 16px; border-radius: 4px; font-size: 11px; border: none; } "
            "QPushButton:hover { background-color: #1d4ed8; }"
        )
        self.btn_copy_prompt.clicked.connect(self._copy_prompt)
        btn_row.addWidget(self.btn_copy_prompt)

        lbl_hint = QLabel(
            "Enthält automatisch deine GPU, VRAM, RAM, CPU & OS"
            if self.lang == "de"
            else "Automatically includes your GPU, VRAM, RAM, CPU & OS"
        )
        lbl_hint.setStyleSheet("color: #64748b; font-size: 10px; font-style: italic; border: none;")
        btn_row.addWidget(lbl_hint)
        btn_row.addStretch()

        p_layout.addLayout(btn_row)
        content_layout.addWidget(prompt_card)

        # --- Card 3: 3-Step Quickstart Guide ---
        guide_card = QFrame()
        guide_card.setStyleSheet(
            "QFrame { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 6px; padding: 6px; }"
        )
        g_layout = QVBoxLayout(guide_card)
        g_layout.setSpacing(10)

        g_title = QLabel(
            "📖 Schnellstart in 3 Schritten:"
            if self.lang == "de"
            else "📖 3-Step Quickstart Guide:"
        )
        g_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        g_title.setStyleSheet("color: #38bdf8; border: none;")
        g_layout.addWidget(g_title)

        # Step 1
        s1_title = QLabel("1. " + t("help_step_1_title", lang=self.lang))
        s1_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #60a5fa; border: none;")
        s1_desc = QLabel(t("help_step_1_desc", lang=self.lang))
        s1_desc.setWordWrap(True)
        s1_desc.setStyleSheet("color: #94a3b8; font-size: 11px; border: none;")
        g_layout.addWidget(s1_title)
        g_layout.addWidget(s1_desc)

        # Step 2
        s2_title = QLabel("2. " + t("help_step_2_title", lang=self.lang))
        s2_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #60a5fa; border: none;")
        s2_desc = QLabel(t("help_step_2_desc", lang=self.lang))
        s2_desc.setWordWrap(True)
        s2_desc.setStyleSheet("color: #94a3b8; font-size: 11px; border: none;")
        g_layout.addWidget(s2_title)
        g_layout.addWidget(s2_desc)

        # Step 3
        s3_title = QLabel("3. " + t("help_step_3_title", lang=self.lang))
        s3_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #60a5fa; border: none;")
        s3_desc = QLabel(t("help_step_3_desc", lang=self.lang))
        s3_desc.setWordWrap(True)
        s3_desc.setStyleSheet("color: #94a3b8; font-size: 11px; border: none;")
        g_layout.addWidget(s3_title)
        g_layout.addWidget(s3_desc)

        content_layout.addWidget(guide_card)
        content_layout.addStretch()

        scroll.setWidget(content_widget)
        layout.addWidget(scroll, stretch=1)

        # Bottom Close Button Bar
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()

        btn_close = QPushButton(t("close", lang=self.lang))
        btn_close.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; "
            "font-weight: bold; padding: 6px 20px; border-radius: 4px; font-size: 11px; } "
            "QPushButton:hover { background-color: #334155; color: #ffffff; }"
        )
        btn_close.clicked.connect(self.accept)
        bottom_bar.addWidget(btn_close)

        layout.addLayout(bottom_bar)

    def _copy_prompt(self) -> None:
        """Copies the dynamic AI hardware prompt to clipboard and gives visual feedback."""
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self.prompt_text)

        self.btn_copy_prompt.setText("✓ " + ("Kopiert!" if self.lang == "de" else "Copied!"))
        self.btn_copy_prompt.setStyleSheet(
            "QPushButton { background-color: #16a34a; color: #ffffff; font-weight: bold; "
            "padding: 7px 16px; border-radius: 4px; font-size: 11px; border: 1px solid #22c55e; }"
        )
        QTimer.singleShot(2500, self._reset_copy_btn)

    def _reset_copy_btn(self) -> None:
        self.btn_copy_prompt.setText(
            "📋 " + ("In Zwischenablage kopieren" if self.lang == "de" else "Copy to Clipboard")
        )
        self.btn_copy_prompt.setStyleSheet(
            "QPushButton { background-color: #2563eb; color: #ffffff; font-weight: bold; "
            "padding: 7px 16px; border-radius: 4px; font-size: 11px; border: none; } "
            "QPushButton:hover { background-color: #1d4ed8; }"
        )


# Backward compatibility alias
HelpDialog = CockpitHelpDialog
