"""
Local Crew Cockpit - Pipeline Team Component (Zone 2)
Manages the active multi-agent pipeline team, column legend, re-ordering,
agent addition/removal, and card thought/status dispatching.
"""

import logging
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.locales import t
from ui.pipeline_card import PipelineCard

logger = logging.getLogger(__name__)


class PipelineWidget(QFrame):
    """
    Zone 2: Active Pipeline Team Component.
    Manages active PipelineCards, order indices, drag/arrow reordering,
    and agent execution states.
    """

    card_added = pyqtSignal(str, int)
    card_removed = pyqtSignal(str)
    order_changed = pyqtSignal()
    log_emitted = pyqtSignal(str, str)

    def __init__(self, parent: Optional[QWidget] = None, lang: str = "de") -> None:
        super().__init__(parent)
        self.lang = lang
        self.pipeline_cards: List[PipelineCard] = []

        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet(
            "QFrame { background-color: #0b0f19; border: 1px solid #1e293b; border-radius: 6px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Header row
        top_header = QHBoxLayout()
        self.lbl_title = QLabel("👥 " + t("pipeline_team_title", lang=self.lang))
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 12px; color: #60a5fa;")
        top_header.addWidget(self.lbl_title)
        top_header.addStretch()

        self.lbl_team_count = QLabel("0 Agenten aktiv" if self.lang == "de" else "0 agents active")
        self.lbl_team_count.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold;")
        top_header.addWidget(self.lbl_team_count)
        layout.addLayout(top_header)

        # Column Header Legend
        legend_frame = QFrame()
        legend_frame.setStyleSheet(
            "QFrame { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 4px; }"
        )
        legend_layout = QHBoxLayout(legend_frame)
        legend_layout.setContentsMargins(10, 4, 10, 4)
        legend_layout.setSpacing(8)

        self.lbl_hdr_pos = QLabel("Pos")
        self.lbl_hdr_pos.setFixedWidth(75)
        self.lbl_hdr_pos.setStyleSheet("color: #64748b; font-size: 11px; font-weight: bold;")
        legend_layout.addWidget(self.lbl_hdr_pos)

        self.lbl_hdr_model = QLabel("Modell & VRAM" if self.lang == "de" else "Model & VRAM")
        self.lbl_hdr_model.setMinimumWidth(170)
        self.lbl_hdr_model.setStyleSheet("color: #64748b; font-size: 11px; font-weight: bold;")
        legend_layout.addWidget(self.lbl_hdr_model, stretch=1)

        self.lbl_hdr_role = QLabel("Rolle" if self.lang == "de" else "Role")
        self.lbl_hdr_role.setFixedWidth(165)
        self.lbl_hdr_role.setStyleSheet("color: #64748b; font-size: 11px; font-weight: bold;")
        legend_layout.addWidget(self.lbl_hdr_role)

        self.lbl_hdr_web = QLabel("Web")
        self.lbl_hdr_web.setFixedWidth(55)
        self.lbl_hdr_web.setStyleSheet("color: #64748b; font-size: 11px; font-weight: bold;")
        legend_layout.addWidget(self.lbl_hdr_web)

        self.lbl_hdr_write = QLabel("Write")
        self.lbl_hdr_write.setFixedWidth(55)
        self.lbl_hdr_write.setStyleSheet("color: #64748b; font-size: 11px; font-weight: bold;")
        legend_layout.addWidget(self.lbl_hdr_write)

        self.lbl_hdr_setup = QLabel("Setup")
        self.lbl_hdr_setup.setFixedWidth(70)
        self.lbl_hdr_setup.setStyleSheet("color: #64748b; font-size: 11px; font-weight: bold;")
        legend_layout.addWidget(self.lbl_hdr_setup)

        self.lbl_hdr_thought = QLabel("Gedanken" if self.lang == "de" else "Thoughts")
        self.lbl_hdr_thought.setFixedWidth(95)
        self.lbl_hdr_thought.setStyleSheet("color: #64748b; font-size: 11px; font-weight: bold;")
        legend_layout.addWidget(self.lbl_hdr_thought)

        self.lbl_hdr_status = QLabel("Status")
        self.lbl_hdr_status.setFixedWidth(90)
        self.lbl_hdr_status.setStyleSheet("color: #64748b; font-size: 11px; font-weight: bold;")
        legend_layout.addWidget(self.lbl_hdr_status)

        self.lbl_hdr_remove = QLabel("Löschen" if self.lang == "de" else "Remove")
        self.lbl_hdr_remove.setFixedWidth(40)
        self.lbl_hdr_remove.setStyleSheet("color: #64748b; font-size: 11px; font-weight: bold;")
        legend_layout.addWidget(self.lbl_hdr_remove)

        layout.addWidget(legend_frame)

        # Scroll area for PipelineCards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        if scroll.viewport():
            scroll.viewport().setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(6)

        # Empty placeholder label
        self.lbl_empty_team = QLabel(
            "Noch keine Agenten im Team.\nKlicke oben bei einem Modell auf [➕ Ins Team holen]."
            if self.lang == "de"
            else "No agents in pipeline team.\nClick [➕ Add to Team] on any model above."
        )
        self.lbl_empty_team.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty_team.setStyleSheet("color: #64748b; padding: 24px; font-size: 12px;")
        self.cards_layout.addWidget(self.lbl_empty_team)

        self.cards_layout.addStretch()
        scroll.setWidget(self.cards_container)
        layout.addWidget(scroll, stretch=1)

    def add_pipeline_card(self, model_name: str, role: Optional[str] = None) -> PipelineCard:
        """
        Instantiates and adds a new PipelineCard widget to the active team pipeline.
        Permits adding identical models multiple times for distinct roles.
        """
        self.cards_container.setUpdatesEnabled(False)
        try:
            order = len(self.pipeline_cards) + 1
            if role is None:
                if order == 1:
                    role = "Architekt" if self.lang == "de" else "Architect"
                elif order in (2, 3):
                    role = "Senior-Entwickler" if self.lang == "de" else "Senior Coder"
                elif order == 4:
                    role = "Prüfer / Reviewer" if self.lang == "de" else "Reviewer"

            card = PipelineCard(
                parent=self,
                model_name=model_name,
                order_index=order,
                initial_role=role,
                lang=self.lang,
            )
            card.remove_requested.connect(self._remove_pipeline_card)
            card.move_up_requested.connect(self._move_card_up)
            card.move_down_requested.connect(self._move_card_down)

            self.pipeline_cards.append(card)
            # Insert before bottom stretch
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

            self.update_positions()
            self._update_pipeline_ui_state()
            self.log_emitted.emit(
                f"Agent #{order} mit Modell '{model_name}' zum Team hinzugefügt.", "SYSTEM"
            )
            self.card_added.emit(model_name, order)
            return card
        finally:
            self.cards_container.setUpdatesEnabled(True)

    def _remove_pipeline_card(self, card: PipelineCard) -> None:
        """Removes card from pipeline without affecting installed files on disk."""
        if card in self.pipeline_cards:
            model_name = card.model_name
            self.cards_container.setUpdatesEnabled(False)
            try:
                self.pipeline_cards.remove(card)
                card.setParent(None)
                card.deleteLater()

                self.update_positions()
                self._update_pipeline_ui_state()
                self.log_emitted.emit("Agent aus der Pipeline entfernt.", "SYSTEM")
                self.card_removed.emit(model_name)
            finally:
                self.cards_container.setUpdatesEnabled(True)

    def _move_card_up(self, card: PipelineCard) -> None:
        """Moves card one position up in pipeline and layout."""
        if card not in self.pipeline_cards:
            return
        idx = self.pipeline_cards.index(card)
        if idx > 0:
            self.cards_container.setUpdatesEnabled(False)
            try:
                self.pipeline_cards[idx], self.pipeline_cards[idx - 1] = (
                    self.pipeline_cards[idx - 1],
                    self.pipeline_cards[idx],
                )
                self.cards_layout.removeWidget(card)
                self.cards_layout.insertWidget(idx - 1, card)
                self.update_positions()
                self.log_emitted.emit(f"Agent #{idx + 1} nach oben verschoben.", "SYSTEM")
                self.order_changed.emit()
            finally:
                self.cards_container.setUpdatesEnabled(True)

    def _move_card_down(self, card: PipelineCard) -> None:
        """Moves card one position down in pipeline and layout."""
        if card not in self.pipeline_cards:
            return
        idx = self.pipeline_cards.index(card)
        if idx < len(self.pipeline_cards) - 1:
            self.cards_container.setUpdatesEnabled(False)
            try:
                self.pipeline_cards[idx], self.pipeline_cards[idx + 1] = (
                    self.pipeline_cards[idx + 1],
                    self.pipeline_cards[idx],
                )
                self.cards_layout.removeWidget(card)
                self.cards_layout.insertWidget(idx + 1, card)
                self.update_positions()
                self.log_emitted.emit(f"Agent #{idx + 1} nach unten verschoben.", "SYSTEM")
                self.order_changed.emit()
            finally:
                self.cards_container.setUpdatesEnabled(True)

    def update_positions(self) -> None:
        """
        Iterates over all PipelineCard widgets in the container from top to bottom (index 0 to n-1).
        Sets each card's position badge to its current row index: card.set_position_index(index + 1)
        (#1 for topmost card, #2 for second, etc.).
        Disables the move-up button on the topmost card (#1).
        Disables the move-down button on the bottommost card.
        """
        total = len(self.pipeline_cards)
        for index, card in enumerate(self.pipeline_cards):
            card.set_position_index(index + 1)
            card.set_move_buttons_enabled(can_move_up=(index > 0), can_move_down=(index < total - 1))

    def _update_card_orders(self) -> None:
        """Compatibility delegate for update_positions."""
        self.update_positions()

    def _update_pipeline_ui_state(self) -> None:
        count = len(self.pipeline_cards)
        self.lbl_team_count.setText(
            f"{count} Agenten aktiv" if self.lang == "de" else f"{count} agents active"
        )
        self.lbl_empty_team.setVisible(count == 0)

    def get_pipeline_configs(self) -> List[Dict[str, Any]]:
        """Extracts runtime configuration dictionary for every card in the pipeline."""
        configs: List[Dict[str, Any]] = []
        for card in self.pipeline_cards:
            cfg = card.get_config()
            cfg["model"] = cfg.get("model_name", "")
            cfg["allow_web_search"] = cfg.get("web", False)
            cfg["allow_file_write"] = cfg.get("write", False)
            cfg["enabled"] = True
            configs.append(cfg)
        return configs

    def get_cards(self) -> List[PipelineCard]:
        return list(self.pipeline_cards)

    def count(self) -> int:
        return len(self.pipeline_cards)

    def is_empty(self) -> bool:
        return len(self.pipeline_cards) == 0

    def reset_card_statuses(self, status: str = "Bereit", color_key: str = "gray") -> None:
        """Sets all card statuses uniformly."""
        for card in self.pipeline_cards:
            card.set_status(status, color_key=color_key)

    def clear_all_drawers(self) -> None:
        for card in self.pipeline_cards:
            card.clear_drawer()

    def clear_agent_states(self) -> None:
        """
        Clears thought and output drawers of all cards, closes opened drawers,
        and resets agent statuses to 'Bereit' (Ready).
        """
        for card in self.pipeline_cards:
            card.clear_drawer()
            card.toggle_drawer(visible=False)
            card.set_status("Bereit" if self.lang == "de" else "Ready", color_key="gray")

    def update_card_status(self, model_name: str, status: str, detail: str = "") -> None:
        """Updates card status badge based on model name matching."""
        for card in self.pipeline_cards:
            if card.model_name.lower() == model_name.lower() or model_name.lower() in card.model_name.lower():
                status_lower = status.lower()
                if "action" in status_lower or "running" in status_lower:
                    card.set_status("⚡ In Aktion...", color_key="yellow")
                elif "done" in status_lower or "finished" in status_lower:
                    card.set_status("✓ Fertig", color_key="green")
                elif "error" in status_lower or "failed" in status_lower:
                    card.set_status("Fehler", color_key="red")
                elif "think" in status_lower:
                    card.set_status("Denkt nach...", color_key="yellow")
                else:
                    card.set_status(status, color_key="gray")

    def append_card_thought(self, model_name: str, thought_chunk: str) -> None:
        """Appends thought chunks to matching card's ThoughtDrawer."""
        for card in self.pipeline_cards:
            if card.model_name.lower() == model_name.lower() or model_name.lower() in card.model_name.lower():
                card.append_stream_text(thought_chunk, is_thought=True)

    def set_task_completed(self, model_name: str, task_output: str) -> bool:
        """Fills drawer with task output if no streaming content was recorded."""
        clean_out = (task_output or "").strip()
        if not clean_out:
            return False
        for card in self.pipeline_cards:
            if card.model_name.lower() == model_name.lower() or model_name.lower() in card.model_name.lower():
                return card.set_task_output_if_empty(clean_out)
        return False

    def ensure_fallback_output(self, success: bool, fallback_text: str = "", error_msg: str = "") -> None:
        """Ensures every agent in the pipeline has visible output in its ThoughtDrawer."""
        for idx, card in enumerate(self.pipeline_cards, start=1):
            if not card.drawer.txt_output.toPlainText().strip():
                if success and fallback_text:
                    card.drawer.append_text(
                        f"### Arbeitsergebnis (#{idx} {card.model_name})\n{fallback_text}",
                        is_thought=False,
                    )
                else:
                    card.drawer.append_text(
                        f"Task beendet. Status: {'Erfolgreich' if success else f'Fehler: {error_msg}'}",
                        is_thought=False,
                    )

    def clear_agent_states(self) -> None:
        """Clears thought and output drawers of all cards, closes open drawers, and resets status to 'Bereit'."""
        for card in self.pipeline_cards:
            if hasattr(card, "drawer") and card.drawer:
                card.drawer.clear()
            card.toggle_drawer(visible=False)
            card.set_status("Bereit" if card.lang == "de" else "Ready", color_key="gray")

    def set_language(self, lang: str) -> None:
        """Retranslates header, legend, and child cards."""
        self.lang = lang
        self.lbl_title.setText("👥 " + t("pipeline_team_title", lang=self.lang))
        self.lbl_hdr_model.setText("Modell & VRAM" if self.lang == "de" else "Model & VRAM")
        self.lbl_hdr_role.setText("Rolle" if self.lang == "de" else "Role")
        self.lbl_hdr_thought.setText("Gedanken" if self.lang == "de" else "Thoughts")
        self.lbl_hdr_remove.setText("Löschen" if self.lang == "de" else "Remove")
        self._update_pipeline_ui_state()

        for card in self.pipeline_cards:
            card.set_language(self.lang)
