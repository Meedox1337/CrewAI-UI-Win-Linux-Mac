"""
Local Crew Cockpit - Model Card UI Component
Represents a configured local LLM agent row with editable role ComboBox,
compact horizontal element order, isolated VRAM traffic light rating,
in-depth knowledge profile info dialog [ℹ️], model deletion with confirmation [🗑️],
intelligent update detection ('✓ Bereits aktuell' vs '✅ Neu aktualisiert'),
and collapsible Goal/Backstory/Delegation details drawer.
"""

import logging
import threading
import tkinter as tk
from typing import Any, Callable, Dict, Optional

import customtkinter as ctk

from core.locales import (
    get_canonical_role_key,
    get_role_presets,
    get_role_template,
    t,
    translate_role,
)
from core.model_knowledge import can_use_tools, get_model_profile
from core.ollama_client import delete_model, pull_model_stream
from core.system_monitor import get_memory_status

logger = logging.getLogger(__name__)


class ToolTip:
    """
    Lightweight, non-intrusive tooltip for Tk / CustomTkinter widgets.
    Uses native tk.Toplevel with overrideredirect so it does not steal focus
    or interfere with mouse clicks.
    """

    def __init__(self, widget: Any, text: str, delay_ms: int = 300) -> None:
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.after_id: Optional[str] = None
        self.tip_window: Optional[tk.Toplevel] = None

        targets = [widget]
        if hasattr(widget, "_canvas"):
            targets.append(widget._canvas)
        if hasattr(widget, "_text_label"):
            targets.append(widget._text_label)

        for target in targets:
            try:
                target.bind("<Enter>", self._on_enter, add="+")
                target.bind("<Leave>", self._on_leave, add="+")
                target.bind("<ButtonPress>", self._on_leave, add="+")
            except Exception:
                pass

    def _on_enter(self, event: Optional[Any] = None) -> None:
        self._cancel()
        try:
            self.after_id = self.widget.after(self.delay_ms, self._show)
        except Exception:
            pass

    def _on_leave(self, event: Optional[Any] = None) -> None:
        self._cancel()
        self._hide()

    def _cancel(self) -> None:
        if self.after_id:
            try:
                self.widget.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None

    def _show(self) -> None:
        if self.tip_window or not self.widget.winfo_exists():
            return
        try:
            x = self.widget.winfo_rootx() + 12
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
            self.tip_window = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            tw.attributes("-topmost", True)
            tw.configure(bg="#374151")

            lbl = tk.Label(
                tw,
                text=self.text,
                background="#1F2937",
                foreground="#F3F4F6",
                font=("Segoe UI", 9),
                padx=8,
                pady=4,
                relief="solid",
                borderwidth=1,
                highlightthickness=0,
            )
            lbl.pack()
        except Exception:
            self.tip_window = None

    def _hide(self) -> None:
        if self.tip_window:
            try:
                self.tip_window.destroy()
            except Exception:
                pass
            self.tip_window = None

    def set_text(self, text: str) -> None:
        self.text = text
        if self.tip_window:
            self._hide()


class ThoughtPopoutWindow(ctk.CTkToplevel):
    """
    Separate, movable pop-out window for an agent's live reasoning & <think> stream.
    Enables placing the stream on a secondary monitor while maintaining
    two-way synchronization with the cockpit.
    """

    def __init__(
        self,
        parent: Any,
        model_name: str,
        on_dock: Callable[[], None],
        on_clear: Callable[[], None],
        lang: str = "de",
    ) -> None:
        super().__init__(parent)

        self.model_name = model_name
        self.on_dock = on_dock
        self.on_clear = on_clear
        self.lang = lang

        self.title(t("thought_popout_title", lang=self.lang, model=model_name))
        self.geometry("640x440")
        self.minsize(420, 260)

        try:
            px = parent.winfo_rootx() + 40
            py = parent.winfo_rooty() + 40
            self.geometry(f"640x440+{px}+{py}")
        except Exception:
            self.geometry("640x440")

        self.protocol("WM_DELETE_WINDOW", self.on_dock)

        self._build_ui()

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, height=38, fg_color=("#1F2937", "#111827"))
        header.pack(fill="x", padx=10, pady=(8, 4))

        self.lbl_title = ctk.CTkLabel(
            header,
            text=t("thought_popout_header", lang=self.lang, model=self.model_name),
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=("#60A5FA", "#93C5FD"),
        )
        self.lbl_title.pack(side="left", padx=10)

        self.btn_dock = ctk.CTkButton(
            header,
            text=t("dock_btn", lang=self.lang),
            width=85,
            height=26,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#2563EB", "#1D4ED8"),
            hover_color=("#1D4ED8", "#1E40AF"),
            command=self.on_dock,
        )
        self.btn_dock.pack(side="right", padx=(6, 8))
        self.tip_dock = ToolTip(self.btn_dock, t("tooltip_dock", lang=self.lang))

        self.btn_clear = ctk.CTkButton(
            header,
            text=t("btn_clear", lang=self.lang),
            width=65,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color=("gray75", "#374151"),
            hover_color=("gray65", "#4B5563"),
            command=self.on_clear,
        )
        self.btn_clear.pack(side="right", padx=6)
        self.tip_clear = ToolTip(self.btn_clear, t("tooltip_clear_thoughts", lang=self.lang))

        self.txt_thought = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Consolas", size=11),
            corner_radius=8,
            fg_color=("#05080E", "#080C13"),
            text_color=("#E2E8F0", "#CBD5E1"),
            wrap="word",
        )
        self.txt_thought.pack(fill="both", expand=True, padx=10, pady=(4, 10))

    def set_language(self, lang: str) -> None:
        self.lang = lang
        self.title(t("thought_popout_title", lang=self.lang, model=self.model_name))
        self.lbl_title.configure(text=t("thought_popout_header", lang=self.lang, model=self.model_name))
        self.btn_dock.configure(text=t("dock_btn", lang=self.lang))
        self.btn_clear.configure(text=t("btn_clear", lang=self.lang))
        self.tip_dock.set_text(t("tooltip_dock", lang=self.lang))
        self.tip_clear.set_text(t("tooltip_clear_thoughts", lang=self.lang))

