"""
Local Crew Cockpit - Model Knowledge Base
Provides extensible profiles, categories, strengths, and recommended
CrewAI roles for common local LLMs running via Ollama.
"""

import logging
import re
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)

# Knowledge dictionary mapping regex patterns to model family profiles
MODEL_FAMILIES: Dict[str, Dict[str, Any]] = {
    "qwen_coder": {
        "pattern": r"(?i)(qwen.*coder|codestral|starcoder)",
        "title": "Qwen 2.5 / 3 Coder & Code Specialists",
        "category_de": "Code-Spezialist",
        "category_en": "Code Specialist",
        "best_role": "Senior Coder",
        "desc_de": (
            "Hochspezialisiertes Coding-Modell mit überragender Syntax- und Refactoring-Genauigkeit. "
            "Exzellent bei der Erzeugung von Python-Funktionen, Fehlerbehebungen und Clean-Code-Strukturen."
        ),
        "desc_en": (
            "Highly specialized coding model with exceptional syntax and refactoring precision. "
            "Excels at generating Python code, debugging, and clean architecture implementation."
        ),
        "strengths_de": [
            "Präzise Python-Syntax & Type Annotations",
            "Effizientes Patchen bestehender Dateien",
            "Minimaler Halluzinationsgrad bei Code-Strukturen",
            "Unterstützt große Kontextfenster bis 128k",
        ],
        "strengths_en": [
            "Accurate Python syntax & type hints",
            "Precise in-place file patching",
            "Low hallucination rate in code generation",
            "Supports long context windows up to 128k",
        ],
        "context_note_de": "Natives Kontextfenster bis 128k Tokens (empfohlen: 32k - 64k)",
        "context_note_en": "Native context up to 128k tokens (recommended: 32k - 64k)",
    },
    "deepseek_r1": {
        "pattern": r"(?i)(deepseek.*r1|r1:)",
        "title": "DeepSeek R1 (Reasoning & Chain-of-Thought)",
        "category_de": "Reasoning & Systemanalyse",
        "category_en": "Reasoning & Logic",
        "best_role": "Architekt",
        "desc_de": (
            "Modernes Reasoning-Modell mit expliziter Chain-of-Thought (CoT). "
            "Perfekt für Systementwürfe, algorithmische Aufgabenteilung und knifflige Architektur-Entscheidungen."
        ),
        "desc_en": (
            "State-of-the-art reasoning model utilizing explicit Chain-of-Thought (CoT). "
            "Ideal for high-level system design, decomposing complex tasks, and architectural decisions."
        ),
        "strengths_de": [
            "Tiefgehende Problemanalyse vor der Ausführung",
            "Hervorragende logische Konsistenzprüfung",
            "Strukturierte Aufgabenaufteilung für Coder-Agenten",
        ],
        "strengths_en": [
            "In-depth problem decomposition before action",
            "High logical consistency and sanity checking",
            "Structured subtask delegation to coder agents",
        ],
        "context_note_de": "GQA-optimiert: 32k bis 64k stabil im VRAM ausführbar",
        "context_note_en": "GQA-optimized: 32k to 64k stable in VRAM",
    },
    "command_r": {
        "pattern": r"(?i)(command.*r)",
        "title": "Cohere Command-R / Command-R+",
        "category_de": "RAG & Recherche-Spezialist",
        "category_en": "RAG & Research Specialist",
        "best_role": "Rechercheur",
        "desc_de": (
            "Von Cohere speziell für Retrieval-Augmented Generation (RAG) und Tool-Use trainiert. "
            "Hervorragend geeignet zum Durchforsten von Web-Suchergebnissen und Dokumentationen."
        ),
        "desc_en": (
            "Specialized for Retrieval-Augmented Generation (RAG) and tool execution. "
            "Exceptional at synthesizing information from web searches and documentation."
        ),
        "strengths_de": [
            "Hervorragende Quellenangaben & Fakten-Treue",
            "Optimiert für Tool-Aufrufe (DuckDuckGo, Grep)",
            "Hohe Verarbeitungsgeschwindigkeit bei großen Textmengen",
        ],
        "strengths_en": [
            "Accurate source citation & factual grounding",
            "Optimized for tool utilization (DuckDuckGo, Grep)",
            "High throughput across voluminous text",
        ],
        "context_note_de": "Großes Kontextfenster bis 128k Tokens",
        "context_note_en": "Large context window up to 128k tokens",
    },
    "llama3": {
        "pattern": r"(?i)(llama3|llama-3)",
        "title": "Meta Llama 3 / 3.1 / 3.2",
        "category_de": "Allrounder & Task-Manager",
        "category_en": "General & Fast Agent",
        "best_role": "Rechercheur",
        "desc_de": (
            "Kompakter, extrem reaktionsschneller Allround-Agent. "
            "Besonders in den Größen 3B und 8B blitzschnell und ideal für schnelle Zwischenrecherchen oder Planung."
        ),
        "desc_en": (
            "Fast, highly responsive general-purpose LLM. "
            "Especially at 3B and 8B scales, ultra-fast and ideal for rapid context analysis and planning."
        ),
        "strengths_de": [
            "Extrem niedrige Latenz (Time-to-First-Token)",
            "Geringer VRAM-Footprint",
            "Ausgezeichnete Sprachkonsistenz in Deutsch und Englisch",
        ],
        "strengths_en": [
            "Ultra-low inference latency",
            "Minimal VRAM footprint",
            "Consistent bilingual performance (DE/EN)",
        ],
        "context_note_de": "16k bis 32k Tokens empfohlen",
        "context_note_en": "16k to 32k tokens recommended",
    },
    "mistral": {
        "pattern": r"(?i)(mistral|mixtral|nemo)",
        "title": "Mistral / Mistral-Nemo",
        "category_de": "Qualitätssicherung & Review",
        "category_en": "Quality Assurance & Review",
        "best_role": "Reviewer",
        "desc_de": (
            "Europäisches Spitzenmodell mit ausgewogener Argumentation und strenger Code-Prüfung. "
            "Ideal für die Rolle des Reviewers, um Sicherheitslücken und Inkonsistenzen aufzudecken."
        ),
        "desc_en": (
            "European flagship model known for balanced reasoning and rigorous validation. "
            "Ideal for QA Reviewer role to discover security flaws, inconsistencies, and edge cases."
        ),
        "strengths_de": [
            "Kritische Code- und Sicherheitsanalyse",
            "Kompakte 12B/13B Architektur mit starkem VRAM-Puffer",
            "Sehr präzise Formatierungsbefolgung",
        ],
        "strengths_en": [
            "Critical code and security auditing",
            "Compact 12B/13B architecture with healthy VRAM headroom",
            "Strict adherence to structured formatting",
        ],
        "context_note_de": "32k bis 64k Tokens stabil",
        "context_note_en": "32k to 64k tokens stable",
    },
    "phi": {
        "pattern": r"(?i)(phi4|phi3|phi-)",
        "title": "Microsoft Phi-3 / Phi-4",
        "category_de": "Kompaktes Reasoning",
        "category_en": "Compact Reasoning",
        "best_role": "Reviewer",
        "desc_de": (
            "Dicht gepacktes, synthetisch trainiertes Microsoft-Modell. "
            "Überraschend stark bei logischen Rätseln und Code-Reviews bei minimaler Modellgröße."
        ),
        "desc_en": (
            "Densely packed, synthetically trained reasoning model by Microsoft. "
            "Surpassingly capable in logical verification and code review at modest size."
        ),
        "strengths_de": [
            "Sehr geringer VRAM-Bedarf",
            "Hohe mathematische und logische Exaktheit",
        ],
        "strengths_en": [
            "Very small VRAM requirement",
            "High mathematical and logical precision",
        ],
        "context_note_de": "16k bis 32k Tokens",
        "context_note_en": "16k to 32k tokens",
    },
    "multimodal_vl": {
        "pattern": r"(?i)(qwen.*vl|llava|vision)",
        "title": "Vision-Language Multimodal Agent",
        "category_de": "Multimodal & Bildanalyse",
        "category_en": "Multimodal & Vision",
        "best_role": "Rechercheur",
        "desc_de": (
            "Verarbeitet sowohl Text als auch visuelle Artefakte (UI-Screenshots, Architektur-Diagramme). "
            "Optimal für Recherche und die Analyse grafischer Benutzeroberflächen."
        ),
        "desc_en": (
            "Processes both text and visual artifacts (UI screenshots, architecture diagrams). "
            "Optimal for research and graphical interface analysis."
        ),
        "strengths_de": [
            "Verständnis von UI-Screenshots und Flussdiagrammen",
            "Kombinierte Text- und Bildrecherche",
        ],
        "strengths_en": [
            "Understands UI screenshots and flowcharts",
            "Combined text and visual research capabilities",
        ],
        "context_note_de": "32k Tokens",
        "context_note_en": "32k tokens",
    },
    "qwen_general": {
        "pattern": r"(?i)(qwen)",
        "title": "Qwen 2.5 / 3 / 3.5 General LLM",
        "category_de": "High-Performance Allrounder",
        "category_en": "High-Performance General",
        "best_role": "Architekt",
        "desc_de": (
            "Führende Open-Weight-Modellreihe für komplexe mehrstufige Aufgaben. "
            "Kombiniert starkes Sprachverständnis, mathematische Logik und strukturierte Planung."
        ),
        "desc_en": (
            "Leading open-weight model family for multi-step enterprise workflows. "
            "Combines profound linguistic comprehension, mathematical logic, and planning."
        ),
        "strengths_de": [
            "Universell stark in Planung und Coden",
            "Hervorragende deutsche und englische Sprachausgabe",
            "Modernste GQA-Architektur für minimalen KV-Cache-Overhead",
        ],
        "strengths_en": [
            "Universally capable in planning and coding",
            "Excellent bilingual generation (German and English)",
            "Modern GQA architecture for minimal KV-cache overhead",
        ],
        "context_note_de": "Bis zu 128k Tokens",
        "context_note_en": "Up to 128k tokens",
    },
    "custom_agent": {
        "pattern": r"(?i)(5090.*agent|custom|agent)",
        "title": "Custom / Workstation Agent",
        "category_de": "Maßgeschneidertes Modell",
        "category_en": "Custom Tailored Model",
        "best_role": "Architekt",
        "desc_de": (
            "Speziell für diese Workstation optimiertes Modell für Multi-Agenten-Orchestrierung. "
            "Übernimmt idealerweise die strategische Führung der Crew."
        ),
        "desc_en": (
            "Workstation-optimized custom model designed for multi-agent orchestration. "
            "Best suited for leading the crew as Architect or Planner."
        ),
        "strengths_de": [
            "Optimal auf die lokale Hardware abgestimmt",
            "Hoher Durchsatz im VRAM",
            "Fokus auf deterministische Agentenschritte",
        ],
        "strengths_en": [
            "Optimized for local host hardware",
            "High throughput in VRAM",
            "Focus on deterministic agent execution",
        ],
        "context_note_de": "32k bis 64k Tokens empfohlen",
        "context_note_en": "32k to 64k tokens recommended",
    },
}


