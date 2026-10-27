**Language / Sprache:** [🇬🇧 English](README.md) | [🇩🇪 Deutsch](README.de.md)

---

# Local Crew Cockpit (PyQt6)

> **Production-ready, local multi-agent orchestration without cloud lock-in.**  
> [![GitHub Profile](https://img.shields.io/badge/Developer-Medox1337-1e293b?style=flat-square&logo=github&logoColor=white)](https://github.com/Meedox1337?tab=repositories)

---

## 1. Authorship & Technology Stack

* **UI & Architecture Design:** [**Medox1337**](https://github.com/Meedox1337?tab=repositories)  
  Fully decoupled, modular PyQt6/PySide6 desktop cockpit with responsive multi-threading, tabular model pool, pipeline cards, and non-blocking real-time hardware telemetry.
* **Core Agent Framework:** **[CrewAI](https://github.com/crewAIInc/crewAI)**  
  Structured role delegation (`Agent`), goal-driven task assignment (`Task`), and deterministic pipeline control with synchronous and asynchronous execution.
* **Local Inference & Model Backend:** **[Ollama](https://github.com/ollama/ollama)**  
  Purely local LLM inference over standardized REST/HTTP endpoints (`/api/tags`, `/api/pull`, `/api/chat`, `/api/generate`). 100% data sovereignty and offline operation.
* **Real-Time Hardware Telemetry:** **NVIDIA Management Library (NVML / pynvml)**  
  Direct polling of physical total, used, and free VRAM as well as GPU utilization in dedicated background threads without impacting the Qt event loop.

---

## 2. Core Architecture & Workflow (How It Works)

### Multi-Model Pipeline (Heterogeneous Specialist Team)
The cockpit breaks away from homogeneous single-model setups: Each stage in the sequential pipeline can be assigned a dedicated local LLM specialized for the task at hand:
* **Architecture, Planning & Code Audit:** Reasoning models (e.g., `deepseek-r1:14b`, `deepseek-r1:32b`, `deepseek-r1:70b`) analyze requirements, identify edge cases, and formulate architectural blueprints.
* **Code Generation & Refactoring:** Programming powerhouses (e.g., `qwen2.5-coder:14b`, `qwen2.5-coder:32b`, `starcoder2`) implement features and patches cleanly into source code.
* **Research, Documentation & QA:** Broad-capability general models (e.g., `mistral-nemo:12b`, `llama3.3:70b`, `llama3.1:8b`) handle documentation, test generation, and web research.

### Dynamic Context Window (Hardware-Adaptive `num_ctx`)
Instead of rigid or arbitrary limits (such as standard 2k or 4k token windows), the cockpit dynamically computes the maximum safe context window prior to workflow execution:
1. Detects physically installed GPU VRAM via NVML (`vram_total_gb`).
2. Identifies the most memory-intensive model in the selected team (`max_model_size_gb`).
3. Computes the remaining safe memory buffer for KV-cache and GPU headroom:
   $$\text{Headroom} = \text{VRAM}_{\text{total}} - \text{Model Size} - \text{Safety Buffer (2.5 GB)}$$
4. Hardware-agnostic allocation:
   * **Entry- & Mid-Range Hardware (< 16 GB VRAM):** Conservative context windows between 4,096 and 16,384 tokens to prevent CUDA Out-of-Memory crashes.
   * **High-End Hardware (24 GB to 32 GB VRAM, e.g., RTX 3090/4090/5090):** Automatically unlocks 65,536 to 131,072 tokens (`64k` / `128k`), explicitly passed to Ollama via `num_ctx` during LLM initialization.

### Tool-Calling & Auto-Execute Sandbox
Agents interact directly and safely with the project workspace:
* **Isolated Workspace Sandbox:** All write and patch operations (`file_write_tool`, `file_patch_tool`, `file_grep_tool`, `file_read_tool`) validate target paths via `os.path.commonpath`. Any unauthorized path traversal outside the project directory is blocked immediately.
* **Surgical Patching:** Targeted code snippet replacements via `file_patch_tool` significantly reduce token consumption compared to full file rewrites.
* **Fallback Parsing for Text Tool-Calls:** When models (especially reasoning models) emit tool invocations as raw JSON text blocks (`{"name": "file_write_tool", ...}`) instead of native API tool-calls, the runner automatically extracts parameters and physically executes the file operation inside the workspace.

### Resource Lifecycle & Zero-Leak Reset
To prevent persistent VRAM allocation or memory fragmentation after task completion or cancellation:
* All active Ollama connections and streams are properly finalized upon pipeline completion.
* An explicit unload with `keep_alive: 0` can be triggered to release VRAM back to the OS.
* Worker threads are cleanly terminated (`quit()` with a timeout fallback to `terminate()`), resetting UI buttons instantly.

---

## 3. Installation & Quickstart

### Prerequisites
* **Operating System:** Windows 10/11 (64-bit), Linux, or macOS.
* **Python:** Python 3.10 or 3.11 recommended.
* **GPU & Drivers:** NVIDIA GPU with up-to-date NVIDIA drivers (for NVML VRAM telemetry).
* **Ollama:** Installed and running in the background ([ollama.com](https://ollama.com)).

### Step-by-Step Setup

1. **Clone the repository or open project directory:**
   ```bash
   git clone https://github.com/Meedox1337/LocalCrewCockpit.git
   cd LocalCrewCockpit
   ```

2. **Create & activate a virtual Python environment:**
   ```bash
   # Windows PowerShell / CMD
   python -m venv venv
   .\venv\Scripts\activate

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the Ollama daemon:**
   Ensure the local Ollama instance is active:
   ```bash
   ollama serve
   ```
   *(Pre-pull recommended models, e.g., `ollama pull qwen2.5-coder:14b` and `ollama pull deepseek-r1:14b`)*

5. **Launch the Local Crew Cockpit:**
   ```bash
   python main.py
   ```

---

## 4. Streaming Tracking & Model Management

The cockpit features an integrated Model Pool management system in Zone 1:
* **Background Remote Update Check:** Compares local SHA256 digests via HEAD/GET requests against the Ollama Registry (`https://registry.ollama.ai/v2/...`). When an update is detected, the button displays `⚡ Update available`.
* **Live Streaming Progress:** JSON chunk streams are parsed in real time during downloads:
  * In the UI: Row button dynamically updates to `⏳ 45% (10.0 GB)`.
  * In Terminal: Interactive console progress bar with transfer rate and ETA:
    ```text
    [PULL] qwen2.5-coder:14b:  45%|████▍     | 10.0G/22.2G [01:23<01:45, 115MB/s]
    ```
  * In Live Log: Periodic progress logs every 10% and completion banner `[SUCCESS] Modell '...' vollständig geladen und einsatzbereit.`

---

## 5. Developer & Debugging Guide (Py-Debugging & CLI)

For developers, prompt engineers, and troubleshooting, the cockpit provides a dedicated, comprehensive debug mode.

### Activating Debug Mode
Launch the cockpit with the CLI flag `--debug`:
```bash
python main.py --debug
```
Or set the environment variable `COCKPIT_DEBUG=1`:
```powershell
# PowerShell
$env:COCKPIT_DEBUG="1"
python main.py

# CMD
set COCKPIT_DEBUG=1
python main.py

# Linux / macOS
export COCKPIT_DEBUG=1
python3 main.py
```

On startup, the cockpit prints an explicit confirmation:
```text
[DEBUG-MODE AKTIV] Detaillierte Fehlerprotokollierung eingeschaltet.
```

### Diagnostics & Real-Time Telemetry
In debug mode, the console outputs:
1. **Ollama HTTP REST Events:**
   Inspects all request URLs, headers, payloads (`/api/pull`, `/api/tags`, `/api/show`, `/api/delete`), and chunk responses.
2. **Tool Payloads & Sandboxing:**
   Full capture of arguments passed into tools (`file_path`, `content_len`, `pattern`) as well as their return values.
3. **CrewAI Step & Callback Tracking:**
   Granular logging of task state changes, thoughts, and token usage increments.
4. **Complete Python Tracebacks:**
   Any unhandled exception in background worker threads or tool calls prints the complete call stack with file names and line numbers.

### Troubleshooting & Best Practices

| Symptom / Problem | Root Cause | Solution |
| :--- | :--- | :--- |
| **`Connection refused` / Offline** | Ollama daemon is not running on port 11434. | Start `ollama serve` in a separate terminal and click `Reload Models`. |
| **`CUDA out of memory`** | Model weights combined with KV-cache exceed physical GPU VRAM. | Choose a more compact quantization (e.g. `q4_K_M` instead of `q8_0`) or close memory-heavy background applications. |
| **Agent simulates tool-calls as text** | Smaller models (< 7B) may not reliably emit native function-calling tokens. | The built-in text fallback parser captures and executes the file call automatically. For native function calling, `qwen2.5-coder:14b` or higher is recommended. |
| **NVML deprecation warning** | Warning message from older `pynvml` packages. | Harmless; caught internally by the system monitor. Optionally upgrade to `nvidia-ml-py`. |

---

## 6. Project Structure

```text
CrewAI/
├── core/
│   ├── crew_runner.py        # CrewAI orchestration, task queue & hardware context calculation
│   ├── logger.py             # Central logging engine (--debug & payload tracing)
│   ├── model_knowledge.py    # VRAM estimates, capability & role matrix
│   ├── ollama_client.py      # Async REST client, registry checks & streaming pull
│   ├── system_monitor.py     # NVML GPU & VRAM background monitor thread
│   ├── tools.py              # Sandboxed file, patch, grep & web search tools
│   └── locales.py            # Localization dictionaries (DE / EN)
├── ui/
│   ├── components/
│   │   ├── model_pool_widget.py   # Zone 1: Tabular model pool & update status
│   │   ├── pipeline_widget.py     # Zone 2: Role-based agent pipeline & reordering
│   │   ├── workspace_widget.py    # Zone 3: Master task prompt & workspace file tree
│   │   ├── system_dock.py         # Hardware telemetry dock (VRAM, RAM, CPU)
│   │   └── log_dock.py            # Live activity log & terminal console
│   ├── main_window.py        # Main PyQt6 window coordinator
│   └── pipeline_card.py      # Agent card component with live thought drawer
├── main.py                   # Application entry point & theme initialization
├── requirements.txt          # Python package dependencies
├── README.md                 # English main documentation
└── README.de.md              # German documentation
```

---

## 7. License & Usage

Designed for transparent, privacy-first, high-performance orchestration of local large language models in modern software development workflows. Free for local research, prototyping, and development.