# Standard role presets delegation for backward compatibility
ROLE_PRESETS: Dict[str, Dict[str, str]] = {
    p: get_role_template(p, lang="de") for p in get_role_presets("de")
}


class ConfirmDeleteDialog(ctk.CTkToplevel):
    """
    Modal confirmation dialog for permanently deleting a model from Ollama storage.
    """

    def __init__(
        self,
        parent: Any,
        model_name: str,
        on_confirmed: Callable[[], None],
        lang: str = "de",
    ) -> None:
        super().__init__(parent)

        self.on_confirmed = on_confirmed
        self.lang = lang
        self.title("Modell löschen" if self.lang == "de" else "Delete Model")
        self.geometry("420x200")
        self.minsize(380, 180)
        self.resizable(False, False)

        # Center on parent window
        try:
            self.update_idletasks()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            w, h = 420, 200
            x = max(50, px + (pw - w) // 2)
            y = max(50, py + (ph - h) // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            self.geometry("420x200")

        self.transient(parent)
        self.grab_set()
        self.focus_set()

        self._build_ui(model_name)

    def _build_ui(self, model_name: str) -> None:
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=20)

        lbl_icon = ctk.CTkLabel(
            content,
            text="🗑️ " + ("Modell von Festplatte löschen?" if self.lang == "de" else "Delete model from disk?"),
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=("#DC2626", "#F87171"),
            anchor="w",
        )
        lbl_icon.pack(fill="x", pady=(0, 8))

        lbl_msg = ctk.CTkLabel(
            content,
            text=(
                f"Modell '{model_name}' wirklich von der Festplatte löschen?"
                if self.lang == "de"
                else f"Permanently delete model '{model_name}' from disk?"
            ),
            font=ctk.CTkFont(size=12, weight="bold"),
            wraplength=380,
            justify="left",
            anchor="w",
        )
        lbl_msg.pack(fill="x", pady=(0, 18))

        btn_row = ctk.CTkFrame(content, fg_color="transparent")
        btn_row.pack(fill="x")

        btn_cancel = ctk.CTkButton(
            btn_row,
            text="Abbrechen" if self.lang == "de" else "Cancel",
            font=ctk.CTkFont(size=12),
            width=100,
            height=30,
            fg_color=("gray70", "#374151"),
            hover_color=("gray60", "#4B5563"),
            command=self.destroy,
        )
        btn_cancel.pack(side="right", padx=(8, 0))

        btn_delete = ctk.CTkButton(
            btn_row,
            text="Ja, Löschen" if self.lang == "de" else "Yes, Delete",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=110,
            height=30,
            fg_color=("#DC2626", "#B91C1C"),
            hover_color=("#B91C1C", "#991B1B"),
            command=self._confirm,
        )
        btn_delete.pack(side="right")

    def _confirm(self) -> None:
        self.destroy()
        self.on_confirmed()


class ModelInfoDialog(ctk.CTkToplevel):
    """
    Modal Info Window displaying in-depth profile, strengths, and role
    recommendation for a specific model from model_knowledge.py.
    """

    def __init__(
        self,
        parent: Any,
        model_name: str,
        size_gb: float,
        vram_status_text: str,
        vram_color: tuple,
        lang: str = "de",
    ) -> None:
        super().__init__(parent)

        self.lang = lang
        self.profile = get_model_profile(model_name, lang=self.lang)

        self.title(f"Modell-Info: {model_name}")
        self.geometry("540x480")
        self.minsize(480, 420)

        try:
            self.update_idletasks()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            w, h = 540, 480
            x = max(50, px + (pw - w) // 2)
            y = max(50, py + (ph - h) // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            self.geometry("540x480")

        self.transient(parent)
        self.grab_set()
        self.focus_set()

        self._build_ui(model_name, size_gb, vram_status_text, vram_color)

    def _build_ui(
        self,
        model_name: str,
        size_gb: float,
        vram_status_text: str,
        vram_color: tuple,
    ) -> None:
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=16)

        lbl_title = ctk.CTkLabel(
            content_frame,
            text=f"🧠 {self.profile.get('title', model_name)}",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            anchor="w",
        )
        lbl_title.pack(fill="x", pady=(0, 4))

        lbl_sub = ctk.CTkLabel(
            content_frame,
            text=f"Ollama Tag: {model_name}  •  Größe: {size_gb:.1f} GB",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=("gray40", "gray60"),
            anchor="w",
        )
        lbl_sub.pack(fill="x", pady=(0, 10))

        badge_row = ctk.CTkFrame(content_frame, fg_color="transparent")
        badge_row.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            badge_row,
            text=self.profile.get("category", "General LLM"),
            font=ctk.CTkFont(size=11, weight="bold"),
            corner_radius=6,
            fg_color=("#DBEAFE", "#1E3A8A"),
            text_color=("#1E40AF", "#93C5FD"),
            padx=10,
            pady=3,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            badge_row,
            text=vram_status_text,
            font=ctk.CTkFont(size=11, weight="bold"),
            corner_radius=6,
            fg_color=("gray85", "#27272A"),
            text_color=vram_color,
            padx=10,
            pady=3,
        ).pack(side="left", padx=(0, 8))

        best_role = self.profile.get("best_role", "Senior Coder")
        ctk.CTkLabel(
            badge_row,
            text=f"Empfehlung: {best_role}",
            font=ctk.CTkFont(size=11, weight="bold"),
            corner_radius=6,
            fg_color=("#FEF3C7", "#78350F"),
            text_color=("#B45309", "#FDE68A"),
            padx=10,
            pady=3,
        ).pack(side="left")

        box_desc = ctk.CTkFrame(content_frame, corner_radius=8, fg_color=("gray90", "#1E2430"))
        box_desc.pack(fill="x", pady=(0, 10), padx=0)

        ctk.CTkLabel(
            box_desc,
            text="Profil & Einsatzbereich:",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(8, 4))

        ctk.CTkLabel(
            box_desc,
            text=self.profile.get("desc", ""),
            font=ctk.CTkFont(size=11),
            wraplength=480,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=12, pady=(0, 10))

        box_strengths = ctk.CTkFrame(content_frame, corner_radius=8, fg_color=("gray90", "#1E2430"))
        box_strengths.pack(fill="x", pady=(0, 10), padx=0)

        ctk.CTkLabel(
            box_strengths,
            text="Kern-Stärken & Fähigkeiten:",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(8, 4))

        for strength in self.profile.get("strengths", []):
            row = ctk.CTkFrame(box_strengths, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=1)

            ctk.CTkLabel(row, text="✓", font=ctk.CTkFont(size=12, weight="bold"), text_color=("#16A34A", "#4ADE80")).pack(side="left", padx=(0, 6))
            ctk.CTkLabel(row, text=strength, font=ctk.CTkFont(size=11), anchor="w").pack(side="left")

        ctx_note = self.profile.get("context_note", "")
        if ctx_note:
            ctk.CTkLabel(
                box_strengths,
                text=f"Kontext-Budget: {ctx_note}",
                font=ctk.CTkFont(size=11, slant="italic"),
                text_color=("gray40", "gray60"),
                anchor="w",
            ).pack(fill="x", padx=12, pady=(6, 8))
        else:
            ctk.CTkLabel(box_strengths, text="", height=4).pack()

        ctk.CTkButton(
            content_frame,
            text=t("close", lang=self.lang),
            font=ctk.CTkFont(size=12, weight="bold"),
            width=100,
            height=30,
            command=self.destroy,
        ).pack(side="right", pady=(4, 0))


class ModelCard(ctk.CTkFrame):
    """
    Card representing one detected local Ollama model configured as an agent.
    Row layout:
    [Checkbox] [Modellname + GB] [Ampel-Badge] [ℹ️] [Rollen-Dropdown (editierbar)] [🌐 Web] [🔄 Update] [🗑️] [⚙️] [Status]
    """

    def __init__(
        self,
        parent: Any,
        model_info: Dict[str, Any],
        default_role: Optional[str] = None,
        lang: str = "de",
        ollama_host: str = "http://localhost:11434",
        initially_active: bool = True,
        on_status_change: Optional[Callable[[str, str], None]] = None,
        on_delete: Optional[Callable[["ModelCard"], None]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, corner_radius=10, **kwargs)

        self.model_info = model_info
        self.model_name = model_info.get("name", "unknown")
        self.size_gb = float(model_info.get("size_gb", 0.0))
        self.lang = lang
        self.ollama_host = ollama_host
        self.on_status_change = on_status_change
        self.on_delete = on_delete

        # Knowledge-Profil abfragen und Standard-Rolle ermitteln
        self.profile = get_model_profile(self.model_name, lang=self.lang)
        fallback_role = "Senior-Entwickler" if self.lang == "de" else "Senior Coder"
        raw_role = default_role if default_role else self.profile.get("best_role", fallback_role)
        translated_initial = translate_role(raw_role, target_lang=self.lang)
        self.assigned_role = translated_initial if translated_initial else raw_role

        # Reactive State Variables
        self.tool_capable = can_use_tools(self.model_name, host=self.ollama_host)
        self.is_active_var = ctk.BooleanVar(value=initially_active)
        self.websearch_var = ctk.BooleanVar(value=False)
        self.filewrite_var = ctk.BooleanVar(value=False)
        self.delegation_var = ctk.BooleanVar(value=False)
        self.details_open = False
        self.thought_open = False
        self.thought_popout: Optional[ThoughtPopoutWindow] = None
        self.is_pulling = False
        self.is_deleting = False

        self._build_ui()
        self.update_vram_badge()

    def _build_ui(self) -> None:
        """Constructs the optimized, non-clipping single-row layout."""
        self.configure(fg_color=("gray92", "#1F242D"), border_width=1, border_color=("gray80", "#2D3748"))

        # =============================================================
        # 1. Hauptzeile: Streng geordnetes 1:1 Grid-Spaltensystem
        # =============================================================
        self.header_row = ctk.CTkFrame(self, fg_color="transparent")
        self.header_row.pack(fill="x", padx=8, pady=6)

        grid_cols = [
            (0, 190),   # [✓] Modell & Größe
            (1, 125),   # VRAM-Check
            (2, 36),    # Info
            (3, 155),   # Rolle
            (4, 66),    # Web
            (5, 72),    # Write
            (6, 82),    # Update
            (7, 36),    # Löschen
            (8, 90),    # Gedanken
            (9, 36),    # Setup
            (10, 110),  # Status (Mindestbreite >= 90 px)
        ]
        for col_idx, min_w in grid_cols:
            self.header_row.grid_columnconfigure(col_idx, minsize=min_w, weight=1 if col_idx == 10 else 0)

        # 1.1 Col 0: [Checkbox] + [Modellname + GB]
        col0_frame = ctk.CTkFrame(self.header_row, fg_color="transparent")
        col0_frame.grid(row=0, column=0, sticky="w", padx=2)

        self.chk_active = ctk.CTkCheckBox(
            col0_frame,
            text="",
            variable=self.is_active_var,
            width=22,
            command=self._on_toggle_active,
        )
        self.chk_active.pack(side="left", padx=(0, 4))
        self.tip_active = ToolTip(self.chk_active, t("tooltip_active", lang=self.lang))

        name_display = f"{self.model_name} ({self.size_gb:.1f} GB)"
        self.lbl_name = ctk.CTkLabel(
            col0_frame,
            text=name_display,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            anchor="w",
            width=155,
        )
        self.lbl_name.pack(side="left")

        # 1.2 Col 1: [Ampel-Badge] (Isolierte Bewertung für dieses Modell)
        self.lbl_vram_badge = ctk.CTkLabel(
            self.header_row,
            text="Prüfe...",
            font=ctk.CTkFont(size=10, weight="bold"),
            corner_radius=6,
            fg_color=("gray85", "#27272A"),
            text_color=("gray30", "gray70"),
            padx=7,
            pady=2,
            width=115,
        )
        self.lbl_vram_badge.grid(row=0, column=1, sticky="w", padx=2)

        # 1.3 Col 2: [ℹ️] Info-Button für Profil, Stärken & Rollenempfehlung
        self.btn_info = ctk.CTkButton(
            self.header_row,
            text="ℹ️",
            width=28,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color=("gray78", "#374151"),
            hover_color=("gray68", "#4B5563"),
            command=self.open_info_dialog,
        )
        self.btn_info.grid(row=0, column=2, sticky="w", padx=2)
        self.tip_info = ToolTip(self.btn_info, t("tooltip_info", lang=self.lang))

        # 1.4 Col 3: [Rollen-Dropdown (editierbar für Freitext / Presets)]
        role_options = get_role_presets(self.lang)
        self.role_combobox = ctk.CTkComboBox(
            self.header_row,
            values=role_options,
            command=self._on_role_selected,
            state="normal",
            width=145,
            height=28,
            font=ctk.CTkFont(size=11),
        )
        self.role_combobox.set(self.assigned_role)
        self.role_combobox.grid(row=0, column=3, sticky="w", padx=2)
        self.tip_role = ToolTip(self.role_combobox, t("tooltip_role", lang=self.lang))

        if hasattr(self.role_combobox, "_entry"):
            self.role_combobox._entry.bind("<KeyRelease>", self._on_role_typed)

        # 1.5 Col 4: [🌐 Web] Checkbox
        self.chk_web = ctk.CTkCheckBox(
            self.header_row,
            text="🌐 Web",
            variable=self.websearch_var,
            font=ctk.CTkFont(size=11),
            width=62,
        )
        if not self.tool_capable:
            self.websearch_var.set(False)
            self.chk_web.configure(state="disabled", text_color=("gray50", "gray50"))
            self.tip_web = ToolTip(self.chk_web, t("tooltip_tools_disabled", lang=self.lang))
        else:
            self.chk_web.configure(state="normal")
            self.tip_web = ToolTip(self.chk_web, t("tooltip_web", lang=self.lang))
        self.chk_web.grid(row=0, column=4, sticky="w", padx=2)

        # 1.6 Col 5: [✏️ Write] Checkbox
        self.chk_write = ctk.CTkCheckBox(
            self.header_row,
            text="✏️ Write",
            variable=self.filewrite_var,
            font=ctk.CTkFont(size=11),
            width=68,
        )
        if not self.tool_capable:
            self.filewrite_var.set(False)
            self.chk_write.configure(state="disabled", text_color=("gray50", "gray50"))
            self.tip_write = ToolTip(self.chk_write, t("tooltip_tools_disabled", lang=self.lang))
        else:
            self.chk_write.configure(state="normal")
            self.tip_write = ToolTip(self.chk_write, t("tooltip_write", lang=self.lang))
        self.chk_write.grid(row=0, column=5, sticky="w", padx=2)

        # 1.7 Col 6: [🔄 Update] Button (Streaming Pull Download)
        self.btn_update = ctk.CTkButton(
            self.header_row,
            text="🔄 " + t("header_update", lang=self.lang),
            font=ctk.CTkFont(size=11, weight="bold"),
            width=76,
            height=26,
            fg_color=("#2563EB", "#1D4ED8"),
            hover_color=("#1D4ED8", "#1E40AF"),
            command=self._trigger_pull_model,
        )
        self.btn_update.grid(row=0, column=6, sticky="w", padx=2)
        self.tip_update = ToolTip(self.btn_update, t("tooltip_update", lang=self.lang))

        # 1.8 Col 7: [🗑️] Modell löschen Button
        self.btn_delete = ctk.CTkButton(
            self.header_row,
            text="🗑️",
            width=28,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color=("gray75", "#374151"),
            hover_color=("#DC2626", "#991B1B"),
            command=self._confirm_delete,
        )
        self.btn_delete.grid(row=0, column=7, sticky="w", padx=2)
        self.tip_delete = ToolTip(self.btn_delete, t("tooltip_delete", lang=self.lang))

        # 1.9 Col 8: [🧠 Gedanken] Toggle Button für Live Reasoning & Gedanken
        self.btn_thought = ctk.CTkButton(
            self.header_row,
            text="🧠 " + t("header_thoughts", lang=self.lang),
            font=ctk.CTkFont(size=11),
            width=84,
            height=26,
            fg_color=("gray75", "#374151"),
            hover_color=("gray65", "#4B5563"),
            command=self.toggle_thought,
        )
        self.btn_thought.grid(row=0, column=8, sticky="w", padx=2)
        self.tip_thought = ToolTip(self.btn_thought, t("tooltip_thoughts", lang=self.lang))

        # 1.10 Col 9: [⚙️] Details-Drawer-Toggle Button
        self.btn_details = ctk.CTkButton(
            self.header_row,
            text="⚙️",
            font=ctk.CTkFont(size=12),
            width=28,
            height=26,
            fg_color=("gray75", "#374151"),
            hover_color=("gray65", "#4B5563"),
            command=self.toggle_details,
        )
        self.btn_details.grid(row=0, column=9, sticky="w", padx=2)
        self.tip_details = ToolTip(self.btn_details, t("tooltip_setup", lang=self.lang))

        # 1.11 Col 10: [Status] Ganz rechts verankert (feste Mindestbreite >= 90 px)
        self.lbl_status = ctk.CTkLabel(
            self.header_row,
            text="⚪ " + t("model_status_ready", lang=self.lang),
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("gray40", "gray70"),
            anchor="e",
            width=100,
        )
        self.lbl_status.grid(row=0, column=10, sticky="e", padx=(2, 6))

        # =============================================================
        # 2. Ausklappbarer Details-Drawer (Goal, Backstory & Delegation)
        # =============================================================
        self.details_frame = ctk.CTkFrame(self, fg_color=("gray88", "#181D24"), corner_radius=8)

        # Delegation-Option im Details-Drawer
        self.chk_delegation = ctk.CTkCheckBox(
            self.details_frame,
            text=(
                "Delegieren erlauben (Agent darf Aufgaben an andere Crew-Mitglieder übergeben)"
                if self.lang == "de"
                else "Allow delegation (agent may assign tasks to other crew members)"
            ),
            variable=self.delegation_var,
            font=ctk.CTkFont(size=11),
        )
        self.chk_delegation.pack(fill="x", padx=12, pady=(8, 4))

        # Goal (Ziel)
        self.lbl_goal = ctk.CTkLabel(
            self.details_frame,
            text="🎯 " + ("Agent Goal (Aufgabenstellung / Ziel):" if self.lang == "de" else "Agent Goal (Mission & Objectives):"),
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="w",
        )
        self.lbl_goal.pack(fill="x", padx=12, pady=(4, 2))

        self.txt_goal = ctk.CTkEntry(
            self.details_frame,
            height=28,
            font=ctk.CTkFont(size=11),
        )
        self.txt_goal.pack(fill="x", padx=12, pady=(0, 6))

        # Backstory (Rolle & Verhaltensregeln)
        self.lbl_backstory = ctk.CTkLabel(
            self.details_frame,
            text="📜 " + ("Agent Backstory (Rolle, Tonfall & Richtlinien):" if self.lang == "de" else "Agent Backstory (Role, Tone & Guidelines):"),
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="w",
        )
        self.lbl_backstory.pack(fill="x", padx=12, pady=(4, 2))

        self.txt_backstory = ctk.CTkTextbox(
            self.details_frame,
            height=54,
            font=ctk.CTkFont(size=11),
            corner_radius=6,
        )
        self.txt_backstory.pack(fill="x", padx=12, pady=(0, 10))

        # =============================================================
        # 3. Ausklappbarer Gedankengang-Stream (Live Reasoning & <think>)
        # =============================================================
        self.thought_frame = ctk.CTkFrame(self, fg_color=("#0F141C", "#0D1117"), corner_radius=8)

        thought_header = ctk.CTkFrame(self.thought_frame, fg_color="transparent")
        thought_header.pack(fill="x", padx=10, pady=(6, 2))

        self.lbl_thought_title = ctk.CTkLabel(
            thought_header,
            text=t("thought_title", lang=self.lang),
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=("#60A5FA", "#93C5FD"),
            anchor="w",
        )
        self.lbl_thought_title.pack(side="left")

        self.btn_clear_t = ctk.CTkButton(
            thought_header,
            text=t("btn_clear", lang=self.lang),
            width=50,
            height=20,
            font=ctk.CTkFont(size=10),
            fg_color=("gray75", "#2D3748"),
            hover_color=("gray65", "#374151"),
            command=self.clear_thought,
        )
        self.btn_clear_t.pack(side="right")
        self.tip_clear_t = ToolTip(self.btn_clear_t, t("tooltip_clear_thoughts", lang=self.lang))

        self.btn_undock = ctk.CTkButton(
            thought_header,
            text=t("undock_btn", lang=self.lang),
            width=75,
            height=20,
            font=ctk.CTkFont(size=10),
            fg_color=("gray75", "#2D3748"),
            hover_color=("gray65", "#374151"),
            command=self.undock_thought,
        )
        self.btn_undock.pack(side="right", padx=(0, 6))
        self.tip_undock = ToolTip(self.btn_undock, t("tooltip_undock", lang=self.lang))

        self.txt_thought = ctk.CTkTextbox(
            self.thought_frame,
            height=85,
            font=ctk.CTkFont(family="Consolas", size=10),
            corner_radius=6,
            fg_color=("#05080E", "#080C13"),
            text_color=("#E2E8F0", "#CBD5E1"),
            wrap="word",
        )
        self.txt_thought.pack(fill="both", expand=True, padx=10, pady=(2, 8))

        self._apply_role_template(self.assigned_role)

    def _apply_role_template(self, role: str) -> None:
        role_clean = role.strip()
        template = get_role_template(role_clean, lang=self.lang)
        goal_text = template.get("goal", "")
        backstory_text = template.get("backstory", "")

        self.txt_goal.delete(0, "end")
        self.txt_goal.insert(0, goal_text)

        self.txt_backstory.delete("1.0", "end")
        self.txt_backstory.insert("1.0", backstory_text)

    def _on_role_selected(self, choice: str) -> None:
        self.assigned_role = choice.strip()
        self._apply_role_template(self.assigned_role)

    def _on_role_typed(self, event: Any) -> None:
        current_text = self.role_combobox.get().strip()
        if current_text:
            self.assigned_role = current_text
            self._apply_role_template(current_text)

    def update_vram_badge(self, free_vram: Optional[float] = None) -> None:
        if free_vram is None:
            mem = get_memory_status()
            free_vram = float(mem.get("free_gb", 0.0))

        buffer = free_vram - self.size_gb

        if buffer >= 3.0:
            badge_text = "🟢 Fit (viel Kontext)" if self.lang == "de" else "🟢 Fit (high context)"
            badge_color = ("#15803D", "#4ADE80")
            badge_bg = ("#DCFCE7", "#064E3B")
        elif self.size_gb <= free_vram:
            badge_text = "🟡 Fit (knapper Cache)" if self.lang == "de" else "🟡 Fit (tight cache)"
            badge_color = ("#B45309", "#FBBF24")
            badge_bg = ("#FEF3C7", "#78350F")
        else:
            badge_text = "🔴 OOM / Zu groß" if self.lang == "de" else "🔴 OOM / Too large"
            badge_color = ("#B91C1C", "#F87171")
            badge_bg = ("#FEE2E2", "#7F1D1D")

        self.lbl_vram_badge.configure(
            text=badge_text,
            text_color=badge_color,
            fg_color=badge_bg,
        )
        self.vram_status_text = badge_text
        self.vram_color = badge_color

    def open_info_dialog(self) -> None:
        ModelInfoDialog(
            parent=self.winfo_toplevel(),
            model_name=self.model_name,
            size_gb=self.size_gb,
            vram_status_text=getattr(self, "vram_status_text", "🟢 Fit"),
            vram_color=getattr(self, "vram_color", ("#15803D", "#4ADE80")),
            lang=self.lang,
        )

    def _confirm_delete(self) -> None:
        """Opens confirmation dialog to delete model."""
        ConfirmDeleteDialog(
            parent=self.winfo_toplevel(),
            model_name=self.model_name,
            on_confirmed=self._execute_delete,
            lang=self.lang,
        )

    def _execute_delete(self) -> None:
        """Deletes model via Ollama DELETE API in background thread."""
        if self.is_deleting:
            return

        self.is_deleting = True
        self.btn_delete.configure(state="disabled")
        self.set_status("action", "Lösche..." if self.lang == "de" else "Deleting...")

        def worker() -> None:
            success = delete_model(self.model_name, host=self.ollama_host)
            self.is_deleting = False
            if success:
                logger.info("Successfully deleted model %s", self.model_name)
                def remove_from_ui():
                    if self.on_delete:
                        self.on_delete(self)
                    self.destroy()
                self.after(0, remove_from_ui)
            else:
                logger.error("Failed to delete model %s", self.model_name)
                self.after(0, lambda: (
                    self.btn_delete.configure(state="normal"),
                    self.set_status("error", "Löschen fehlgeschlagen" if self.lang == "de" else "Delete failed")
                ))

        threading.Thread(target=worker, daemon=True).start()

    def toggle_details(self) -> None:
        if self.details_open:
            self.details_frame.pack_forget()
            self.btn_details.configure(text="⚙️")
            self.details_open = False
        else:
            self.details_frame.pack(fill="x", padx=8, pady=(0, 8))
            self.btn_details.configure(text="▲")
            self.details_open = True

    def toggle_thought(self) -> None:
        """Toggles visibility of the thinking stream drawer."""
        if self.thought_open:
            self.thought_frame.pack_forget()
            self.btn_thought.configure(fg_color=("gray75", "#374151"))
            self.thought_open = False
        else:
            self.thought_frame.pack(fill="x", padx=8, pady=(0, 6))
            self.btn_thought.configure(fg_color=("#1E3A8A", "#2563EB"))
            self.thought_open = True

    def undock_thought(self) -> None:
        """Opens the thought stream in a separate pop-out window."""
        if self.thought_popout and self.thought_popout.winfo_exists():
            self.thought_popout.lift()
            self.thought_popout.focus()
            return

        self.thought_popout = ThoughtPopoutWindow(
            parent=self.winfo_toplevel(),
            model_name=self.model_name,
            on_dock=self.dock_thought,
            on_clear=self.clear_thought,
            lang=self.lang,
        )

        current_text = self.txt_thought.get("1.0", "end-1c")
        if current_text:
            self.thought_popout.txt_thought.insert("end", current_text)
            self.thought_popout.txt_thought.see("end")

        self.btn_undock.configure(text="↗ " + ("Geöffnet" if self.lang == "de" else "Opened"), state="disabled")

    def dock_thought(self) -> None:
        """Docks the pop-out window back into the card."""
        if self.thought_popout and self.thought_popout.winfo_exists():
            popout_text = self.thought_popout.txt_thought.get("1.0", "end-1c")
            self.txt_thought.delete("1.0", "end")
            if popout_text:
                self.txt_thought.insert("end", popout_text)
                self.txt_thought.see("end")
            try:
                self.thought_popout.destroy()
            except Exception:
                pass
        self.thought_popout = None
        self.btn_undock.configure(text=t("undock_btn", lang=self.lang), state="normal")

        if not self.thought_open:
            self.toggle_thought()

    def append_thought(self, thought_chunk: str) -> None:
        """
        Appends live thought chunk in real-time and scrolls to the end.
        Automatically syncs with pop-out window if undocked, or reveals drawer.
        """
        formatted = thought_chunk if thought_chunk.endswith("\n") else thought_chunk + "\n"

        self.txt_thought.insert("end", formatted)
        self.txt_thought.see("end")

        if self.thought_popout and self.thought_popout.winfo_exists():
            self.thought_popout.txt_thought.insert("end", formatted)
            self.thought_popout.txt_thought.see("end")
        else:
            if not getattr(self, "thought_open", False):
                self.thought_frame.pack(fill="x", padx=8, pady=(0, 6))
                self.btn_thought.configure(fg_color=("#1E3A8A", "#2563EB"))
                self.thought_open = True

    def clear_thought(self) -> None:
        """Empties the thought reasoning stream in both card and popout."""
        self.txt_thought.delete("1.0", "end")
        if self.thought_popout and self.thought_popout.winfo_exists():
            self.thought_popout.txt_thought.delete("1.0", "end")

    def destroy(self) -> None:
        if getattr(self, "thought_popout", None) and self.thought_popout.winfo_exists():
            try:
                self.thought_popout.destroy()
            except Exception:
                pass
            self.thought_popout = None
        super().destroy()

    def set_language(self, lang: str) -> None:
        """Dynamically updates all labels, buttons, and tooltips to the target language."""
        self.lang = lang
        self.tip_active.set_text(t("tooltip_active", lang=self.lang))
        self.tip_info.set_text(t("tooltip_info", lang=self.lang))
        self.tip_role.set_text(t("tooltip_role", lang=self.lang))
        if not getattr(self, "tool_capable", True):
            self.tip_web.set_text(t("tooltip_tools_disabled", lang=self.lang))
            self.tip_write.set_text(t("tooltip_tools_disabled", lang=self.lang))
        else:
            self.tip_web.set_text(t("tooltip_web", lang=self.lang))
            self.tip_write.set_text(t("tooltip_write", lang=self.lang))
        self.tip_update.set_text(t("tooltip_update", lang=self.lang))
        self.tip_delete.set_text(t("tooltip_delete", lang=self.lang))
        self.tip_thought.set_text(t("tooltip_thoughts", lang=self.lang))
        self.tip_details.set_text(t("tooltip_setup", lang=self.lang))
        self.tip_undock.set_text(t("tooltip_undock", lang=self.lang))
        self.tip_clear_t.set_text(t("tooltip_clear_thoughts", lang=self.lang))

        self.btn_thought.configure(text="🧠 " + t("header_thoughts", lang=self.lang))
        if not getattr(self, "is_pulling", False):
            self.btn_update.configure(text="🔄 " + t("header_update", lang=self.lang))
        self.lbl_thought_title.configure(text=t("thought_title", lang=self.lang))
        self.btn_clear_t.configure(text=t("btn_clear", lang=self.lang))
        if self.thought_popout and self.thought_popout.winfo_exists():
            self.btn_undock.configure(text="↗ " + ("Geöffnet" if self.lang == "de" else "Opened"))
            self.thought_popout.set_language(self.lang)
        else:
            self.btn_undock.configure(text=t("undock_btn", lang=self.lang))

        self.chk_delegation.configure(
            text=(
                "Delegieren erlauben (Agent darf Aufgaben an andere Crew-Mitglieder übergeben)"
                if self.lang == "de"
                else "Allow delegation (agent may assign tasks to other crew members)"
            )
        )
        self.lbl_goal.configure(
            text="🎯 " + ("Agent Goal (Aufgabenstellung / Ziel):" if self.lang == "de" else "Agent Goal (Mission & Objectives):")
        )
        self.lbl_backstory.configure(
            text="📜 " + ("Agent Backstory (Rolle, Tonfall & Richtlinien):" if self.lang == "de" else "Agent Backstory (Role, Tone & Guidelines):")
        )

        # Rollen-Dropdown aktualisieren und Standard-Rollen übersetzen
        new_presets = get_role_presets(self.lang)
        self.role_combobox.configure(values=new_presets)

        current_role = self.role_combobox.get().strip()
        translated_role = translate_role(current_role, target_lang=self.lang)
        if translated_role is not None:
            # Vordefiniertes Preset: Übersetze den Text in die Zielsprache
            self.assigned_role = translated_role
            self.role_combobox.set(translated_role)
            self._apply_role_template(translated_role)
        else:
            # Eigene Freitext-Eingabe (z.B. 'Biologe'): Bleibt unangetastet, Goal/Backstory sprachlich anpassen
            self.assigned_role = current_role
            self._apply_role_template(current_role)

        self.update_vram_badge()
        self.set_status(getattr(self, "current_status_code", "ready"), getattr(self, "current_status_detail", ""))

    def _on_toggle_active(self) -> None:
        active = self.is_active_var.get()
        opacity_color = ("black", "white") if active else ("gray50", "gray50")
        self.lbl_name.configure(text_color=opacity_color)
        if not active:
            self.set_status("disabled", "Deaktiviert" if self.lang == "de" else "Deactivated")
        else:
            self.set_status("ready", "")

    def set_status(self, status: str, detail: str = "") -> None:
        self.current_status_code = status
        self.current_status_detail = detail

        status_key = status.lower()
        if status_key == "ready":
            text_disp = f"✓ {detail}" if detail else "⚪ " + t("model_status_ready", lang=self.lang)
            color_disp = ("#16A34A", "#4ADE80") if detail else ("gray40", "gray70")
            self.lbl_status.configure(text=text_disp, text_color=color_disp)
        elif status_key in ("action", "thinking"):
            label_text = f"⚙️ {detail or t('model_status_thinking', lang=self.lang)}"
            self.lbl_status.configure(text=label_text, text_color=("#2563EB", "#60A5FA"))
        elif status_key == "done":
            label_text = f"✅ {detail or t('model_status_done', lang=self.lang)}"
            self.lbl_status.configure(text=label_text, text_color=("#16A34A", "#4ADE80"))
        elif status_key == "error":
            label_text = f"⚠️ {detail or t('model_status_error', lang=self.lang)}"
            self.lbl_status.configure(text=label_text, text_color=("#DC2626", "#F87171"))
        elif status_key == "disabled":
            self.lbl_status.configure(text="⏸️ " + ("Inaktiv" if self.lang == "de" else "Inactive"), text_color="gray50")
        else:
            self.lbl_status.configure(text=f"• {status}", text_color=("gray40", "gray70"))

        if self.on_status_change:
            self.on_status_change(self.model_name, status)

    def _trigger_pull_model(self) -> None:
        """Triggers live streaming pull and renders download percentage directly on button and status."""
        if self.is_pulling:
            return

        self.is_pulling = True
        self.btn_update.configure(state="disabled")
        self.set_status("action", "Lade..." if self.lang == "de" else "Pulling...")

        def progress_callback(status: str, completed: int, total: int) -> None:
            if total > 0:
                pct = int((completed / total) * 100)
                btn_label = f"{pct}%"
                detail_text = f"{pct}%"
            else:
                btn_label = "Pull..."
                detail_text = status[:12] if status else ("Lade..." if self.lang == "de" else "Pulling...")

            self.after(0, lambda: (
                self.btn_update.configure(text=btn_label),
                self.set_status("action", detail_text)
            ))

        def worker() -> None:
            result = pull_model_stream(
                model_name=self.model_name,
                callback=progress_callback,
                host=self.ollama_host,
            )
            self.is_pulling = False
            if result == "up_to_date":
                msg = "Bereits aktuell" if self.lang == "de" else "Up to date"
                self.after(0, lambda: (
                    self.btn_update.configure(state="normal", text=f"✓ {msg}"),
                    self.set_status("ready", msg)
                ))
                self.after(5000, lambda: self.btn_update.configure(text="🔄 " + t("header_update", lang=self.lang)))
            elif result == "updated":
                msg = "Neu aktualisiert" if self.lang == "de" else "Updated"
                self.after(0, lambda: (
                    self.btn_update.configure(state="normal", text=f"✅ {msg}"),
                    self.set_status("done", msg)
                ))
                self.after(5000, lambda: self.btn_update.configure(text="🔄 " + t("header_update", lang=self.lang)))
            else:
                msg = "Fehler" if self.lang == "de" else "Error"
                self.after(0, lambda: (
                    self.btn_update.configure(state="normal", text="🔄 " + t("header_update", lang=self.lang)),
                    self.set_status("error", msg)
                ))

        threading.Thread(target=worker, daemon=True).start()

    def is_enabled(self) -> bool:
        return self.is_active_var.get()

    def get_config(self) -> Dict[str, Any]:
        role_val = self.role_combobox.get().strip()
        web_allowed = bool(self.websearch_var.get() and getattr(self, "tool_capable", True))
        write_allowed = bool(self.filewrite_var.get() and getattr(self, "tool_capable", True))
        return {
            "model_name": self.model_name,
            "size_gb": self.size_gb,
            "role": role_val,
            "canonical_role": get_canonical_role_key(role_val),
            "goal": self.txt_goal.get().strip(),
            "backstory": self.txt_backstory.get("1.0", "end-1c").strip(),
            "websearch": web_allowed,
            "allow_web_search": web_allowed,
            "allow_file_write": write_allowed,
            "allow_delegation": self.delegation_var.get(),
            "enabled": self.is_active_var.get(),
        }