def get_model_profile(model_name: str, lang: str = "de") -> Dict[str, Any]:
    """
    Returns an informative knowledge profile for a given Ollama model name.

    Args:
        model_name: The tag or name of the model (e.g. 'qwen2.5-coder:32b', 'deepseek-r1:70b').
        lang: Preferred language ('de' or 'en', default: 'de').

    Returns:
        Dictionary containing:
            - 'title': Readable title
            - 'category': Category string
            - 'desc': In-depth description
            - 'best_role': Recommended CrewAI role ('Senior Coder', 'Architekt', 'Rechercheur', 'Reviewer')
            - 'strengths': List of strength bullet points
            - 'context_note': Context recommendation
    """
    selected_lang = lang.lower() if lang in ("de", "en") else "de"
    clean_name = model_name.strip()

    # Search through predefined model families by pattern
    for family_key, data in MODEL_FAMILIES.items():
        pattern = data.get("pattern", "")
        if pattern and re.search(pattern, clean_name):
            cat_key = f"category_{selected_lang}"
            desc_key = f"desc_{selected_lang}"
            strengths_key = f"strengths_{selected_lang}"
            ctx_key = f"context_note_{selected_lang}"

            return {
                "title": data.get("title", clean_name),
                "category": data.get(cat_key, data.get("category_de", "General LLM")),
                "desc": data.get(desc_key, data.get("desc_de", "")),
                "best_role": data.get("best_role", "Senior Coder"),
                "strengths": data.get(strengths_key, []),
                "context_note": data.get(ctx_key, "32k Tokens empfohlen"),
            }

    # Heuristic fallback for unknown or experimental models
    best_role = "Senior Coder"
    lower_name = clean_name.lower()
    if any(k in lower_name for k in ("review", "qa", "eval", "judge", "guard")):
        best_role = "Reviewer"
    elif any(k in lower_name for k in ("plan", "arch", "lead", "think", "reason")):
        best_role = "Architekt"
    elif any(k in lower_name for k in ("search", "rag", "find", "web", "doc")):
        best_role = "Rechercheur"

    cat_str = "Allgemeines LLM" if selected_lang == "de" else "General LLM"
    desc_str = (
        f"Lokales Sprachmodell '{clean_name}'. Einsatzbereit für allgemeine Text- und Code-Verarbeitung."
        if selected_lang == "de"
        else f"Local model '{clean_name}'. Ready for general text and code orchestration."
    )

    return {
        "title": clean_name,
        "category": cat_str,
        "desc": desc_str,
        "best_role": best_role,
        "strengths": [
            "Vollständig lokale Ausführung ohne Cloud-Abhängigkeit",
            "Standard-Kompatibilität mit Ollama",
        ] if selected_lang == "de" else [
            "100% local execution without cloud dependencies",
            "Full compatibility with Ollama REST runtime",
        ],
        "context_note": "16k - 32k Tokens",
    }


