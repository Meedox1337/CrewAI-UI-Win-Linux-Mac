"""
Local Crew Cockpit - System & VRAM Monitor Module
High-performance real-time memory monitoring for NVIDIA GPUs, Apple Silicon Unified Memory,
and CPU/RAM fallbacks, with dynamic KV-cache token budget calculations for local LLMs.
"""

import logging
import platform
import sys
import time
from typing import Any, Dict, Optional

import psutil
from PyQt6.QtCore import QThread, pyqtSignal

# Safe, crash-resilient import of pynvml (NVIDIA Management Library)
try:
    import pynvml
    PYNVML_AVAILABLE = True
except (ImportError, Exception):
    pynvml = None  # type: ignore
    PYNVML_AVAILABLE = False

logger = logging.getLogger(__name__)


class SystemMonitor:
    """
    Manages low-overhead, thread-safe hardware memory queries.
    Supports NVIDIA NVML, Apple Silicon Unified Memory, and generic CPU/RAM.
    """

    def __init__(self) -> None:
        self.nvml_initialized: bool = False
        self.gpu_handle: Optional[Any] = None
        self.gpu_device_name: Optional[str] = None
        self._init_nvml()

    def _init_nvml(self) -> None:
        """Attempts to initialize NVML if pynvml is installed and an NVIDIA GPU exists."""
        if not PYNVML_AVAILABLE:
            return

        # Do not use NVML on macOS
        if platform.system() == "Darwin":
            return

        try:
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            if device_count > 0:
                # Default to primary GPU (device 0)
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                raw_name = pynvml.nvmlDeviceGetName(handle)
                # Handle bytes vs str across pynvml versions cleanly
                device_name = raw_name.decode("utf-8") if isinstance(raw_name, bytes) else str(raw_name)

                self.gpu_handle = handle
                self.gpu_device_name = device_name
                self.nvml_initialized = True
                logger.info("NVML initialized successfully with GPU: %s", device_name)
            else:
                self.nvml_initialized = False
        except Exception as exc:
            # Handles driver not loaded, library not found, or non-NVIDIA environments
            logger.debug("NVML initialization bypassed or failed: %s", exc)
            self.nvml_initialized = False
            self.gpu_handle = None
            self.gpu_device_name = None

    def get_memory_status(self) -> Dict[str, Any]:
        """
        Retrieves real-time memory usage metrics.
        Returns a stable dictionary:
            {
                "device_name": str,
                "total_gb": float,
                "used_gb": float,
                "free_gb": float,
                "is_gpu": bool
            }
        """
        # 1. Primary: NVIDIA GPU via pynvml (Windows / Linux)
        if self.nvml_initialized and self.gpu_handle is not None and platform.system() != "Darwin":
            try:
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(self.gpu_handle)
                total_gb = round(mem_info.total / (1024.0 ** 3), 2)
                used_gb = round(mem_info.used / (1024.0 ** 3), 2)
                free_gb = round(mem_info.free / (1024.0 ** 3), 2)

                return {
                    "device_name": self.gpu_device_name or "NVIDIA GPU",
                    "total_gb": total_gb,
                    "used_gb": used_gb,
                    "free_gb": free_gb,
                    "is_gpu": True,
                }
            except Exception as exc:
                logger.warning("Failed reading NVML memory info (%s). Re-initializing...", exc)
                self.nvml_initialized = False
                self._init_nvml()

        # 2. Fallback 1: macOS Apple Silicon / Darwin Unified Memory
        current_os = platform.system()
        vm = psutil.virtual_memory()

        if current_os == "Darwin":
            is_arm = platform.machine().lower() in ("arm64", "aarch64")
            device_name = (
                "Apple Silicon Unified Memory"
                if is_arm
                else "Apple Mac System-RAM"
            )
            total_gb = round(vm.total / (1024.0 ** 3), 2)
            used_gb = round(vm.used / (1024.0 ** 3), 2)
            free_gb = round(vm.available / (1024.0 ** 3), 2)

            return {
                "device_name": device_name,
                "total_gb": total_gb,
                "used_gb": used_gb,
                "free_gb": free_gb,
                "is_gpu": is_arm,  # Apple Silicon unified memory directly powers GPU shaders
            }

        # 3. Fallback 2: Generic Host System RAM (Windows / Linux ohne NVML)
        total_gb = round(vm.total / (1024.0 ** 3), 2)
        used_gb = round(vm.used / (1024.0 ** 3), 2)
        free_gb = round(vm.available / (1024.0 ** 3), 2)

        return {
            "device_name": f"System-RAM ({platform.processor() or 'CPU'})",
            "total_gb": total_gb,
            "used_gb": used_gb,
            "free_gb": free_gb,
            "is_gpu": False,
        }

    def shutdown(self) -> None:
        """Releases NVML driver handles safely."""
        if self.nvml_initialized and PYNVML_AVAILABLE:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass
            self.nvml_initialized = False


