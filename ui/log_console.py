"""
Local Crew Cockpit - Log Console & Human-in-the-Loop UI Component
Provides real-time agent activity logging with intelligent autoscroll,
diagnostic alert banner for timeouts/tool errors, clean final deliverable viewer,
and an interactive Human-in-the-Loop approval/revision control bar.
"""

import logging
from tkinter import filedialog
from typing import Any, Callable, Optional

import customtkinter as ctk

from core.locales import t

logger = logging.getLogger(__name__)


class LogConsole(ctk.CTkFrame):
    """
    Console combining live agent logging, warning banners, final result display,
    and Human-in-the-Loop iteration controls.
    """

    def __init__(
        self,
        parent: Any,
        lang: str = "de",
        on_approve: Optional[Callable[[], None]] = None,
        on_revise: Optional[Callable[[str], None]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, corner_radius=10, **kwargs)

        self.lang = lang
        self.on_approve = on_approve
        self.on_revise = on_revise

        # Autoscroll state
        self.autoscroll_active = True

        self._build_ui()

    def _build_ui(self) -> None:
        """Constructs split-view logging and HITL interface."""
        self.configure(fg_color=("gray95", "#161B22"), border_width=1, border_color=("gray85", "#2D3748"))

        # =============================================================
        # 1. Diagnose-Banner (Warnungen / Timeouts / Fehler)
        # =============================================================
        self.banner_frame = ctk.CTkFrame(self, corner_radius=6, height=36)
        self.banner_icon = ctk.CTkLabel(
            self.banner_frame,
            text="⚠️",
            font=ctk.CTkFont(size=14),
        )
        self.banner_icon.pack(side="left", padx=(10, 6))

        self.banner_text = ctk.CTkLabel(
            self.banner_frame,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        )
        self.banner_text.pack(side="left", fill="x", expand=True, padx=4)

        btn_dismiss_banner = ctk.CTkButton(
            self.banner_frame,
            text="✕",
            width=26,
            height=24,
            fg_color="transparent",
            hover_color=("gray60", "gray30"),
            command=self.hide_banner,
        )
        btn_dismiss_banner.pack(side="right", padx=6)
        # Initially hidden (pack_forget)

        # =============================================================
        # 2. Oberer Bereich: Live-Agentenprotokoll
        # =============================================================
        log_header = ctk.CTkFrame(self, fg_color="transparent")
        log_header.pack(fill="x", padx=12, pady=(10, 4))

        lbl_log_title = ctk.CTkLabel(
            log_header,
            text=f"📡 {t('tab_live_log', lang=self.lang)}",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            anchor="w",
        )
        lbl_log_title.pack(side="left")

        # Autoscroll Toggle Button
        self.btn_autoscroll = ctk.CTkButton(
            log_header,
            text="🔽 Autoscroll: AN",
            width=120,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color=("#16A34A", "#15803D"),
            hover_color=("#15803D", "#166534"),
            command=self._toggle_autoscroll,
        )
        self.btn_autoscroll.pack(side="right", padx=(6, 0))

        btn_clear = ctk.CTkButton(
            log_header,
            text="🗑️ Leeren",
            width=75,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color=("gray75", "#374151"),
            hover_color=("gray65", "#4B5563"),
            command=self.clear_log,
        )
        btn_clear.pack(side="right")

        # Live-Log Textbox
        self.txt_log = ctk.CTkTextbox(
            self,
            height=190,
            font=ctk.CTkFont(family="Consolas", size=11),
            corner_radius=8,
            wrap="word",
        )
        self.txt_log.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        # Mousewheel binding to detect upward scrolling by user
        self.txt_log.bind("<MouseWheel>", self._on_user_scroll)
        self.txt_log.bind("<Button-4>", self._on_user_scroll)

        # =============================================================
        # 3. Unterer Bereich: Sauberes Endergebnis (Deliverable)
        # =============================================================
        result_header = ctk.CTkFrame(self, fg_color="transparent")
        result_header.pack(fill="x", padx=12, pady=(4, 4))

        lbl_result_title = ctk.CTkLabel(
            result_header,
            text=f"📄 {t('tab_final_result', lang=self.lang)}",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            anchor="w",
        )
        lbl_result_title.pack(side="left")

        btn_copy_res = ctk.CTkButton(
            result_header,
            text="📋 Kopieren",
            width=85,
            height=24,
            font=ctk.CTkFont(size=11),
            command=self._copy_result_to_clipboard,
        )
        btn_copy_res.pack(side="right", padx=(6, 0))

        btn_save_res = ctk.CTkButton(
            result_header,
            text="💾 Speichern...",
            width=90,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color=("gray75", "#374151"),
            hover_color=("gray65", "#4B5563"),
            command=self._save_result_to_file,
        )
        btn_save_res.pack(side="right")

        self.txt_result = ctk.CTkTextbox(
            self,
            height=140,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            corner_radius=8,
            wrap="word",
        )
        self.txt_result.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        # =============================================================
        # 4. Human-in-the-Loop Steuerleiste
        # =============================================================
        hitl_frame = ctk.CTkFrame(self, fg_color=("gray90", "#1E2430"), corner_radius=8)
        hitl_frame.pack(fill="x", padx=12, pady=(0, 10))

        lbl_hitl = ctk.CTkLabel(
            hitl_frame,
            text="🧑‍💻 Human-in-the-Loop Feedback & Freigabe:",
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="w",
        )
        lbl_hitl.pack(fill="x", padx=10, pady=(6, 2))

        input_row = ctk.CTkFrame(hitl_frame, fg_color="transparent")
        input_row.pack(fill="x", padx=10, pady=(0, 8))

        self.entry_feedback = ctk.CTkEntry(
            input_row,
            placeholder_text=t("hitl_feedback_placeholder", lang=self.lang),
            height=30,
            font=ctk.CTkFont(size=11),
        )
        self.entry_feedback.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_feedback.bind("<Return>", lambda e: self._trigger_revise())

        # Button: [🔄 Nachbessern lassen]
        btn_revise = ctk.CTkButton(
            input_row,
            text="🔄 Nachbessern lassen",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=150,
            height=30,
            fg_color=("#D97706", "#B45309"),
            hover_color=("#B45309", "#92400E"),
            command=self._trigger_revise,
        )
        btn_revise.pack(side="left", padx=(0, 6))

        # Button: [✅ Abnehmen & Reset]
        btn_approve = ctk.CTkButton(
            input_row,
            text="✅ Abnehmen & Reset",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=150,
            height=30,
            fg_color=("#16A34A", "#15803D"),
            hover_color=("#15803D", "#166534"),
            command=self._trigger_approve,
        )
        btn_approve.pack(side="left")

    # =================================================================
    # Log-Methoden & Intelligenter Autoscroll
    # =================================================================

    def append_log(self, text: str, tag: str = "INFO") -> None:
        """
        Appends formatted log message to the protocol text widget.
        Honors intelligent autoscroll: only scrolls down if user hasn't scrolled up.
        """
        formatted = f"[{tag}] {text}\n"
        self.txt_log.insert("end", formatted)

        # Smart Autoscroll check
        if self.autoscroll_active:
            self.txt_log.see("end")

    def clear_log(self) -> None:
        """Clears the live log window."""
        self.txt_log.delete("1.0", "end")

    def _on_user_scroll(self, event: Any) -> None:
        """
        Detects upward manual scrolling and automatically pauses autoscroll
        so user can inspect earlier logs without being forced to bottom.
        """
        # MouseWheel delta > 0 means scrolled up on Windows
        delta = getattr(event, "delta", 0)
        num = getattr(event, "num", 0)

        if delta > 0 or num == 4:
            # User scrolled up: pause autoscroll
            if self.autoscroll_active:
                self.autoscroll_active = False
                self.btn_autoscroll.configure(
                    text="⏸️ Autoscroll: PAUSE",
                    fg_color=("gray60", "#4B5563"),
                    hover_color=("gray50", "#374151"),
                )

    def _toggle_autoscroll(self) -> None:
        """Toggles autoscroll state and instantly jumps to end if re-enabled."""
        self.autoscroll_active = not self.autoscroll_active
        if self.autoscroll_active:
            self.btn_autoscroll.configure(
                text="🔽 Autoscroll: AN",
                fg_color=("#16A34A", "#15803D"),
                hover_color=("#15803D", "#166534"),
            )
            self.txt_log.see("end")
        else:
            self.btn_autoscroll.configure(
                text="⏸️ Autoscroll: AUS",
                fg_color=("gray60", "#4B5563"),
                hover_color=("gray50", "#374151"),
            )

    # =================================================================
    # Diagnose-Banner
    # =================================================================

    def show_banner(self, message: str, banner_type: str = "warning") -> None:
        """
        Displays a persistent diagnostic alert strip at the top.
        banner_type can be 'error', 'warning', or 'info'.
        """
        type_key = banner_type.lower()
        if type_key == "error":
            bg_color = ("#FEE2E2", "#7F1D1D")
            text_color = ("#991B1B", "#FCA5A5")
            icon = "🚨"
        elif type_key == "info":
            bg_color = ("#DBEAFE", "#1E3A8A")
            text_color = ("#1E40AF", "#93C5FD")
            icon = "ℹ️"
        else:  # warning
            bg_color = ("#FEF3C7", "#78350F")
            text_color = ("#92400E", "#FDE68A")
            icon = "⚠️"

        self.banner_frame.configure(fg_color=bg_color)
        self.banner_icon.configure(text=icon)
        self.banner_text.configure(text=message, text_color=text_color)
        self.banner_frame.pack(fill="x", padx=12, pady=(8, 0), before=self.txt_log)

    def hide_banner(self) -> None:
        """Hides the diagnostic warning banner."""
        self.banner_frame.pack_forget()

    # =================================================================
    # Endergebnis (Deliverable)
    # =================================================================

    def set_result(self, content: str) -> None:
        """Sets and formats final output in the deliverable viewer."""
        self.txt_result.delete("1.0", "end")
        self.txt_result.insert("1.0", content)

    def get_result(self) -> str:
        """Retrieves raw content of the final output window."""
        return self.txt_result.get("1.0", "end-1c").strip()

    def _copy_result_to_clipboard(self) -> None:
        """Copies final deliverable to clipboard."""
        text = self.get_result()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()

    def _save_result_to_file(self) -> None:
        """Opens file dialog to save final deliverable as markdown or text file."""
        text = self.get_result()
        if not text:
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown Datei", "*.md"), ("Textdatei", "*.txt"), ("Alle Dateien", "*.*")],
            title="Endergebnis speichern",
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(text)
                self.show_banner(f"Endergebnis erfolgreich in '{file_path}' gespeichert.", banner_type="info")
            except Exception as exc:
                self.show_banner(f"Fehler beim Speichern der Datei: {exc}", banner_type="error")

    # =================================================================
    # Human-in-the-Loop Aktionen
    # =================================================================

    def get_feedback(self) -> str:
        """Returns the user-written feedback string from the entry field."""
        return self.entry_feedback.get().strip()

    def clear_feedback(self) -> None:
        """Clears the feedback entry field."""
        self.entry_feedback.delete(0, "end")

    def _trigger_approve(self) -> None:
        """Invoked when user clicks [✅ Abnehmen & Reset]."""
        if self.on_approve:
            self.on_approve()

    def _trigger_revise(self) -> None:
        """Invoked when user clicks [🔄 Nachbessern lassen]."""
        feedback = self.get_feedback()
        if self.on_revise:
            self.on_revise(feedback)
