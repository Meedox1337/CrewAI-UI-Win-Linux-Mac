"""
Local Crew Cockpit - Pipeline Agent Card Widget (PyQt6)
Represents an individual agent in the active pipeline team with model capabilities,
role selection, tool-permission gating, custom setup dialog, and live thought drawer.
"""

import logging
from typing import Any, Dict, List, Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.locales import (
    get_canonical_role_key,
    get_role_presets,
    get_role_template,
    t,
    translate_role,
)
from core.model_knowledge import (
    can_use_tools,
    evaluate_vram_status,
    get_model_specs,
    has_thinking_mode,
)
from ui.thought_drawer import ThoughtDrawer

logger = logging.getLogger(__name__)


class AgentSetupDialog(QDialog):
    """
    Modal dialog allowing users to customize an agent's individual Goal and Backstory.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        role: str = "",
        model_name: str = "",
        current_goal: str = "",
        current_backstory: str = "",
        lang: str = "de",
    ) -> None:
        super().__init__(parent)
        self.role = role
        self.model_name = model_name
        self.lang = lang

        self.resize(580, 420)
        self.setMinimumSize(450, 320)
        self._update_title()
        self._build_ui(current_goal, current_backstory)

    def _update_title(self) -> None:
        title = (
            f"⚙️ Agenten-Setup: {self.role} ({self.model_name})"
            if self.lang == "de"
            else f"⚙️ Agent Setup: {self.role} ({self.model_name})"
        )
        self.setWindowTitle(title)

    def _build_ui(self, initial_goal: str, initial_backstory: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header info
        lbl_info = QLabel(
            f"<b>{self.role}</b> &bull; <span style='color: #94a3b8;'>{self.model_name}</span>"
        )
        lbl_info.setStyleSheet("font-size: 13px; color: #38bdf8;")
        layout.addWidget(lbl_info)

        # Goal section
        lbl_goal = QLabel("<b>Ziel / Goal:</b>" if self.lang == "de" else "<b>Mission / Goal:</b>")
        lbl_goal.setStyleSheet("color: #e2e8f0; font-size: 11px;")
        layout.addWidget(lbl_goal)

        self.txt_goal = QLineEdit()
        self.txt_goal.setText(initial_goal)
        self.txt_goal.setPlaceholderText(
            "z. B. Entwerfe eine saubere, skalierbare Systemarchitektur..."
            if self.lang == "de"
            else "e.g. Design a clean, scalable system architecture..."
        )
        self.txt_goal.setStyleSheet(
            "background-color: #0f172a; color: #f8fafc; border: 1px solid #334155; "
            "border-radius: 5px; padding: 6px; font-size: 11px;"
        )
        layout.addWidget(self.txt_goal)

        # Backstory section
        lbl_backstory = QLabel(
            "<b>Hintergrundgeschichte / Backstory:</b>"
            if self.lang == "de"
            else "<b>Agent Backstory:</b>"
        )
        lbl_backstory.setStyleSheet("color: #e2e8f0; font-size: 11px;")
        layout.addWidget(lbl_backstory)

        self.txt_backstory = QTextEdit()
        self.txt_backstory.setPlainText(initial_backstory)
        self.txt_backstory.setPlaceholderText(
            "Beschreibe die Fachkompetenz und Arbeitsweise dieses Agenten..."
            if self.lang == "de"
            else "Describe the expertise and persona of this agent..."
        )
        self.txt_backstory.setStyleSheet(
            "background-color: #0f172a; color: #f8fafc; border: 1px solid #334155; "
            "border-radius: 5px; padding: 6px; font-size: 11px;"
        )
        layout.addWidget(self.txt_backstory)

        # Button row (Cancel & Save)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        btn_save = buttons.button(QDialogButtonBox.StandardButton.Save)
        btn_cancel = buttons.button(QDialogButtonBox.StandardButton.Cancel)

        if btn_save:
            btn_save.setText(t("save", lang=self.lang))
            btn_save.setStyleSheet(
                "background-color: #2563eb; color: #ffffff; font-weight: bold; padding: 6px 14px; border-radius: 4px;"
            )
        if btn_cancel:
            btn_cancel.setText(t("cancel", lang=self.lang))
            btn_cancel.setStyleSheet(
                "background-color: #334155; color: #cbd5e1; padding: 6px 12px; border-radius: 4px;"
            )

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self) -> Dict[str, str]:
        return {
            "goal": self.txt_goal.text().strip(),
            "backstory": self.txt_backstory.toPlainText().strip(),
        }


class PipelineCard(QFrame):
    """
    Modular PyQt6 card widget representing an agent in the active team pipeline.
    Displays model name, VRAM badge, role dropdown, tool permissions (Web, Write),
    setup modal trigger, inline thought drawer, status badge, and remove button.
    """

    move_up_requested = pyqtSignal(object)
    move_down_requested = pyqtSignal(object)
    remove_requested = pyqtSignal(object)
    config_changed = pyqtSignal()
    status_changed = pyqtSignal(str, str)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        model_name: str = "",
        order_index: int = 1,
        initial_role: Optional[str] = None,
        lang: str = "de",
    ) -> None:
        super().__init__(parent)
        self.model_name = model_name
        self.order_index = order_index
        self.lang = lang

        # Model knowledge specs
        self.specs = get_model_specs(model_name)
        self.tool_capable = self.specs.get("can_use_tools", False)
        self.has_thinking = self.specs.get("has_thinking", False)
        self.vram_gb = self.specs.get("vram_gb", 6.0)

        # Custom goal & backstory overrides
        self.custom_goal: Optional[str] = None
        self.custom_backstory: Optional[str] = None

        self.setObjectName("pipelineCard")
        self.setStyleSheet(
            "QFrame#pipelineCard {"
            "  background-color: #1e293b;"
            "  border: 1px solid #334155;"
            "  border-radius: 8px;"
            "}"
        )

        self._build_ui(initial_role)
        self._apply_tool_gating()

    def _build_ui(self, initial_role: Optional[str] = None) -> None:
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 8, 10, 8)
        self.main_layout.setSpacing(6)

        # Top horizontal row
        top_row = QHBoxLayout()
        top_row.setContentsMargins(10, 4, 10, 4)
        top_row.setSpacing(8)

        # 1. Order control element (#X with [▲] and [▼])
        order_box = QWidget()
        order_box.setFixedWidth(75)
        o_layout = QHBoxLayout(order_box)
        o_layout.setContentsMargins(0, 0, 0, 0)
        o_layout.setSpacing(3)

        self.lbl_order = QLabel(f"#{self.order_index}")
        self.lbl_order.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_order.setFixedWidth(28)
        self.lbl_order.setStyleSheet(
            "font-weight: 800; font-size: 12px; color: #38bdf8; "
            "background-color: #0f172a; padding: 3px 2px; border-radius: 4px; "
            "border: 1px solid #1e293b;"
        )
        self.lbl_order.setToolTip(
            "Pipeline-Reihenfolge dieses Agenten"
            if self.lang == "de"
            else "Execution order of this agent"
        )
        o_layout.addWidget(self.lbl_order)

        btn_col = QVBoxLayout()
        btn_col.setContentsMargins(0, 0, 0, 0)
        btn_col.setSpacing(1)

        self.btn_up = QPushButton("▲")
        self.btn_up.setFixedSize(18, 13)
        self.btn_up.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; border-radius: 2px; font-size: 8px; padding: 0; }"
            "QPushButton:hover { background-color: #2563eb; color: #ffffff; border-color: #3b82f6; }"
            "QPushButton:disabled { color: #475569; background-color: #0f172a; border-color: #1e293b; }"
        )
        self.btn_up.setToolTip("Agent in der Reihenfolge nach oben verschieben" if self.lang == "de" else "Move agent up")
        self.btn_up.clicked.connect(lambda: self.move_up_requested.emit(self))
        btn_col.addWidget(self.btn_up)

        self.btn_down = QPushButton("▼")
        self.btn_down.setFixedSize(18, 13)
        self.btn_down.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; border-radius: 2px; font-size: 8px; padding: 0; }"
            "QPushButton:hover { background-color: #2563eb; color: #ffffff; border-color: #3b82f6; }"
            "QPushButton:disabled { color: #475569; background-color: #0f172a; border-color: #1e293b; }"
        )
        self.btn_down.setToolTip("Agent in der Reihenfolge nach unten verschieben" if self.lang == "de" else "Move agent down")
        self.btn_down.clicked.connect(lambda: self.move_down_requested.emit(self))
        btn_col.addWidget(self.btn_down)

        o_layout.addLayout(btn_col)
        top_row.addWidget(order_box)

        # 2. Model & VRAM container
        model_vram_box = QWidget()
        model_vram_box.setMinimumWidth(170)
        mv_layout = QHBoxLayout(model_vram_box)
        mv_layout.setContentsMargins(0, 0, 0, 0)
        mv_layout.setSpacing(6)

        self.lbl_model = QLabel(self.model_name)
        self.lbl_model.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_model.setStyleSheet("color: #f8fafc;")
        self.lbl_model.setToolTip(f"Modell: {self.model_name}")
        mv_layout.addWidget(self.lbl_model)

        vram_status = evaluate_vram_status(self.vram_gb)
        self.lbl_vram = QLabel(f"~{self.vram_gb:.1f} GB")
        self.lbl_vram.setStyleSheet(
            f"background-color: {vram_status['bg']}; color: {vram_status['fg']}; font-size: 10px; font-weight: bold; "
            f"padding: 3px 6px; border-radius: 4px; border: 1px solid {vram_status['border']};"
        )
        self.lbl_vram.setToolTip(
            f"{vram_status['tooltip']} (Bedarf: ~{self.vram_gb:.1f} GB)"
        )
        mv_layout.addWidget(self.lbl_vram)
        mv_layout.addStretch()

        top_row.addWidget(model_vram_box, stretch=1)

        # 3. Role dropdown (QComboBox with standard presets & editable freetext)
        self.cb_role = QComboBox()
        self.cb_role.setEditable(True)
        self.cb_role.setFixedWidth(165)
        self._populate_role_presets(initial_role)
        self.cb_role.currentTextChanged.connect(self._on_role_changed)
        top_row.addWidget(self.cb_role)

        # 4. Checkbox [ ] Web
        self.chk_web = QCheckBox("Web")
        self.chk_web.setFixedWidth(55)
        self.chk_web.setStyleSheet("color: #e2e8f0; font-size: 11px;")
        self.chk_web.stateChanged.connect(lambda: self.config_changed.emit())
        top_row.addWidget(self.chk_web)

        # 5. Checkbox [ ] Write
        self.chk_write = QCheckBox("Write")
        self.chk_write.setFixedWidth(55)
        self.chk_write.setStyleSheet("color: #e2e8f0; font-size: 11px;")
        self.chk_write.stateChanged.connect(lambda: self.config_changed.emit())
        top_row.addWidget(self.chk_write)

        # 6. Button [⚙️ Setup]
        self.btn_setup = QPushButton("⚙️ Setup")
        self.btn_setup.setFixedWidth(70)
        self.btn_setup.setStyleSheet(
            "background-color: #1e293b; color: #cbd5e1; border: 1px solid #475569; "
            "border-radius: 4px; padding: 4px 6px; font-size: 11px;"
        )
        self.btn_setup.setToolTip(
            "Benutzerdefiniertes Ziel (Goal) und Hintergrund (Backstory) anpassen"
            if self.lang == "de"
            else "Configure custom agent goal and backstory"
        )
        self.btn_setup.clicked.connect(self._open_setup_dialog)
        top_row.addWidget(self.btn_setup)

        # 7. Button [💭 Gedanken / Output]
        thought_btn_label = "💭 " + (
            "Gedanken" if self.has_thinking else "Output"
        )
        self.btn_thought = QPushButton(thought_btn_label)
        self.btn_thought.setFixedWidth(95)
        self.btn_thought.setStyleSheet(
            "background-color: #1e293b; color: #93c5fd; border: 1px solid #3b82f6; "
            "border-radius: 4px; padding: 4px 6px; font-size: 11px;"
        )
        self.btn_thought.setToolTip(
            "Live-Gedanken & Output-Konsole ein-/ausklappen"
            if self.lang == "de"
            else "Toggle live thoughts and stream console"
        )
        self.btn_thought.clicked.connect(lambda: self.toggle_drawer())
        top_row.addWidget(self.btn_thought)

        # 8. Status badge (Bereit, In Aktion..., Fertig, Fehler)
        self.lbl_status = QLabel("Bereit" if self.lang == "de" else "Ready")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setFixedWidth(90)
        self.set_status("Bereit" if self.lang == "de" else "Ready", color_key="gray")
        top_row.addWidget(self.lbl_status)

        # 9. Button [🗑 Entfernen]
        self.btn_remove = QPushButton("🗑")
        self.btn_remove.setFixedWidth(40)
        self.btn_remove.setStyleSheet(
            "background-color: #450a0a; color: #f87171; border: 1px solid #991b1b; "
            "border-radius: 4px; padding: 4px 6px; font-weight: bold; font-size: 11px;"
        )
        self.btn_remove.setToolTip(
            "Diesen Agenten aus der Pipeline entfernen"
            if self.lang == "de"
            else "Remove this agent from the pipeline"
        )
        self.btn_remove.clicked.connect(lambda: self.remove_requested.emit(self))
        top_row.addWidget(self.btn_remove)

        self.main_layout.addLayout(top_row)

        # Inline collapsible ThoughtDrawer (hidden by default)
        self.drawer = ThoughtDrawer(self, model_name=self.model_name, lang=self.lang)
        self.drawer.hide()
        self.main_layout.addWidget(self.drawer)

    def _populate_role_presets(self, initial_role: Optional[str] = None) -> None:
        """Populates combo box with presets and selects appropriate role."""
        self.cb_role.blockSignals(True)
        self.cb_role.clear()
        presets = get_role_presets(self.lang)
        self.cb_role.addItems(presets)

        if initial_role:
            target = initial_role
        elif getattr(self, "order_index", 1) == 4:
            target = "Prüfer / Reviewer" if self.lang == "de" else "Reviewer"
        elif getattr(self, "order_index", 1) == 1:
            target = "Architekt" if self.lang == "de" else "Architect"
        elif getattr(self, "order_index", 1) in (2, 3):
            target = "Senior-Entwickler" if self.lang == "de" else "Senior Coder"
        else:
            target = self.specs.get("best_role", presets[0])

        translated = translate_role(target, target_lang=self.lang) or target

        idx = self.cb_role.findText(translated, Qt.MatchFlag.MatchFixedString)
        if idx >= 0:
            self.cb_role.setCurrentIndex(idx)
        else:
            self.cb_role.setEditText(translated)

        self.cb_role.blockSignals(False)

    def _apply_tool_gating(self) -> None:
        """Enforces safe disabling of Web and Write permissions for non-tool models."""
        if not self.tool_capable:
            self.chk_web.setChecked(False)
            self.chk_web.setEnabled(False)
            self.chk_web.setToolTip(t("pipeline_tooltip_web_disabled", lang=self.lang))

            self.chk_write.setChecked(False)
            self.chk_write.setEnabled(False)
            self.chk_write.setToolTip(t("pipeline_tooltip_write_disabled", lang=self.lang))
        else:
            self.chk_web.setEnabled(True)
            self.chk_web.setToolTip(t("model_tooltip_websearch", lang=self.lang))

            self.chk_write.setEnabled(True)
            write_tip = (
                "Erlaubt diesem Agenten, Dateien im Workspace anzulegen oder zu modifizieren."
                if self.lang == "de"
                else "Allows this agent to create or modify files directly in the workspace."
            )
            self.chk_write.setToolTip(write_tip)

    def _open_setup_dialog(self) -> None:
        """Opens dialog to customize Goal and Backstory."""
        cfg = self.get_config()
        dlg = AgentSetupDialog(
            parent=self.window(),
            role=cfg["role"],
            model_name=self.model_name,
            current_goal=cfg["goal"],
            current_backstory=cfg["backstory"],
            lang=self.lang,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            vals = dlg.get_values()
            self.custom_goal = vals["goal"]
            self.custom_backstory = vals["backstory"]
            self.config_changed.emit()

    def _on_role_changed(self) -> None:
        # Clear custom overrides if user switches preset role so defaults adapt
        self.custom_goal = None
        self.custom_backstory = None
        self.config_changed.emit()

    def toggle_drawer(self, *args: Any, visible: Optional[bool] = None) -> None:
        """Toggles the inline ThoughtDrawer visibility."""
        if visible is None or (isinstance(visible, bool) and args):
            new_vis = self.drawer.isHidden()
        else:
            new_vis = bool(visible)

        self.drawer.setVisible(new_vis)
        if new_vis:
            self.btn_thought.setStyleSheet(
                "background-color: #1d4ed8; color: #ffffff; border: 1px solid #60a5fa; "
                "border-radius: 4px; padding: 4px 6px; font-size: 11px;"
            )
        else:
            self.btn_thought.setStyleSheet(
                "background-color: #1e293b; color: #93c5fd; border: 1px solid #3b82f6; "
                "border-radius: 4px; padding: 4px 6px; font-size: 11px;"
            )

        self.adjustSize()
        if self.parentWidget():
            self.parentWidget().adjustSize()

    def set_move_buttons_enabled(self, can_move_up: bool, can_move_down: bool) -> None:
        """Enables or disables reorder buttons based on position in team."""
        self.btn_up.setEnabled(can_move_up)
        self.btn_down.setEnabled(can_move_down)

    def set_order_index(self, index: int) -> None:
        """Updates display sequence number."""
        self.order_index = index
        self.lbl_order.setText(f"#{index}")

    def set_position_index(self, index: int) -> None:
        """Sets display position index (#1, #2, ...)."""
        self.set_order_index(index)

    def set_status(self, status: str, color_key: str = "gray") -> None:
        """
        Updates the status badge text and styling.
        Supported color keys:
          - 'gray' / 'ready': Bereit (idle)
          - 'yellow' / 'running' / 'action': In Aktion...
          - 'green' / 'done': Fertig
          - 'red' / 'error': Fehler
        """
        key_lower = (color_key or "").lower()
        status_clean = status.strip()

        if key_lower in ("yellow", "running", "action", "in_action"):
            style = (
                "background-color: #854d0e; color: #fef08a; border: 1px solid #eab308; "
                "border-radius: 4px; padding: 3px 8px; font-weight: bold; font-size: 11px;"
            )
        elif key_lower in ("green", "done", "success", "finished"):
            style = (
                "background-color: #14532d; color: #86efac; border: 1px solid #22c55e; "
                "border-radius: 4px; padding: 3px 8px; font-weight: bold; font-size: 11px;"
            )
        elif key_lower in ("red", "error", "failed"):
            style = (
                "background-color: #7f1d1d; color: #fca5a5; border: 1px solid #ef4444; "
                "border-radius: 4px; padding: 3px 8px; font-weight: bold; font-size: 11px;"
            )
        else:  # Gray / Ready fallback
            style = (
                "background-color: #334155; color: #cbd5e1; border: 1px solid #475569; "
                "border-radius: 4px; padding: 3px 8px; font-weight: bold; font-size: 11px;"
            )

        self.lbl_status.setText(status_clean)
        self.lbl_status.setStyleSheet(style)
        self.status_changed.emit(status_clean, color_key)

    def append_stream_text(self, token: str, is_thought: bool = False) -> None:
        """Streams tokens into the embedded ThoughtDrawer."""
        self.drawer.append_text(token, is_thought=is_thought)

    def set_task_output_if_empty(self, text: str) -> bool:
        """
        Populates the drawer with the final task output if currently empty.
        Returns True if text was inserted, False if the drawer already contained text.
        """
        if not self.drawer.txt_output.toPlainText().strip() and text and text.strip():
            self.drawer.append_text(text.strip(), is_thought=False)
            return True
        return False

    def clear_drawer(self) -> None:
        """Clears text in the embedded drawer."""
        self.drawer.clear()

    def get_config(self) -> Dict[str, Any]:
        """
        Extracts complete agent configuration:
        role name, model name, tool flags (web & write), goal, and backstory.
        """
        role = self.cb_role.currentText().strip()
        template = get_role_template(role, lang=self.lang)

        goal = self.custom_goal if self.custom_goal is not None else template.get("goal", "")
        backstory = (
            self.custom_backstory
            if self.custom_backstory is not None
            else template.get("backstory", "")
        )

        return {
            "model_name": self.model_name,
            "role": role,
            "web": self.chk_web.isChecked() and self.chk_web.isEnabled(),
            "write": self.chk_write.isChecked() and self.chk_write.isEnabled(),
            "goal": goal,
            "backstory": backstory,
            "order": self.order_index,
            "vram_gb": self.vram_gb,
            "has_thinking": self.has_thinking,
            "canonical_role": get_canonical_role_key(role),
        }

    def set_language(self, lang: str) -> None:
        """Adapts localized texts across the card and embedded drawer."""
        self.lang = lang
        current_role = self.cb_role.currentText().strip()
        self._populate_role_presets(initial_role=current_role)
        self._apply_tool_gating()

        thought_btn_label = "💭 " + (
            "Gedanken" if self.has_thinking else "Output"
        )
        self.btn_thought.setText(thought_btn_label)
        self.drawer.set_language(lang)
