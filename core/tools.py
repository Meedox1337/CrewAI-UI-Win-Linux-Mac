"""
Local Crew Cockpit - Agent Tools Module
Provides local code grep search, safe file read/write/patch utilities,
and DuckDuckGo web search integration for CrewAI agent workflows.
"""

import os
import re
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Resilient CrewAI tool decorator & BaseTool import
try:
    from crewai.tools import tool, BaseTool
    try:
        from crewai.tools.base_tool import Tool
        def _tool_call(self: Any, *args: Any, **kwargs: Any) -> Any:
            fn = getattr(self, "func", None)
            if fn and callable(fn):
                return fn(*args, **kwargs)
            return self.run(*args, **kwargs)
        Tool.__call__ = _tool_call  # type: ignore
    except Exception:
        pass
except (ImportError, Exception):
    BaseTool = object  # type: ignore
    def tool(name_or_func: Any = None, *args: Any, **kwargs: Any) -> Any:
        if callable(name_or_func):
            return name_or_func
        def decorator(func: Any) -> Any:
            return func
        return decorator

# Resilient DuckDuckGo Search import (supports duckduckgo_search and renamed ddgs)
try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    try:
        from ddgs import DDGS  # type: ignore
        DDGS_AVAILABLE = True
    except ImportError:
        DDGS = None  # type: ignore
        DDGS_AVAILABLE = False

logger = logging.getLogger(__name__)

from core.logger import is_debug, log_tool_payload

# Standard directory and file exclusions for code search
DEFAULT_EXCLUDED_DIRS = {
    ".git", ".svn", ".hg", "__pycache__", "venv", ".venv", "env",
    "node_modules", "build", "dist", ".idea", ".vscode", ".next",
    ".cache", "target", "out", "bin", "obj"
}

DEFAULT_EXCLUDED_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".dylib", ".exe", ".bin",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".pdf",
    ".zip", ".tar", ".gz", ".7z", ".rar", ".parquet", ".db", ".sqlite",
    ".mp3", ".mp4", ".mov", ".avi", ".wav"
}


# =====================================================================
# 1. Lokales Code-Grep-Werkzeug
# =====================================================================

@tool("file_grep_tool")
def file_grep_tool(
    pattern: str,
    directory_path: str = ".",
    case_sensitive: bool = False,
    max_matches: int = 50,
) -> str:
    """
    Durchsucht rekursiv ein Projektverzeichnis nach einem String oder regulären Ausdruck.
    Ignoriert temporäre Ordner (.git, venv, build etc.) und Binärdateien.

    Args:
        pattern: Der gesuchte Text oder Regex (z.B. "Colors.purple" oder "def [a-zA-Z_]+").
        directory_path: Basisverzeichnis für die Suche (Standard: aktuelles Verzeichnis).
        case_sensitive: Ob Groß-/Kleinschreibung beachtet werden soll (Standard: False).
        max_matches: Maximale Anzahl von Treffern (Standard: 50).

    Returns:
        Formatierte Liste von Treffern mit Dateipfad, Zeilennummer und Zeileninhalt.
    """
    if is_debug():
        log_tool_payload("file_grep_tool", {"pattern": pattern, "directory": directory_path})

    base_path = Path(directory_path).resolve()
    if not base_path.exists() or not base_path.is_dir():
        res = f"Fehler: Das Verzeichnis '{directory_path}' existiert nicht oder ist kein Ordner."
        if is_debug():
            log_tool_payload("file_grep_tool", {"pattern": pattern}, result=res)
        return res

    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        regex = re.compile(pattern, flags)
    except re.error as err:
        # Fallback to literal search if pattern contains unescaped special characters
        escaped_pattern = re.escape(pattern)
        regex = re.compile(escaped_pattern, flags)

    matches: List[str] = []
    total_matches = 0

    for root, dirs, files in os.walk(base_path):
        # Prune excluded directories in-place to avoid deep recursions
        dirs[:] = [d for d in dirs if d not in DEFAULT_EXCLUDED_DIRS and not d.startswith(".")]

        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext in DEFAULT_EXCLUDED_EXTENSIONS:
                continue

            file_path = Path(root) / filename
            rel_path = file_path.relative_to(base_path)

            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    for line_num, line in enumerate(f, start=1):
                        if regex.search(line):
                            clean_line = line.strip()
                            # Truncate overly long lines for agent readability
                            if len(clean_line) > 160:
                                clean_line = clean_line[:160] + "..."
                            matches.append(f"{rel_path}:{line_num}: {clean_line}")
                            total_matches += 1

                            if total_matches >= max_matches:
                                matches.append(f"\n[Hinweis: Suche bei {max_matches} Treffern limitiert.]")
                                return "\n".join(matches)
            except Exception as e:
                logger.debug("Could not read file %s: %s", file_path, e)
                continue

    if not matches:
        return f"Keine Treffer für das Muster '{pattern}' im Verzeichnis '{base_path.name}' gefunden."

    header = f"Grep-Treffer für '{pattern}' ({total_matches} gefunden):\n" + ("-" * 60)
    return header + "\n" + "\n".join(matches)


