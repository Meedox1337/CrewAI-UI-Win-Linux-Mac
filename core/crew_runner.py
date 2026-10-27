"""
Local Crew Cockpit - CrewAI Orchestration Engine
Thread-safe execution runner with dynamic agent instantiation, Ollama LLM binding,
Lead-Agent architecture, live step callbacks, token budgeting, error recall, and HITL support.
"""

import json
import logging
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional
import requests

from core.locales import get_canonical_role_key
from core.model_knowledge import can_use_tools, estimate_model_vram_gb
from core.tools import (
    file_grep_tool,
    file_patch_tool,
    file_read_tool,
    file_write_tool,
    get_workspace_tools,
    safe_write_file,
    set_active_workspace,
    web_search_tool,
)

# Standardized alias for FileWriterTool
FileWriterTool = file_write_tool

from core.logger import is_debug, log_crew_step

logger = logging.getLogger(__name__)


def query_model_context_limit(model_name: str, host: str = "http://localhost:11434") -> int:
    """
    Queries Ollama /api/show to determine the model's native context length.
    Returns integer token count (e.g. 65536, 131072), defaulting to 65536 (64k).
    """
    try:
        url = f"{host.rstrip('/')}/api/show"
        resp = requests.post(url, json={"name": model_name}, timeout=(2.0, 3.0))
        if resp.status_code == 200:
            data = resp.json()
            model_info = data.get("model_info", {})
            candidates: List[int] = []
            for k, v in model_info.items():
                if k.endswith(".context_length") and isinstance(v, int) and v > 0:
                    candidates.append(v)
            if candidates:
                return max(candidates)
            params = data.get("parameters", "")
            if params and "num_ctx" in params:
                for line in params.splitlines():
                    if "num_ctx" in line:
                        parts = line.strip().split()
                        if len(parts) >= 2 and parts[-1].isdigit():
                            return int(parts[-1])
    except Exception as exc:
        logger.debug("Could not determine context limit for %s: %s", model_name, exc)
    return 65536


def calculate_hardware_context_limit(
    model_configs: List[Dict[str, Any]],
    host: str = "http://localhost:11434",
    vram_total_override: Optional[float] = None,
) -> int:
    """
    Dynamically and hardware-agnostically calculates the optimal context window (num_ctx):
    1. Queries total available GPU VRAM via SystemMonitor / NVML (vram_total_gb).
    2. Determines memory requirement of the largest model in the active team (max_model_size_gb).
    3. Calculates remaining headroom for KV-cache:
       vram_headroom = vram_total_gb - max_model_size_gb - 2.0 (2 GB OS/UI safety margin).
    4. Hardware tier derivation:
       - vram_headroom >= 10.0 GB -> 65536 (64k) (or 131072 if model natively supports 128k)
       - vram_headroom >= 5.0 GB  -> 32768 (32k)
       - vram_headroom >= 2.0 GB  -> 16384 (16k)
       - vram_headroom < 2.0 GB   -> 8192 (or 4096 if headroom < 1.0 GB)
    5. Bounds value to the models' native context limit from Ollama /api/show.
    """
    # 1. Total VRAM detection
    vram_total_gb = 16.0
    if vram_total_override is not None and vram_total_override > 0:
        vram_total_gb = float(vram_total_override)
    else:
        try:
            from core.system_monitor import SystemMonitor
            mon = SystemMonitor()
            mem = mon.get_memory_status()
            if mem.get("total_gb", 0) > 0:
                vram_total_gb = float(mem["total_gb"])
        except Exception as exc:
            logger.debug("Could not query GPU VRAM via SystemMonitor: %s", exc)

    # 2. Footprint of largest model in active team
    max_model_size_gb = 0.0
    native_limits: List[int] = []

    for cfg in model_configs:
        if cfg.get("enabled", True):
            m_name = cfg.get("model_name") or cfg.get("model", "")
            if m_name:
                size = estimate_model_vram_gb(m_name)
                if size > max_model_size_gb:
                    max_model_size_gb = size
                native_limit = query_model_context_limit(m_name, host=host)
                native_limits.append(native_limit)

    if max_model_size_gb <= 0.0:
        max_model_size_gb = 6.0

    max_native_ctx = max(native_limits) if native_limits else 65536
    min_native_ctx = min(native_limits) if native_limits else 65536

    # 3. KV-cache headroom (2.0 GB safety buffer for OS/desktop UI)
    vram_headroom = vram_total_gb - max_model_size_gb - 2.0

    # 4. Hardware-tier context derivation
    if vram_headroom >= 10.0:
        if max_native_ctx >= 131072:
            computed_limit = 131072
        else:
            computed_limit = 65536
    elif vram_headroom >= 5.0:
        computed_limit = 32768
    elif vram_headroom >= 2.0:
        computed_limit = 16384
    elif vram_headroom >= 1.0:
        computed_limit = 8192
    else:
        computed_limit = 4096

    # 5. Cap by native model context limit so Ollama does not fail
    final_limit = min(computed_limit, min_native_ctx)
    return max(4096, final_limit)


