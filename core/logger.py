"""
Local Crew Cockpit - Centralized Logging System
Supports global --debug CLI flag and COCKPIT_DEBUG=1 environment variable.
Provides detailed payload logging for tools, Ollama HTTP events, and CrewAI steps.
"""

import logging
import os
import sys
import traceback
from typing import Any, Optional

DEBUG_ENV_VAR = "COCKPIT_DEBUG"
_is_debug_mode: bool = False


def is_debug() -> bool:
    """Returns True if the debug mode is globally active."""
    global _is_debug_mode
    return _is_debug_mode or os.environ.get(DEBUG_ENV_VAR, "").strip().lower() in ("1", "true", "yes")


def setup_logging(debug: Optional[bool] = None) -> bool:
    """
    Initializes root logging according to CLI flags and environment variables.
    If debug is True (via --debug or COCKPIT_DEBUG=1), logs at DEBUG level
    with detailed formatting and prints confirmation banner.
    Otherwise sets standard INFO level.
    """
    global _is_debug_mode
    if debug is None:
        debug = ("--debug" in sys.argv) or (os.environ.get(DEBUG_ENV_VAR, "").strip().lower() in ("1", "true", "yes"))

    _is_debug_mode = bool(debug)
    if _is_debug_mode:
        os.environ[DEBUG_ENV_VAR] = "1"
        log_level = logging.DEBUG
        log_format = "%(asctime)s [%(levelname)s] (%(name)s:%(lineno)d) %(message)s"
    else:
        log_level = logging.INFO
        log_format = "%(asctime)s [%(levelname)s] (%(name)s) %(message)s"

    # Configure root logger and stdout handler
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers to prevent duplicate output
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(logging.Formatter(log_format, datefmt="%H:%M:%S"))
    root_logger.addHandler(handler)

    if _is_debug_mode:
        print("[DEBUG-MODE AKTIV] Detaillierte Fehlerprotokollierung eingeschaltet.")
        sys.stdout.flush()

    return _is_debug_mode


def log_tool_payload(
    tool_name: str,
    args: Any,
    result: Optional[Any] = None,
    exc: Optional[Exception] = None,
) -> None:
    """Logs detailed tool payloads and tracebacks in debug mode."""
    if not is_debug():
        return
    logger = logging.getLogger("core.tools")
    if exc is not None:
        tb = traceback.format_exc()
        logger.debug("[TOOL-DEBUG] '%s' failed!\nArgs: %r\nException: %s\nTraceback:\n%s", tool_name, args, exc, tb)
    else:
        logger.debug("[TOOL-DEBUG] '%s' executed.\nArgs: %r\nResult: %r", tool_name, args, result)


def log_http_event(
    endpoint: str,
    method: str = "GET",
    payload: Optional[Any] = None,
    status_code: Optional[int] = None,
    response: Optional[Any] = None,
) -> None:
    """Logs detailed Ollama HTTP API events and payloads in debug mode."""
    if not is_debug():
        return
    logger = logging.getLogger("core.ollama_client")
    logger.debug(
        "[HTTP-DEBUG] %s %s | Status: %s\nPayload: %r\nResponse: %r",
        method, endpoint, status_code, payload, response
    )


def log_crew_step(
    agent_name: str,
    step_info: str,
    payload: Optional[Any] = None,
    exc: Optional[Exception] = None,
) -> None:
    """Logs detailed CrewAI step payloads and tracebacks in debug mode."""
    if not is_debug():
        return
    logger = logging.getLogger("core.crew_runner")
    if exc is not None:
        tb = traceback.format_exc()
        logger.debug("[CREW-DEBUG] [%s] %s failed!\nPayload: %r\nException: %s\nTraceback:\n%s", agent_name, step_info, payload, exc, tb)
    else:
        logger.debug("[CREW-DEBUG] [%s] %s | Payload: %r", agent_name, step_info, payload)