# Module-level singleton instance for zero-allocation recurring queries
_MONITOR_INSTANCE = SystemMonitor()


def get_memory_status() -> Dict[str, Any]:
    """
    Public API: Returns the current memory status dictionary.
    Guaranteed schema:
        {"device_name": str, "total_gb": float, "used_gb": float, "free_gb": float, "is_gpu": bool}
    """
    return _MONITOR_INSTANCE.get_memory_status()


def calculate_token_budget(
    model_size_gb: float,
    free_vram_gb: float,
    requested_ctx: int = 32768,
) -> Dict[str, Any]:
    """
    Calculates the dynamic KV-cache memory requirement and token budget
    for GQA-optimized modern LLMs (e.g., Qwen 2.5, DeepSeek, Llama 3).

    Formula Basis:
      - KV cache requirement rule of thumb: ~0.6 MB to 0.8 MB VRAM per 1,000 context tokens.
      - Rechnerischer Cache-Bedarf = (requested_ctx / 1000) * 0.0007 GB.
      - Remaining buffer after model weights = buffer_gb = free_vram_gb - model_size_gb.

    Status-Ampel:
      - 'green': Genug freier VRAM für vollen Kontext (buffer_gb >= cache_needed).
      - 'yellow': Knapper VRAM, Kontext belegt mehr als 75% des Puffers.
      - 'red': VRAM-Überlauf (OOM-Gefahr / RAM-Offloading droht).

    Args:
        model_size_gb: Weights size of the model in GB (e.g. 5.0 for 8B Q4, 18.0 for 32B Q4).
        free_vram_gb: Currently free VRAM or available host memory in GB.
        requested_ctx: Desired context length in tokens (default: 32,768).

    Returns:
        Dictionary with status ('green', 'yellow', 'red'), readable status_text,
        and numeric breakdown (model_size_gb, free_vram_gb, buffer_gb,
        cache_needed_gb, requested_ctx, recommended_max_tokens, can_fit_full).
    """
    KV_FACTOR_PER_1K = 0.0007  # GB per 1,000 tokens

    # Defensive type conversions
    model_size_gb = max(0.0, float(model_size_gb))
    free_vram_gb = max(0.0, float(free_vram_gb))
    requested_ctx = max(512, int(requested_ctx))

    # Rechnerischer Cache-Bedarf in GB
    cache_needed_gb = round((requested_ctx / 1000.0) * KV_FACTOR_PER_1K, 4)

    # Verbleibender Puffer nach Abzug des Modells
    buffer_gb = round(free_vram_gb - model_size_gb, 4)

    ctx_k = requested_ctx // 1024

    # 1. Fall: Modell selbst passt nicht in den freien VRAM
    if buffer_gb <= 0.0:
        status = "red"
        can_fit_full = False
        recommended_max_tokens = 0
        deficit_gb = abs(buffer_gb)
        status_text = (
            f"Kritisch: VRAM unzureichend für Modell ({model_size_gb:.1f} GB bei {free_vram_gb:.1f} GB frei, "
            f"Defizit: {deficit_gb:.1f} GB). OOM / RAM-Offload droht!"
        )

    # 2. Fall: Modell passt, aber Kontext übersteigt den Puffer (VRAM-Überlauf)
    elif buffer_gb < cache_needed_gb:
        status = "red"
        can_fit_full = False
        # Maximaler stabiler Kontext, der ohne Überlauf in den Puffer passt
        raw_max = int((buffer_gb / KV_FACTOR_PER_1K) * 1000.0)
        recommended_max_tokens = max(0, (raw_max // 1024) * 1024)
        rec_k = recommended_max_tokens // 1024
        status_text = (
            f"Kritisch: VRAM-Überlauf droht ({cache_needed_gb:.3f} GB Cache nötig, {buffer_gb:.3f} GB frei). "
            f"Warnung: Max {rec_k}k empfohlen."
        )

    # 3. Fall: Kontext belegt mehr als 75% des verfügbaren Puffers
    elif cache_needed_gb > (0.75 * buffer_gb):
        status = "yellow"
        can_fit_full = True
        # Empfohlenes sicheres Limit auf Basis von 75% Pufferbelegung
        safe_cache_gb = buffer_gb * 0.75
        raw_max = int((safe_cache_gb / KV_FACTOR_PER_1K) * 1000.0)
        recommended_max_tokens = max(1024, (raw_max // 1024) * 1024)
        rec_k = recommended_max_tokens // 1024
        pct = (cache_needed_gb / buffer_gb) * 100.0 if buffer_gb > 0 else 100.0
        status_text = (
            f"Warnung: VRAM knapp ({pct:.0f}% des Puffers belegt). "
            f"Warnung: Max {rec_k}k empfohlen."
        )

    # 4. Fall: Ausreichend freier VRAM für vollen Kontext (green)
    else:
        status = "green"
        can_fit_full = True
        raw_max = int((buffer_gb / KV_FACTOR_PER_1K) * 1000.0)
        recommended_max_tokens = max(requested_ctx, (raw_max // 1024) * 1024)
        status_text = f"Ausreichend für {ctx_k}k (Puffer: {buffer_gb:.1f} GB frei)."

    return {
        "status": status,
        "status_text": status_text,
        "model_size_gb": model_size_gb,
        "free_vram_gb": free_vram_gb,
        "buffer_gb": buffer_gb,
        "cache_needed_gb": cache_needed_gb,
        "requested_ctx": requested_ctx,
        "recommended_max_tokens": recommended_max_tokens,
        "can_fit_full": can_fit_full,
    }


class SystemMonitorThread(QThread):
    """
    Asynchronous Qt background worker decoupling Ollama health checks and
    hardware VRAM/RAM metrics from the PyQt GUI thread completely.
    Polls in a dedicated loop (2.0s interval) and emits passive Qt signals:
    - status_updated(is_online: bool)
    - vram_updated(used_gb: float, total_gb: float, percent: int)
    """

    status_updated = pyqtSignal(bool)
    vram_updated = pyqtSignal(float, float, int)

    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        interval: float = 2.0,
        parent: Optional[Any] = None,
    ) -> None:
        super().__init__(parent)
        self.ollama_host = ollama_host.rstrip("/")
        self.interval = max(0.5, float(interval))
        self._running = True

    def run(self) -> None:
        import requests
        session = requests.Session()

        while self._running:
            # 1. Ollama connectivity check in background thread
            is_online = False
            try:
                url = f"{self.ollama_host}/api/tags"
                res = session.get(url, timeout=(1.0, 1.5))
                is_online = (res.status_code == 200)
            except Exception:
                is_online = False

            if not self._running:
                break
            self.status_updated.emit(is_online)

            # 2. VRAM / RAM metrics query in background thread
            try:
                mem = get_memory_status()
                used = float(mem.get("used_gb", 0.0))
                total = float(mem.get("total_gb", 0.0))
                pct = int((used / total * 100.0) if total > 0 else 0)
                if not self._running:
                    break
                self.vram_updated.emit(used, total, pct)
            except Exception as exc:
                logger.debug("VRAM background query: %s", exc)

            # High-resolution sleep enabling prompt thread shutdown
            steps = max(1, int(self.interval / 0.1))
            for _ in range(steps):
                if not self._running:
                    break
                time.sleep(0.1)

        try:
            session.close()
        except Exception:
            pass

    def stop(self) -> None:
        """Gracefully halts the monitor thread."""
        self._running = False
        self.wait(1000)