# Cache for detected tool-calling capabilities to prevent repeated HTTP calls
_CAN_USE_TOOLS_CACHE: Dict[str, bool] = {}

# Known models that should NEVER have tool write access (pure reasoning / vision / base)
NON_TOOL_PATTERNS = [
    r"(?i)vl",          # Excludes qwen2.5vl, qwen-vl, any model with 'vl'
    r"(?i)vision",      # Excludes llama3.2-vision, etc.
    r"(?i)llava",       # Excludes llava, bakllava
    r"(?i)bakllava",
    r"(?i)r1",          # Excludes deepseek-r1, r1, etc.
    r"(?i)-base\b",
]

# Known tool-calling and coding models that reliably support function calling
VERIFIED_TOOL_PATTERNS = [
    r"(?i)qwen.*coder",
    r"(?i)qwen2\.5",
    r"(?i)qwen3",
    r"(?i)llama3(\.1|\.2|\.3)?",
    r"(?i)llama-3(\.1|\.2|\.3)?",
    r"(?i)mistral-nemo",
    r"(?i)mistral-small",
    r"(?i)codestral",
    r"(?i)command-r",
]
TOOL_CAPABLE_PATTERNS = VERIFIED_TOOL_PATTERNS


def can_use_tools(model_name: str, host: str = "http://localhost:11434") -> bool:
    """
    Automatically detects whether a local Ollama model reliably supports function calling /
    tool usage (and is thus safe for disk file creation/modification).
    Strictly excludes models with vision ('vl', 'vision', 'llava') and pure reasoning ('r1').
    Only verified tool models (e.g. qwen2.5-coder, qwen2.5 without vl, llama3.1, llama3.2,
    mistral-nemo, command-r) return True.

    Args:
        model_name: Exact tag or name of the model (e.g. 'qwen2.5-coder:14b', 'deepseek-r1:8b').
        host: Ollama daemon host URL.

    Returns:
        True if the model safely supports function calling / file write tools, False otherwise.
    """
    clean_name = model_name.strip()
    if not clean_name:
        return False

    if clean_name in _CAN_USE_TOOLS_CACHE:
        return _CAN_USE_TOOLS_CACHE[clean_name]

    lower_name = clean_name.lower()

    # 1. Hard exclusions: Any model with 'vl', 'vision', 'llava', 'bakllava', or 'r1' in its name
    # Vision models and pure reasoning models cannot reliably use tools in Ollama and lead to HTTP 400
    if any(k in lower_name for k in ("vl", "vision", "llava", "bakllava", "r1")):
        _CAN_USE_TOOLS_CACHE[clean_name] = False
        return False

    for pat in NON_TOOL_PATTERNS:
        if re.search(pat, clean_name):
            _CAN_USE_TOOLS_CACHE[clean_name] = False
            return False

    # 2. Only verified tool models return True
    for pat in VERIFIED_TOOL_PATTERNS:
        if re.search(pat, clean_name):
            _CAN_USE_TOOLS_CACHE[clean_name] = True
            return True

    # Default fallback: False (read-only by default for safety)
    _CAN_USE_TOOLS_CACHE[clean_name] = False
    return False