def extract_simulated_file_writes(text: str) -> List[Dict[str, str]]:
    """
    Extracts simulated file_write_tool calls from agent raw output text.
    Detects JSON patterns such as:
      {"name": "file_write_tool", "arguments": {"file_path": "...", "content": "..."}}
      {"tool": "file_write_tool", "tool_input": {"file_path": "...", "content": "..."}}
      markdown code blocks, JSON lists, or regex fallbacks.
    """
    writes: List[Dict[str, str]] = []
    if not text or "file_write_tool" not in text:
        return writes

    # 1. Bracket scanner to locate JSON object or list boundaries
    json_candidates: List[Any] = []
    n = len(text)
    i = 0
    while i < n:
        if text[i] in ('{', '['):
            open_char = text[i]
            close_char = '}' if open_char == '{' else ']'
            start = i
            depth = 0
            in_string = False
            escape = False
            j = i
            while j < n:
                ch = text[j]
                if in_string:
                    if escape:
                        escape = False
                    elif ch == '\\':
                        escape = True
                    elif ch == '"':
                        in_string = False
                else:
                    if ch == '"':
                        in_string = True
                    elif ch == open_char:
                        depth += 1
                    elif ch == close_char:
                        depth -= 1
                        if depth == 0:
                            candidate = text[start : j + 1]
                            try:
                                parsed = json.loads(candidate)
                                json_candidates.append(parsed)
                            except Exception:
                                try:
                                    cleaned = re.sub(
                                        r'[\x00-\x1f]',
                                        lambda m: '\\u00%02x' % ord(m.group()),
                                        candidate
                                    )
                                    parsed = json.loads(cleaned)
                                    json_candidates.append(parsed)
                                except Exception:
                                    pass
                            i = j
                            break
                j += 1
        i += 1

    def process_obj(obj: Any) -> None:
        if isinstance(obj, list):
            for item in obj:
                process_obj(item)
            return
        if not isinstance(obj, dict):
            return

        name = obj.get("name") or obj.get("tool") or obj.get("action") or ""
        args = (
            obj.get("arguments")
            or obj.get("parameters")
            or obj.get("tool_input")
            or obj.get("action_input")
            or obj.get("input")
        )
        if not isinstance(args, dict):
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            else:
                args = {}

        if "file_write_tool" in str(name).lower() or "file_write_tool" in str(obj.get("name", "")).lower():
            fp = args.get("file_path") or args.get("filepath") or args.get("path") or args.get("filename")
            cnt = args.get("content") or args.get("code") or args.get("text") or args.get("file_content")
            if not fp:
                fp = obj.get("file_path") or obj.get("filepath") or obj.get("path") or obj.get("filename")
            if cnt is None:
                cnt = obj.get("content") or obj.get("code") or obj.get("text") or obj.get("file_content")
            if fp and cnt is not None:
                writes.append({"file_path": str(fp).strip(), "content": str(cnt)})

    for cand in json_candidates:
        process_obj(cand)

    # 2. Regex Fallback if standard JSON decoding did not catch it
    if not writes:
        pattern = re.compile(
            r'["\']name["\']\s*:\s*["\']file_write_tool["\'][\s\S]*?'
            r'["\']file_path["\']\s*:\s*["\']([^"\']+)["\'][\s\S]*?'
            r'["\']content["\']\s*:\s*["\']([\s\S]*?)["\']\s*\}',
            re.DOTALL
        )
        for m in pattern.finditer(text):
            fp = m.group(1).strip()
            cnt = m.group(2)
            cnt = cnt.replace(r'\n', '\n').replace(r'\t', '\t').replace(r'\"', '"').replace(r'\\', '\\')
            writes.append({"file_path": fp, "content": cnt})

    return writes

# Safe optional import of CrewAI components
try:
    from crewai import Agent, Crew, Process, Task, LLM
    CREWAI_AVAILABLE = True
except (ImportError, Exception) as exc:
    logger.debug("CrewAI not available in environment: %s", exc)
    CREWAI_AVAILABLE = False
    Agent = Any  # type: ignore
    Crew = Any  # type: ignore
    Process = Any  # type: ignore
    Task = Any  # type: ignore
    LLM = Any  # type: ignore