# =====================================================================
# 2. Lokale Datei-Lese- & Schreib-Werkzeuge für punktuelle Patches
# =====================================================================

@tool("file_read_tool")
def file_read_tool(file_path: str, start_line: int = 1, end_line: int = -1) -> str:
    """
    Liest den Inhalt einer Textdatei (optional zeilenweise eingegrenzt) aus.

    Args:
        file_path: Relativer oder absoluter Pfad zur Datei.
        start_line: Erste zu lesende Zeile (1-indiziert, Standard: 1).
        end_line: Letzte zu lesende Zeile (-1 bedeutet bis zum Ende der Datei).

    Returns:
        Der Dateiinhalt mit vorangestellten Zeilennummern.
    """
    if is_debug():
        log_tool_payload("file_read_tool", {"file_path": file_path, "start_line": start_line, "end_line": end_line})

    target = Path(file_path).resolve()
    if not target.exists() or not target.is_file():
        res = f"Fehler: Datei '{file_path}' existiert nicht."
        if is_debug():
            log_tool_payload("file_read_tool", {"file_path": file_path}, result=res)
        return res

    try:
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        total_lines = len(lines)
        if start_line < 1:
            start_line = 1
        if end_line == -1 or end_line > total_lines:
            end_line = total_lines

        output_lines: List[str] = []
        for i in range(start_line - 1, end_line):
            output_lines.append(f"{i + 1:4d} | {lines[i].rstrip()}")

        return "\n".join(output_lines)
    except Exception as exc:
        return f"Fehler beim Lesen der Datei '{file_path}': {exc}"


# Global active workspace directory tracking
_CURRENT_WORKSPACE_PATH: str = os.path.abspath(".")


def set_active_workspace(path: str) -> None:
    """Sets the active authorized workspace directory for file sandboxing."""
    global _CURRENT_WORKSPACE_PATH
    if path:
        _CURRENT_WORKSPACE_PATH = os.path.abspath(path)


def get_active_workspace() -> str:
    """Returns the active authorized workspace directory."""
    return _CURRENT_WORKSPACE_PATH