THINKING_PATTERNS = [
    r"(?i)deepseek.*r1",
    r"(?i)\br1\b",
    r"(?i)qwq",
    r"(?i)reasoner",
    r"(?i)\bo1\b",
    r"(?i)marco-o1",
]


def has_thinking_mode(model_name: str) -> bool:
    """
    Determines if a model uses explicit reasoning / chain-of-thought mode
    emitting dedicated <think>...</think> blocks (e.g. DeepSeek-R1, QwQ).

    Args:
        model_name: Exact tag or name of the model.

    Returns:
        True if the model emits explicit thinking streams, False otherwise.
    """
    clean_name = model_name.strip()
    if not clean_name:
        return False
    for pat in THINKING_PATTERNS:
        if re.search(pat, clean_name):
            return True
    return False


def estimate_model_vram_gb(model_name: str) -> float:
    """
    Estimates typical VRAM footprint in GB for a 4-bit quantized Ollama model
    based on parsed parameter scale or known model family sizes.
    """
    clean = model_name.strip().lower()
    m = re.search(r":(\d+(?:\.\d+)?)b\b", clean)
    if m:
        params = float(m.group(1))
        return round(params * 0.75 + 1.5, 1)

    if ":3b" in clean:
        return 3.5
    if ":7b" in clean or ":8b" in clean:
        return 7.5
    if ":14b" in clean or ":12b" in clean:
        return 12.0
    if ":32b" in clean or ":27b" in clean:
        return 24.0
    if ":70b" in clean:
        return 48.0
    return 6.0