class CrewRunner:
    """
    Manages non-blocking execution of local CrewAI teams.
    Streams thoughts and steps back to the UI thread-safely.
    """

    def __init__(self, ollama_host: str = "http://localhost:11434") -> None:
        self.ollama_host = ollama_host.rstrip("/")
        self.is_running: bool = False
        self.stop_requested: bool = False
        self._is_cancelled: bool = False
        self.worker_thread: Optional[Any] = None
        self._active_callbacks: Dict[str, Callable[..., None]] = {}

        # Human-in-the-Loop iteration state
        self.last_master_prompt: str = ""
        self.last_configs: List[Dict[str, Any]] = []
        self.last_workspace: str = "."
        self.last_included_files: List[str] = []
        self.accumulated_tokens: int = 0

    def cancel(self) -> None:
        """Immediately halts workflow execution, cancels subtasks and flags cancellation."""
        self._is_cancelled = True
        self.stop_requested = True
        self.is_running = False
        logger.info("CrewRunner: Workflow execution cancelled.")
        if self._active_callbacks:
            try:
                cb_canc = self._active_callbacks.get("on_cancelled")
                if callable(cb_canc):
                    cb_canc()
                cb_fin = self._active_callbacks.get("on_finish")
                if callable(cb_fin):
                    cb_fin(False, "Abgebrochen")
            except Exception as e:
                logger.debug("Exception emitting cancellation from cancel(): %s", e)

    def stop_workflow(self) -> None:
        """Alias for cancel()."""
        self.cancel()

    def run(
        self,
        model_configs: List[Dict[str, Any]],
        master_prompt: str,
        workspace_path: str,
        included_files: List[str],
        callbacks: Dict[str, Callable[..., None]],
        revision_feedback: Optional[str] = None,
    ) -> None:
        """Direct execution entry point for background worker threads."""
        self._run_crew_worker(
            model_configs=model_configs,
            master_prompt=master_prompt,
            workspace_path=workspace_path,
            included_files=included_files,
            callbacks=callbacks,
            revision_feedback=revision_feedback,
        )

    def start_workflow(
        self,
        model_configs: List[Dict[str, Any]],
        master_prompt: str,
        workspace_path: str,
        included_files: List[str],
        callbacks: Dict[str, Callable[..., None]],
        revision_feedback: Optional[str] = None,
    ) -> bool:
        """
        Launches the orchestrated crew run in a background daemon thread.
        """
        if self.is_running:
            return False

        self.is_running = True
        self.stop_requested = False
        self._is_cancelled = False
        self.accumulated_tokens = 0

        self.last_master_prompt = master_prompt
        self.last_configs = model_configs
        self.last_workspace = workspace_path
        self.last_included_files = included_files

        self.worker_thread = threading.Thread(
            target=self.run,
            args=(model_configs, master_prompt, workspace_path, included_files, callbacks, revision_feedback),
            daemon=True,
            name="CrewAI-WorkerThread",
        )
        self.worker_thread.start()
        return True

    @staticmethod
    def _extract_section_for_agent(prompt: str, role: str, canon_role: str, index: int) -> str:
        """
        Extracts an agent-specific instruction section from the master prompt.
        Handles numbered/bracketed formats (e.g. '1. [Architekt]: ...', '[Architekt] ...', '1. ...').
        """
        if not prompt:
            return ""

        candidates = [re.escape(role)]
        if canon_role and canon_role.lower() != role.lower():
            candidates.append(re.escape(canon_role))

        # Role-based alias expansion to guarantee robust matching for all preset roles
        role_aliases = {
            "architect": ["architekt", "architect", "planner", "planer"],
            "coder": ["coder", "entwickler", "developer", "programmierer"],
            "researcher": ["recherche", "rechercheur", "research", "researcher", "analyst"],
            "reviewer": ["prüfer", "pruefer", "reviewer", "review", "qa", "tester", "auditor"],
        }
        if canon_role in role_aliases:
            for alias in role_aliases[canon_role]:
                if alias.lower() not in [c.lower() for c in candidates]:
                    candidates.append(re.escape(alias))

        # Extract keywords from compound role names (e.g. 'Entwickler' from 'Senior-Entwickler')
        words = [w for w in re.split(r"[\s\-_/]+", role) if len(w) >= 4]
        for w in words:
            if w.lower() not in [c.lower() for c in candidates]:
                candidates.append(re.escape(w))

        pattern_role = "|".join(candidates)

        # 1. Role-labeled sections: "1. [Role]: ...", "[Role] ...", "Role: ..."
        role_regex = (
            rf"(?:^|\n)\s*(?:(?:\d+[\.\)]\s*)?\[?(?:{pattern_role})[\]:]?[:\-]?\s*)"
            rf"(.*?)(?=(?:\n\s*(?:\d+[\.\)]\s*)?\[?[A-ZÄÖÜa-zäöüß][\w\s\-_/]{{2,30}}[\]:]|\Z))"
        )
        m = re.search(role_regex, prompt, re.DOTALL | re.IGNORECASE)
        if m:
            extracted = m.group(1).strip()
            if len(extracted) > 5:
                return extracted

        # 2. Numbered index-based sections: "1. ...", "2. ..."
        idx_regex = (
            rf"(?:^|\n)\s*{index + 1}[\.\)]\s*(?:\[?[^\]\n]+\]?[:\-])?\s*"
            rf"(.*?)(?=(?:\n\s*\d+[\.\)]\s*)|\Z)"
        )
        m_idx = re.search(idx_regex, prompt, re.DOTALL)
        if m_idx:
            extracted = m_idx.group(1).strip()
            if len(extracted) > 5:
                return extracted

        return ""

    def _run_crew_worker(
        self,
        model_configs: List[Dict[str, Any]],
        master_prompt: str,
        workspace_path: str,
        included_files: List[str],
        callbacks: Dict[str, Callable[..., None]],
        revision_feedback: Optional[str],
    ) -> None:
        # Thread-safe callback dispatchers for UI / Qt Signal integration
        def safe_call(func: Optional[Callable[..., None]], *args: Any, **kwargs: Any) -> None:
            if func and callable(func):
                try:
                    if is_debug():
                        log_crew_step("Pipeline", getattr(func, "__name__", "callback"), payload={"args": args, "kwargs": kwargs})
                    func(*args, **kwargs)
                except Exception as cb_err:
                    if is_debug():
                        log_crew_step("Pipeline", getattr(func, "__name__", "callback"), exc=cb_err)
                    logger.debug("Qt/UI callback invocation exception caught: %s", cb_err)

        self._active_callbacks = callbacks

        raw_on_log = callbacks.get("on_log")
        raw_on_status = callbacks.get("on_card_status")
        raw_on_thought = callbacks.get("on_card_thought")
        raw_on_step = callbacks.get("on_step")
        raw_on_banner = callbacks.get("on_banner")
        raw_on_result = callbacks.get("on_result")
        raw_on_finish = callbacks.get("on_finish")
        raw_on_task_completed = callbacks.get("on_task_completed")
        raw_on_tokens = callbacks.get("on_tokens")
        raw_on_cancelled = callbacks.get("on_cancelled")

        on_log = lambda text, tag="INFO": safe_call(raw_on_log, text, tag)
        on_card_status = lambda name, stat, det="": safe_call(raw_on_status, name, stat, det)
        on_card_thought = lambda name, chunk: safe_call(raw_on_thought, name, chunk)
        on_step = lambda agent, stype, det="", tok=0: safe_call(raw_on_step, agent, stype, det, tok)
        on_banner = lambda msg, typ="warning": safe_call(raw_on_banner, msg, typ)
        on_result = lambda res: safe_call(raw_on_result, res)
        on_finish = lambda succ, msg="": safe_call(raw_on_finish, succ, msg)
        on_task_completed = lambda name, out: safe_call(raw_on_task_completed, name, out)

        # 0. Hardware-agnostische, dynamische Ermittlung des optimalen Kontextfensters
        pipeline_max_tokens = calculate_hardware_context_limit(
            model_configs=model_configs,
            host=self.ollama_host,
        )

        on_tokens = lambda used, max_t=pipeline_max_tokens: safe_call(raw_on_tokens, used, max_t)
        on_cancelled = lambda: safe_call(raw_on_cancelled)

        self.accumulated_tokens = 0
        on_tokens(0, pipeline_max_tokens)

        if self._is_cancelled or self.stop_requested:
            on_cancelled()
            on_finish(False, "Abgebrochen")
            return

        set_active_workspace(workspace_path)
        on_log(f"Starte Crew-Orchestrierung für Workspace: {workspace_path}", "INFO")
        on_log(f"Aktive Dateien im Kontext: {len(included_files)}", "INFO")

        # Set all active cards to "thinking / initializing"
        for cfg in model_configs:
            on_card_status(cfg["model_name"], "thinking", "Initialisiere...")

        if not CREWAI_AVAILABLE:
            # Fallback execution simulation if CrewAI is not yet installed in host environment
            self._simulate_execution(model_configs, master_prompt, workspace_path, callbacks, revision_feedback)
            self.is_running = False
            return

        try:
            # 1. LLM & Agenten dynamisch instanziieren
            agents: List[Any] = []
            active_agent_records: List[Dict[str, Any]] = []
            crew_holder: List[Any] = []

            def extract_token_count(source: Any) -> int:
                if source is None:
                    return 0
                for attr in ("total_tokens", "token_usage", "usage", "usage_metrics"):
                    val = getattr(source, attr, None)
                    if isinstance(val, int) and val > 0:
                        return val
                    if isinstance(val, dict):
                        tot = val.get("total_tokens") or (val.get("prompt_tokens", 0) + val.get("completion_tokens", 0))
                        if tot and int(tot) > 0:
                            return int(tot)
                    elif val and hasattr(val, "total_tokens") and getattr(val, "total_tokens", 0) > 0:
                        return int(val.total_tokens)
                if isinstance(source, dict):
                    tot = source.get("total_tokens") or (source.get("prompt_tokens", 0) + source.get("completion_tokens", 0))
                    if tot and int(tot) > 0:
                        return int(tot)
                return 0

            def query_current_tokens() -> int:
                tot = 0
                if crew_holder and crew_holder[0] is not None:
                    try:
                        c = crew_holder[0]
                        if hasattr(c, "usage_metrics") and c.usage_metrics:
                            tot = max(tot, extract_token_count(c.usage_metrics))
                        if hasattr(c, "calculate_usage_metrics"):
                            m = c.calculate_usage_metrics()
                            if m and getattr(m, "total_tokens", 0) > 0:
                                tot = max(tot, int(m.total_tokens))
                    except Exception:
                        pass
                for ag in agents:
                    try:
                        if hasattr(ag, "llm") and hasattr(ag.llm, "get_token_usage_summary"):
                            summ = ag.llm.get_token_usage_summary()
                            if summ and getattr(summ, "total_tokens", 0) > 0:
                                tot = max(tot, int(summ.total_tokens))
                        if hasattr(ag, "_token_process"):
                            tp = ag._token_process.get_summary()
                            if tp and getattr(tp, "total_tokens", 0) > 0:
                                tot = max(tot, int(tp.total_tokens))
                    except Exception:
                        pass
                return tot

            for cfg in model_configs:
                if not cfg.get("enabled", True):
                    continue

                model_name = cfg["model_name"]
                role = cfg.get("role", "Senior-Entwickler")
                canon_role = cfg.get("canonical_role") or get_canonical_role_key(role)
                goal = cfg.get("goal", "Erfülle die Aufgabe präzise.")
                backstory = cfg.get("backstory", "Professioneller KI-Agent.")
                use_web = bool(
                    cfg.get("allow_web")
                    or cfg.get("allow_web_search")
                    or cfg.get("websearch")
                    or canon_role == "researcher"
                    or "recherche" in role.lower()
                    or "research" in role.lower()
                )
                allow_file_write = bool(cfg.get("allow_file_write", False))
                allow_delegation = cfg.get("allow_delegation", False)

                # Strikt prüfen, ob das Modell Tool-Calling unterstützt
                if not can_use_tools(model_name, host=self.ollama_host):
                    agent_tools: List[Any] = []
                    on_log(
                        f"Agent '{role}' ({model_name}): Modell unterstützt kein Tool-Calling -> tools=[] zugewiesen",
                        "INFO",
                    )
                else:
                    # Standardmäßig Lese-Tools zuweisen
                    agent_tools = [file_read_tool, file_grep_tool]

                    # Web-Recherche hinzufügen, falls erlaubt
                    if use_web:
                        agent_tools.append(web_search_tool)

                    # Datei-Schreibwerkzeuge nur bei explizit erteilter Berechtigung
                    if allow_file_write:
                        agent_tools.extend([file_write_tool, file_patch_tool])
                        on_log(f"Agent '{role}' mit Datei-Schreibrechten autorisiert", "INFO")
                    else:
                        on_log(f"Agent '{role}' im Read-Only-Modus aktiv", "INFO")

                # LLM via Ollama anbinden mit dynamischem Kontextfenster (num_ctx via extra_body) und Timeout-Schutz
                ollama_base = self.ollama_host.rstrip("/")
                v1_url = f"{ollama_base}/v1" if not ollama_base.endswith("/v1") else ollama_base

                llm = LLM(
                    model=f"ollama/{model_name}",
                    base_url=v1_url,
                    temperature=0.2,
                    timeout=180,
                    extra_body={
                        "num_ctx": pipeline_max_tokens,
                        "options": {"num_ctx": pipeline_max_tokens},
                    },
                )

                # Step-Callback für diesen spezifischen Agenten
                def make_step_callback(m_name: str, a_role: str):
                    def _step_cb(step_output: Any) -> None:
                        if self._is_cancelled or self.stop_requested:
                            raise InterruptedError("Workflow durch Anwender abgebrochen.")

                        on_card_status(m_name, "action", "In Aktion...")

                        # 1. Gedanken, Reasoning-Snippets und <think>-Inhalte abfangen
                        thought_raw = ""
                        if hasattr(step_output, "thought") and step_output.thought:
                            thought_raw = str(step_output.thought)
                        elif hasattr(step_output, "log") and step_output.log:
                            thought_raw = str(step_output.log)
                        elif hasattr(step_output, "output") and step_output.output:
                            thought_raw = str(step_output.output)
                        else:
                            thought_raw = str(step_output)

                        # Parse <think>...</think> oder Reasoning
                        if "<think>" in thought_raw:
                            parts = thought_raw.split("<think>")
                            for p in parts[1:]:
                                if "</think>" in p:
                                    think_block = p.split("</think>")[0].strip()
                                    if think_block:
                                        on_card_thought(m_name, f"🧠 {think_block}")
                                else:
                                    if p.strip():
                                        on_card_thought(m_name, f"🧠 {p.strip()}")
                        elif thought_raw.strip():
                            clean_t = thought_raw.strip()
                            on_card_thought(m_name, clean_t)

                        # 2. Reale Token-Metriken abfragen und inkrementell akkumulieren
                        real_tokens = query_current_tokens()
                        step_tokens = extract_token_count(step_output)
                        if real_tokens > self.accumulated_tokens:
                            self.accumulated_tokens = real_tokens
                        elif step_tokens > 0:
                            self.accumulated_tokens += step_tokens
                        else:
                            tokens_est = max(1, len(thought_raw) // 4)
                            self.accumulated_tokens += tokens_est

                        on_tokens(self.accumulated_tokens, pipeline_max_tokens)
                        on_step(m_name, "token", thought_raw[:120], self.accumulated_tokens)

                        # 3. Formatiere für Live-Log und Tool-Events
                        if hasattr(step_output, "tool"):
                            tool_name = getattr(step_output, "tool", "Tool")
                            tool_inp = getattr(step_output, "tool_input", "")
                            on_log(f"[{a_role}] ruft Werkzeug auf: {tool_name}({tool_inp})", "TOOL")
                            on_step(m_name, "tool", f"{tool_name}({tool_inp})", 0)
                        else:
                            clean_text = thought_raw.strip()
                            if len(clean_text) > 300:
                                clean_text = clean_text[:300] + "..."
                            on_log(f"[{a_role}] Gedanke: {clean_text}", "AGENT")
                            on_step(m_name, "thought", clean_text, self.accumulated_tokens)

                    return _step_cb

                if allow_file_write:
                    backstory += (
                        "\n\nWICHTIGSTE REGEL: Gib NIEMALS ein JSON-Objekt wie '{\"name\": \"file_write_tool\"...}' als Textantwort aus! "
                        "Du MUSST das Werkzeug 'file_write_tool' physisch über den Funktionsaufruf-Mechanismus ausführen. "
                        "Eine Textausgabe von Tool-Aufrufen gilt als schwerer Fehler."
                    )

                # Agent mit max_iter=3 und Timeout-Schutz gegen Endlosschleifen
                agent = Agent(
                    role=role,
                    goal=goal,
                    backstory=backstory,
                    tools=agent_tools,
                    llm=llm,
                    verbose=True,
                    allow_delegation=allow_delegation,
                    max_iter=3,
                    max_execution_time=180,
                    step_callback=make_step_callback(model_name, role),
                )

                agents.append(agent)
                active_agent_records.append({"agent": agent, "cfg": cfg})

            if not agents:
                on_banner("Keine aktiven Agenten ausgewählt!", "error")
                on_finish(False, "Keine Agenten aktiv.")
                self.is_running = False
                return

            on_log(f"{len(agents)} Agent(en) erfolgreich initialisiert.", "INFO")

            # 2. Dynamische 1:1 Aufgaben (Tasks) für JEDEN aktiven Agenten erzeugen
            tasks: List[Any] = []

            # Dateikontext-Zusammenfassung
            files_context = "\n".join([f"- {f}" for f in included_files[:30]])
            if len(included_files) > 30:
                files_context += f"\n... und {len(included_files) - 30} weitere Dateien."
            elif not included_files:
                files_context = "(Keine spezifischen Dateien ausgewählt - Workspace-Root aktiv)"

            for idx, item in enumerate(active_agent_records):
                agent = item["agent"]
                cfg = item["cfg"]
                role = cfg.get("role", "Senior-Entwickler")
                canon_role = cfg.get("canonical_role") or get_canonical_role_key(role)
                allow_file_write = cfg.get("allow_file_write", False)

                # 3. Überprüfung des Task-Flows:
                # Stelle sicher, dass Task 4 sauber dem Prüfer / Reviewer zugewiesen wird und nicht fälschlicherweise erneut dem Architekten
                if idx == 3:
                    if canon_role == "architect" or "architekt" in role.lower() or canon_role != "reviewer":
                        role = "Prüfer / Reviewer"
                        canon_role = "reviewer"
                        cfg["role"] = role
                        cfg["canonical_role"] = canon_role
                        if hasattr(agent, "role"):
                            agent.role = role
                        if hasattr(agent, "goal"):
                            agent.goal = "Prüfe Code und Architektur gründlich auf Fehler, Sicherheitslücken und Inkonsistenzen."
                        if hasattr(agent, "backstory"):
                            agent.backstory = "Erfahrener QA- und Code-Reviewer. Prüft Software-Implementierungen auf Robustheit, Korrektheit und Best Practices."
                        allow_file_write = False
                        cfg["allow_file_write"] = False
                        agent.tools = [file_read_tool, file_grep_tool]

                # Teilabschnitt für diesen Agenten extrahieren oder Rollen-Fallback
                extracted_mission = self._extract_section_for_agent(master_prompt, role, canon_role, idx)
                if extracted_mission:
                    task_desc = (
                        f"Aufgabe für deine Rolle '{role}':\n{extracted_mission}\n\n"
                        f"Gesamtaufgabe / Projekt-Kontext:\n{master_prompt}\n\n"
                        f"Projekt-Workspace: {workspace_path}\n"
                        f"Verfügbare Dateien:\n{files_context}"
                    )
                else:
                    if canon_role == "reviewer" or idx == 3:
                        task_desc = (
                            f"Aufgabe für deine Rolle '{role}':\n"
                            f"Führe eine gründliche Qualitäts-, Code- und Sicherheitsprüfung des gesamten Projekts durch.\n\n"
                            f"Gesamtaufgabe / Projekt-Kontext:\n{master_prompt}\n\n"
                            "Prüfe alle durch die vorherigen Entwickler erstellten oder modifizierten Dateien auf Korrektheit, "
                            "Architekturkonformität, Funktionalität und Sicherheit unter Berücksichtigung der Gesamtaufgabe.\n\n"
                            f"Projekt-Workspace: {workspace_path}\n"
                            f"Verfügbare Dateien:\n{files_context}"
                        )
                        expected_output = (
                            f"Vollständiger Prüf- und Reviewbericht als {role} mit konkreten Bewertungen, "
                            "festgestellten Mängeln und Freigabeempfehlung."
                        )
                    elif idx == 0:
                        task_desc = (
                            f"Arbeite als {role} an der Gesamtaufgabe:\n{master_prompt}\n\n"
                            f"Projekt-Workspace: {workspace_path}\n"
                            f"Verfügbare Dateien:\n{files_context}"
                        )
                    else:
                        task_desc = (
                            f"Arbeite als {role} an der Gesamtaufgabe:\n{master_prompt} "
                            f"unter Berücksichtigung der Ergebnisse der vorherigen Agenten.\n\n"
                            f"Projekt-Workspace: {workspace_path}\n"
                            f"Verfügbare Dateien:\n{files_context}"
                        )

                if revision_feedback:
                    task_desc += f"\n\nKORREKTUR-FEEDBACK AUS VORHERIGEM DURCHLAUF:\n{revision_feedback}"

                if allow_file_write:
                    task_desc += (
                        "\n\nSCHREIBRECHTE: Du bist autorisiert, Dateien mit 'file_write_tool' oder 'file_patch_tool' "
                        f"direkt im Projekt-Workspace anzulegen oder zu modifizieren.\n"
                        f"WICHTIG: Alle Dateien MÜSSEN im Projektordner '{workspace_path}' gespeichert werden. Pfade außerhalb sind verboten.\n"
                        "WICHTIGSTE REGEL: Gib NIEMALS ein JSON-Objekt wie '{\"name\": \"file_write_tool\"...}' als Textantwort aus! "
                        "Du MUSST das Werkzeug 'file_write_tool' physisch über den Funktionsaufruf-Mechanismus ausführen. "
                        "Eine Textausgabe von Tool-Aufrufen gilt als schwerer Fehler."
                    )
                    expected_output = (
                        f"Vollständiges Arbeitsergebnis und Code als {role}. "
                        "Erforderliche Dateien wurden direkt im Workspace über das Werkzeug 'file_write_tool' angelegt oder modifiziert."
                    )
                elif canon_role != "reviewer" and idx != 3:
                    task_desc += (
                        "\n\nWICHTIGER HINWEIS: Gib den Code ausschließlich als Markdown-Text aus. Führe keine Dateischreiboperationen aus. "
                        "Erstelle den Code als Markdown-Block im Text."
                    )
                    expected_output = (
                        f"Präzise Ausarbeitung, Analyse oder Code im Markdown-Format als {role}. "
                        "Keine Datei-Schreiboperationen ausgeführt."
                    )

                prev_task = tasks[-1] if tasks else None

                def make_task_callback(m_name: str, a_role: str, can_write: bool):
                    def _task_done(task_output: Any) -> None:
                        if self._is_cancelled or self.stop_requested:
                            raise InterruptedError("Workflow durch Anwender abgebrochen.")

                        out_text = ""
                        if hasattr(task_output, "raw") and task_output.raw:
                            out_text = str(task_output.raw)
                        elif hasattr(task_output, "output") and task_output.output:
                            out_text = str(task_output.output)
                        else:
                            out_text = str(task_output)

                        # Backend-Sicherheitsnetz: Automatisches Parsen von simulierten Tool-Calls
                        if can_write:
                            simulated_writes = extract_simulated_file_writes(out_text)
                            for sw in simulated_writes:
                                fp = sw["file_path"]
                                cnt = sw["content"]
                                safe_write_file(file_path=fp, content=cnt, workspace_path=workspace_path)
                                on_log(
                                    f"[SYSTEM-FALLBACK] Erkannte JSON-Tool-Simulation vom Coder wurde automatisch als physische Datei auf der Festplatte gespeichert: {fp}",
                                    "SUCCESS",
                                )

                        # Reale Token-Metriken nach Task-Abschluss abfragen
                        real_tokens = query_current_tokens()
                        task_tokens = extract_token_count(task_output)
                        if real_tokens > self.accumulated_tokens:
                            self.accumulated_tokens = real_tokens
                        elif task_tokens > 0:
                            self.accumulated_tokens += task_tokens
                        else:
                            self.accumulated_tokens += max(10, len(out_text) // 4)

                        on_tokens(self.accumulated_tokens, 32768)
                        on_log(f"[{a_role}] Task abgeschlossen (~{self.accumulated_tokens} Tokens kumuliert).", "INFO")
                        on_card_status(m_name, "done", "✓ Fertig")
                        on_task_completed(m_name, out_text)
                    return _task_done

                task = Task(
                    description=task_desc,
                    expected_output=expected_output,
                    agent=agent,
                    context=[prev_task] if prev_task else None,
                    callback=make_task_callback(cfg["model_name"], role, allow_file_write),
                )
                tasks.append(task)

            # 3. Crew instanziieren und ausführen
            crew = Crew(
                agents=agents,
                tasks=tasks,
                process=Process.sequential,
                verbose=True,
            )
            crew_holder.append(crew)

            if self._is_cancelled or self.stop_requested:
                on_cancelled()
                on_finish(False, "Abgebrochen")
                return

            on_log("Starte sequenziellen CrewAI-Workflow...", "INFO")
            start_time = time.time()

            result = crew.kickoff()
            duration = time.time() - start_time

            if self._is_cancelled or self.stop_requested:
                on_cancelled()
                on_finish(False, "Abgebrochen")
                return

            # Finale Tokens aus Crew-Metrics abfragen
            real_tokens = query_current_tokens()
            result_tokens = extract_token_count(result)
            if real_tokens > self.accumulated_tokens:
                self.accumulated_tokens = real_tokens
            elif result_tokens > 0:
                self.accumulated_tokens = max(self.accumulated_tokens, result_tokens)
            on_tokens(self.accumulated_tokens, 32768)

            result_str = str(result)
            on_log(f"Workflow erfolgreich beendet in {duration:.1f}s (~{self.accumulated_tokens} Tokens)", "SUCCESS")

            # Post-Kickoff: Finale Teilergebnisse an alle Karten senden, falls noch nicht erfolgt
            for idx, item in enumerate(active_agent_records):
                m_name = item["cfg"]["model_name"]
                can_write = item["cfg"].get("allow_file_write", False)
                if idx < len(tasks) and hasattr(tasks[idx], "output") and tasks[idx].output:
                    t_out = getattr(tasks[idx].output, "raw", str(tasks[idx].output))
                    if t_out:
                        if can_write:
                            for sw in extract_simulated_file_writes(str(t_out)):
                                fp = sw["file_path"]
                                safe_write_file(file_path=fp, content=sw["content"], workspace_path=workspace_path)
                                on_log(
                                    f"[SYSTEM-FALLBACK] Erkannte JSON-Tool-Simulation vom Coder wurde automatisch als physische Datei auf der Festplatte gespeichert: {fp}",
                                    "SUCCESS",
                                )
                        on_task_completed(m_name, str(t_out))

            # Status auf allen Karten auf 'done' setzen
            for cfg in model_configs:
                on_card_status(cfg["model_name"], "done", "Abgeschlossen")

            on_result(result_str)
            on_finish(True, "Erfolg")

        except InterruptedError:
            on_log("[ABBRUCH] Ausführung wurde vom Benutzer abgebrochen. System ist wieder startklar.", "WARNING")
            on_banner("Workflow abgebrochen.", "warning")
            for cfg in model_configs:
                on_card_status(cfg["model_name"], "ready", "Bereit")
            on_cancelled()
            on_finish(False, "Abgebrochen")

        except Exception as exc:
            if self._is_cancelled or self.stop_requested:
                on_log("[ABBRUCH] Ausführung wurde vom Benutzer abgebrochen. System ist wieder startklar.", "WARNING")
                on_banner("Workflow abgebrochen.", "warning")
                for cfg in model_configs:
                    on_card_status(cfg["model_name"], "ready", "Bereit")
                on_cancelled()
                on_finish(False, "Abgebrochen")
                return

            # Error-Recall: Timeout / Verbindung / Ollama-Fehler abfangen
            err_msg = str(exc)
            logger.error("Crew execution exception: %s", exc, exc_info=True)
            on_log(f"Fehler während der CrewAI-Ausführung: {err_msg}", "ERROR")

            # Verständliches Feedback im Banner
            if "Connection refused" in err_msg or "Failed to establish" in err_msg:
                on_banner("Ollama nicht erreichbar! Bitte 'ollama serve' ausführen.", "error")
            elif "model" in err_msg.lower() and "not found" in err_msg.lower():
                on_banner(f"Modell nicht gefunden: {err_msg}", "error")
            else:
                on_banner(f"Fehler abgefangen: {err_msg[:90]}", "warning")

            for cfg in model_configs:
                on_card_status(cfg["model_name"], "error", "Fehler")
                on_task_completed(cfg["model_name"], f"⚠️ Fehler bei der Ausführung: {err_msg}")

            on_finish(False, err_msg)

        finally:
            self.is_running = False
            self._active_callbacks = {}

    def _simulate_execution(
        self,
        model_configs: List[Dict[str, Any]],
        master_prompt: str,
        workspace_path: str,
        callbacks: Dict[str, Callable[..., None]],
        revision_feedback: Optional[str],
    ) -> None:
        """
        Simulation for automated testing when CrewAI/Ollama is not yet started.
        """
        def safe_call(func: Optional[Callable[..., None]], *args: Any, **kwargs: Any) -> None:
            if func and callable(func):
                try:
                    func(*args, **kwargs)
                except Exception as cb_err:
                    logger.debug("Simulation callback invocation exception caught: %s", cb_err)

        on_log = lambda text, tag="INFO": safe_call(callbacks.get("on_log"), text, tag)
        on_card_status = lambda name, stat, det="": safe_call(callbacks.get("on_card_status"), name, stat, det)
        on_card_thought = lambda name, chunk: safe_call(callbacks.get("on_card_thought"), name, chunk)
        on_step = lambda agent, stype, det="", tok=0: safe_call(callbacks.get("on_step"), agent, stype, det, tok)
        on_result = lambda res: safe_call(callbacks.get("on_result"), res)
        on_finish = lambda succ, msg="": safe_call(callbacks.get("on_finish"), succ, msg)
        on_task_completed = lambda name, out: safe_call(callbacks.get("on_task_completed"), name, out)

        set_active_workspace(workspace_path)
        self.accumulated_tokens = 0
        on_log("CrewAI-Simulation gestartet...", "INFO")
        time.sleep(0.5)

        pipeline_max_tokens = calculate_hardware_context_limit(
            model_configs=model_configs,
            host=self.ollama_host,
        )
        if callable(callbacks.get("on_tokens")):
            safe_call(callbacks.get("on_tokens"), 0, pipeline_max_tokens)

        for idx, cfg in enumerate(model_configs):
            if self._is_cancelled or self.stop_requested:
                on_log("[ABBRUCH] Ausführung wurde vom Benutzer abgebrochen. System ist wieder startklar.", "WARNING")
                for c in model_configs:
                    on_card_status(c["model_name"], "ready", "Bereit")
                if callable(callbacks.get("on_cancelled")):
                    safe_call(callbacks.get("on_cancelled"))
                on_finish(False, "Abgebrochen")
                return

            self.accumulated_tokens += 1250
            if callable(callbacks.get("on_tokens")):
                safe_call(callbacks.get("on_tokens"), self.accumulated_tokens, pipeline_max_tokens)

            m_name = cfg["model_name"]
            role = cfg.get("role", "Agent")
            canon_role = cfg.get("canonical_role") or get_canonical_role_key(role)
            allow_file_write = cfg.get("allow_file_write", False)

            # Task 4 Überprüfung in Simulation
            if idx == 3:
                if canon_role == "architect" or "architekt" in role.lower() or canon_role != "reviewer":
                    role = "Prüfer / Reviewer"
                    canon_role = "reviewer"
                    cfg["role"] = role
                    cfg["canonical_role"] = canon_role
                    allow_file_write = False
                    cfg["allow_file_write"] = False
            if allow_file_write:
                on_log(f"Agent '{role}' mit Datei-Schreibrechten autorisiert", "INFO")
            else:
                on_log(f"Agent '{role}' im Read-Only-Modus aktiv", "INFO")
            on_card_status(m_name, "action", "Analysiert...")
            on_log(f"[{role}] Analysiert Master-Prompt...", "AGENT")
            on_card_thought(
                m_name,
                f"🧠 <think>\nAnalysiere Kontext und Zielvorgaben für '{role}' ({canon_role})...\n"
                f"Bewerte modulare Schnittstellen und Systemintegrität.\n</think>\nStrategie festgelegt."
            )
            time.sleep(0.4)

            if self._is_cancelled or self.stop_requested:
                on_log("[ABBRUCH] Ausführung wurde vom Benutzer abgebrochen. System ist wieder startklar.", "WARNING")
                for c in model_configs:
                    on_card_status(c["model_name"], "ready", "Bereit")
                if callable(callbacks.get("on_cancelled")):
                    safe_call(callbacks.get("on_cancelled"))
                on_finish(False, "Abgebrochen")
                return

            sim_output = (
                f"### Ergebnis für {role} ({m_name})\n"
                f"- Aufgabe erfolgreich bearbeitet im Kontext von {workspace_path}.\n"
                f"- Analyse und Teilergebnis abgeschlossen."
            )
            on_task_completed(m_name, sim_output)
            on_card_status(m_name, "done", "Bereit")

        deliverable = (
            f"# CrewAI Endergebnis\n\n"
            f"**Workspace:** `{workspace_path}`\n\n"
            f"**Aufgabenstellung:**\n{master_prompt}\n\n"
            f"**Status:** Erfolgreich ausgeführt mit {len(model_configs)} Agenten."
        )
        if revision_feedback:
            deliverable += f"\n\n**Eingearbeitetes Feedback:**\n> {revision_feedback}"

        on_result(deliverable)
        on_finish(True, "Simulation abgeschlossen")