def validate_and_resolve_workspace_path(
    filepath: str,
    workspace_path: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    """
    Validates that a file path resides strictly inside the authorized workspace directory.
    - Relative paths are resolved to os.path.abspath(os.path.join(workspace_path, filepath))
    - Absolute paths are checked via os.path.commonpath([target_path, workspace_path]) == workspace_path
    - Outside paths immediately abort with:
      'Sicherheitsblockade: Schreiben außerhalb des autorisierten Projektordners ist nicht erlaubt.'
    - Missing subdirectories in workspace are automatically created via os.makedirs(os.path.dirname(target_path), exist_ok=True)
    """
    ws = os.path.abspath(workspace_path or _CURRENT_WORKSPACE_PATH)
    clean_fp = filepath.strip()

    # a) Relative Pfade auflösen
    if not os.path.isabs(clean_fp):
        target_path = os.path.abspath(os.path.join(ws, clean_fp))
    else:
        target_path = os.path.abspath(clean_fp)

    # b) Prüfen: os.path.commonpath([target_path, workspace_path]) == workspace_path
    try:
        norm_target = os.path.normcase(target_path)
        norm_ws = os.path.normcase(ws)
        is_inside = os.path.commonpath([norm_target, norm_ws]) == norm_ws
    except ValueError:
        is_inside = False

    # c) Liegt das Ziel AUßERHALB des Projektordners, bricht der Vorgang sofort ab
    if not is_inside:
        return None, "Sicherheitsblockade: Schreiben außerhalb des autorisierten Projektordners ist nicht erlaubt."

    # d) Fehlende Unterverzeichnisse im Workspace werden automatisch angelegt
    parent_dir = os.path.dirname(target_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    return target_path, None


def safe_write_file(file_path: str, content: str, workspace_path: Optional[str] = None) -> str:
    """
    Direct function to write or overwrite a file strictly inside the authorized workspace directory.
    Creates missing subdirectories automatically.

    Args:
        file_path: Relative or absolute file path within workspace.
        content: The text content to write.
        workspace_path: Optional workspace path (defaults to active workspace).

    Returns:
        Success string or security blockage / error message.
    """
    if is_debug():
        log_tool_payload("file_write_tool", {"file_path": file_path, "content_len": len(content)})
    target_path, err = validate_and_resolve_workspace_path(file_path, workspace_path)
    if err:
        if is_debug():
            log_tool_payload("file_write_tool", {"file_path": file_path}, result=err)
        return err

    try:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)
        res = f"Erfolg: Datei '{target_path}' wurde erfolgreich mit {len(content)} Zeichen gespeichert."
        if is_debug():
            log_tool_payload("file_write_tool", {"file_path": file_path}, result=res)
        return res
    except Exception as exc:
        if is_debug():
            log_tool_payload("file_write_tool", {"file_path": file_path}, exc=exc)
        return f"Fehler beim Schreiben der Datei '{file_path}': {exc}"


@tool("file_write_tool")
def file_write_tool(file_path: str, content: str, workspace_path: Optional[str] = None) -> str:
    """
    Schreibt oder überschreibt eine Datei vollständig mit dem angegebenen Inhalt.
    Erstellt bei Bedarf übergeordnete Ordner automatisch.
    Strikte Sandbox: Pfade müssen innerhalb des autorisierten Projektordners liegen.

    Args:
        file_path: Relativer oder absoluter Pfad der Zieldatei im Projektordner.
        content: Der vollständige Textinhalt.
        workspace_path: Optionaler Workspace-Pfad (Standard: aktiver Projektordner).

    Returns:
        Erfolgs- oder Fehlermeldung bzw. Sicherheitsblockade.
    """
    return safe_write_file(file_path, content, workspace_path)


@tool("file_patch_tool")
def file_patch_tool(
    file_path: str,
    target_snippet: str,
    replacement_snippet: str,
    workspace_path: Optional[str] = None,
) -> str:
    """
    Führt einen gezielten, punktuellen Patch an einer Datei durch,
    indem ein exakter Textblock durch neuen Code ersetzt wird.
    Strikte Sandbox: Pfade müssen innerhalb des autorisierten Projektordners liegen.

    Args:
        file_path: Relativer oder absoluter Pfad der zu bearbeitenden Datei.
        target_snippet: Der exakte zu ersetzende Code-Ausschnitt.
        replacement_snippet: Der neue Code-Ausschnitt.
        workspace_path: Optionaler Workspace-Pfad (Standard: aktiver Projektordner).

    Returns:
        Statusbericht des Patch-Vorgangs oder Sicherheitsblockade.
    """
    target_path, err = validate_and_resolve_workspace_path(file_path, workspace_path)
    if err:
        return err

    if not os.path.exists(target_path) or not os.path.isfile(target_path):
        return f"Fehler: Datei '{file_path}' existiert nicht im autorisierten Workspace."

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read()

        count = content.count(target_snippet)
        if count == 0:
            return (
                f"Fehler: Das Zielmuster wurde in '{file_path}' nicht gefunden. "
                "Bitte prüfen Sie Zeilenumbrüche und Einrückungen."
            )
        if count > 1:
            return (
                f"Fehler: Das Zielmuster kommt {count}-mal in '{file_path}' vor. "
                "Bitte wählen Sie einen längeren, eindeutigen Kontext-Block."
            )

        new_content = content.replace(target_snippet, replacement_snippet, 1)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return f"Erfolg: Datei '{file_path}' wurde punktuell gepatcht (1 Ersetzung)."
    except Exception as exc:
        return f"Fehler beim Patchen der Datei '{file_path}': {exc}"


# Standardized aliases
FileWriterTool = file_write_tool
FilePatchTool = file_patch_tool


# =====================================================================
# 3. DuckDuckGo Websearch-Werkzeug
# =====================================================================

@tool("web_search_tool")
def web_search_tool(query: str, max_results: int = 3) -> str:
    """
    Führt eine Live-Websuche über DuckDuckGo durch und liefert präzise Suchtreffer.
    Enthält Titel, Snippet und URL pro Treffer.

    Args:
        query: Die Suchanfrage (z.B. "CrewAI local LLM ollama configuration").
        max_results: Maximale Trefferanzahl (Standard: 3).

    Returns:
        Formatierte Zusammenfassung der Suchergebnisse oder Fehlermeldung.
    """
    if not DDGS_AVAILABLE or DDGS is None:
        return (
            "Fehler: 'duckduckgo-search' ist nicht installiert. "
            "Bitte 'pip install duckduckgo-search' ausführen."
        )

    clean_query = query.strip()
    if not clean_query:
        return "Fehler: Die Suchanfrage darf nicht leer sein."

    if is_debug():
        log_tool_payload("web_search_tool", {"query": clean_query, "max_results": max_results})

    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(clean_query, max_results=max_results))

        if not raw_results:
            return f"Keine Web-Suchergebnisse für '{clean_query}' gefunden."

        formatted_entries: List[str] = []
        for idx, item in enumerate(raw_results, start=1):
            title = item.get("title", "Kein Titel")
            body = item.get("body", "Keine Beschreibung verfügbar")
            href = item.get("href", "")
            entry = f"[{idx}] {title}\nURL: {href}\nAuszug: {body}"
            formatted_entries.append(entry)

        header = f"DuckDuckGo Suchergebnisse für '{clean_query}':\n" + ("=" * 60)
        return header + "\n\n" + "\n\n".join(formatted_entries)

    except Exception as exc:
        logger.warning("DuckDuckGo search error for query '%s': %s", clean_query, exc)
        return f"Netzwerk- oder Suchfehler bei DuckDuckGo: {exc}"