def get_model_specs(model_name: str, host: str = "http://localhost:11434") -> Dict[str, Any]:
    """
    Provides comprehensive capability specs for an Ollama model:
    VRAM requirement, tool support, thinking mode, suggested role, and category.

    Args:
        model_name: Exact tag or name of the model.
        host: Ollama daemon host URL.

    Returns:
        Dictionary containing vram_gb, can_use_tools, has_thinking, title, category, best_role, etc.
    """
    profile = get_model_profile(model_name)
    tool_ok = can_use_tools(model_name, host=host)
    thinking_ok = has_thinking_mode(model_name)
    vram_req = estimate_model_vram_gb(model_name)

    return {
        "model_name": model_name,
        "vram_gb": vram_req,
        "can_use_tools": tool_ok,
        "has_thinking": thinking_ok,
        "title": profile.get("title", model_name),
        "category": profile.get("category", "General LLM"),
        "best_role": profile.get("best_role", "Senior Coder"),
        "context_note": profile.get("context_note", "32k Tokens"),
        "strengths": profile.get("strengths", []),
    }


def get_capability_badge(model_name: str, host: str = "http://localhost:11434") -> Dict[str, str]:
    """
    Returns visual capability badge metadata:
    - Vision models: [👁️ Vision] (Orange/Brown)
    - Tool-capable: [🔧 Tools & Write] (Green)
    - Reasoning-capable: [🧠 Reasoning] (Cyan/Blue)
    - General text / chat: [📝 Text / Chat] (Gray)
    """
    lower = model_name.strip().lower()
    if any(k in lower for k in ("vl", "vision", "llava", "bakllava")):
        return {
            "text": "👁️ Vision",
            "type": "vision",
            "bg": "#451a03",
            "fg": "#fed7aa",
            "border": "#f97316",
            "tooltip": "Multimodales Vision-Modell (Bildverarbeitung, kein Tool-Calling).",
        }
    elif can_use_tools(model_name, host=host):
        return {
            "text": "🔧 Tools & Write",
            "type": "tool",
            "bg": "#14532d",
            "fg": "#86efac",
            "border": "#16a34a",
            "tooltip": "Unterstützt Function Calling, Web-Recherche und Dateizugriff (Read/Write).",
        }
    elif has_thinking_mode(model_name) or "r1" in lower:
        return {
            "text": "🧠 Reasoning",
            "type": "reasoning",
            "bg": "#082f49",
            "fg": "#38bdf8",
            "border": "#0284c7",
            "tooltip": "Reines Reasoning-/Chain-of-Thought Modell (Read-Only, ideal für Architektur & Analyse).",
        }
    else:
        return {
            "text": "📝 Text / Chat",
            "type": "text",
            "bg": "#1e293b",
            "fg": "#94a3b8",
            "border": "#334155",
            "tooltip": "Allgemeines Sprachmodell für Textgenerierung und Chat (Read-Only).",
        }


