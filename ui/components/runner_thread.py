"""
Local Crew Cockpit - Crew Runner Background Thread & Signals
Qt bridge and background worker thread for non-blocking execution of CrewAI workflows.
"""

import logging
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from core.crew_runner import CrewRunner

logger = logging.getLogger(__name__)


class RunnerBridgeSignals(QObject):
    """Qt signal bridge forwarding asynchronous callbacks safely into the Qt event loop."""

    log_received = pyqtSignal(str, str)
    step_received = pyqtSignal(str, str, str, int)
    card_status_received = pyqtSignal(str, str, str)
    card_thought_received = pyqtSignal(str, str)
    task_completed = pyqtSignal(str, str)
    banner_received = pyqtSignal(str, str)
    result_received = pyqtSignal(str)
    tokens_updated = pyqtSignal(int, int)
    cancelled = pyqtSignal()
    finished = pyqtSignal(bool, str)


class CrewWorkerThread(QThread):
    """
    Dedicated QThread executing the CrewRunner orchestration in the background.
    Allows graceful shutdown via cancel() / quit() and safe fallback to terminate().
    """

    def __init__(
        self,
        runner: CrewRunner,
        model_configs: List[Dict[str, Any]],
        master_prompt: str,
        workspace_path: str,
        included_files: List[str],
        callbacks: Dict[str, Any],
        revision_feedback: Optional[str] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.runner = runner
        self.model_configs = model_configs
        self.master_prompt = master_prompt
        self.workspace_path = workspace_path
        self.included_files = included_files
        self.callbacks = callbacks
        self.revision_feedback = revision_feedback

    def run(self) -> None:
        try:
            self.runner.run(
                model_configs=self.model_configs,
                master_prompt=self.master_prompt,
                workspace_path=self.workspace_path,
                included_files=self.included_files,
                callbacks=self.callbacks,
                revision_feedback=self.revision_feedback,
            )
        except Exception as exc:
            logger.error("CrewWorkerThread unhandled execution error: %s", exc, exc_info=True)

    def cancel(self) -> None:
        if self.runner:
            self.runner.cancel()