# =====================================================================
# 4. Workspace Tools Factory & Container
# =====================================================================

class WorkspaceToolList(list):
    """List of tools providing both sequence iteration and dictionary-style name access."""

    def __init__(self, tools_dict: Dict[str, Any]) -> None:
        super().__init__(tools_dict.values())
        self._dict = tools_dict

    def __getitem__(self, item: Any) -> Any:
        if isinstance(item, str):
            return self._dict[item]
        return super().__getitem__(item)

    def get(self, key: str, default: Any = None) -> Any:
        return self._dict.get(key, default)


def get_workspace_tools(workspace_path: str) -> WorkspaceToolList:
    """
    Sets the active authorized workspace directory and returns configured CrewAI tool instances.
    Compatible with Agent(tools=...) as a list, and supports dict access by tool name.

    Args:
        workspace_path: Path to the active workspace project directory.

    Returns:
        WorkspaceToolList containing all valid CrewAI tool instances.
    """
    set_active_workspace(workspace_path)
    tools_dict = {
        "file_grep_tool": file_grep_tool,
        "file_read_tool": file_read_tool,
        "file_write_tool": file_write_tool,
        "file_patch_tool": file_patch_tool,
        "web_search_tool": web_search_tool,
    }
    return WorkspaceToolList(tools_dict)