def get_role_recommendation_badge(model_name: str, host: str = "http://localhost:11434") -> Dict[str, str]:
    """
    Returns role recommendation badge for model pool:
    - Coder models ('coder' in name): [💻 Coder]
    - Reasoning models ('r1', 'o1' in name): [🧠 Architekt / Review]
    - Tool/Research models: [🔍 Rechercheur]
    - Fallback: [📋 Assistent]
    """
    lower = model_name.strip().lower()
    if "coder" in lower or "codestral" in lower or "starcoder" in lower:
        return {
            "text": "💻 Coder",
            "type": "coder",
            "bg": "#1e3a5f",
            "fg": "#93c5fd",
            "border": "#2563eb",
            "tooltip": "Empfohlene Rolle: Senior-Entwickler / Code-Implementierung.",
        }
    elif "r1" in lower or "o1" in lower or "qwq" in lower or "reason" in lower:
        return {
            "text": "🧠 Architekt / Review",
            "type": "architect",
            "bg": "#3b1e54",
            "fg": "#d8b4fe",
            "border": "#9333ea",
            "tooltip": "Empfohlene Rolle: Architekt, Planer oder Code-Reviewer.",
        }
    elif can_use_tools(model_name, host=host) or any(k in lower for k in ("search", "find", "web", "doc")):
        return {
            "text": "🔍 Rechercheur",
            "type": "researcher",
            "bg": "#134e4a",
            "fg": "#5eead4",
            "border": "#0d9488",
            "tooltip": "Empfohlene Rolle: Rechercheur mit Web- und Dateianalyse-Werkzeugen.",
        }
    else:
        return {
            "text": "📋 Assistent",
            "type": "assistant",
            "bg": "#1e293b",
            "fg": "#cbd5e1",
            "border": "#475569",
            "tooltip": "Empfohlene Rolle: Allgemeiner Projekt-Assistent.",
        }



