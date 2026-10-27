"""
Local Crew Cockpit - Ollama REST API Client
Provides low-latency health checks, model catalog inspection,
streaming model pull with precise update detection, interactive CMD progress bar,
Qt progress signals, and model deletion.
"""

import hashlib
import json
import logging
import sys
import time
from typing import Any, Callable, Dict, List, Optional
import requests
from PyQt6.QtCore import QObject, pyqtSignal

from core.logger import is_debug, log_http_event

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_CONNECT_TIMEOUT = 1.5
DEFAULT_READ_TIMEOUT = 3.0


class OllamaClient(QObject):
    """
    Client for interacting with local Ollama daemon REST endpoints.
    Inherits from QObject to provide thread-safe Qt signals for live
    streaming progress and activity logging.
    """

    progress_updated = pyqtSignal(str, int, float, float)  # model_name, percent, completed_gb, total_gb
    log_emitted = pyqtSignal(str, str)  # message, level

    def __init__(self, host: str = DEFAULT_OLLAMA_HOST, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.host = host.rstrip("/")

    def check_status(self, timeout: float = DEFAULT_CONNECT_TIMEOUT) -> bool:
        """
        Checks whether the local Ollama instance is running and reachable.
        Queries the root endpoint or '/api/tags' with a short timeout.
        """
        url = f"{self.host}/api/tags"
        try:
            response = requests.get(url, timeout=(timeout, timeout))
            log_http_event(url, "GET", None, response.status_code)
            return response.status_code == 200
        except (requests.RequestException, Exception) as exc:
            if is_debug():
                logger.debug("Ollama status check failed on %s: %s", self.host, exc, exc_info=True)
            else:
                logger.debug("Ollama status check failed on %s: %s", self.host, exc)
            return False

    def get_installed_models(self, timeout: float = DEFAULT_READ_TIMEOUT) -> List[Dict[str, Any]]:
        """
        Retrieves the list of locally pulled/installed models from Ollama.
        Queries '/api/tags'.
        """
        url = f"{self.host}/api/tags"
        try:
            response = requests.get(url, timeout=(DEFAULT_CONNECT_TIMEOUT, timeout))
            log_http_event(url, "GET", None, response.status_code)
            if response.status_code != 200:
                logger.warning("Ollama /api/tags responded with status %s", response.status_code)
                return []

            data = response.json()
            raw_models = data.get("models", [])
            normalized_models: List[Dict[str, Any]] = []

            for m in raw_models:
                size_bytes = m.get("size", 0)
                size_gb = round(size_bytes / (1024.0 ** 3), 2)
                details = m.get("details", {})

                normalized_models.append({
                    "name": m.get("name", "unknown"),
                    "digest": m.get("digest", ""),
                    "size_gb": size_gb,
                    "size_bytes": size_bytes,
                    "modified_at": m.get("modified_at", ""),
                    "format": details.get("format", ""),
                    "family": details.get("family", ""),
                    "parameter_size": details.get("parameter_size", ""),
                    "quantization_level": details.get("quantization_level", ""),
                    "raw": m,
                })

            normalized_models.sort(key=lambda x: x["name"].lower())
            return normalized_models

        except (requests.RequestException, Exception) as exc:
            if is_debug():
                logger.warning("Could not fetch installed Ollama models: %s", exc, exc_info=True)
            else:
                logger.warning("Could not fetch installed Ollama models: %s", exc)
            return []

    def pull_model_stream(
        self,
        model_name: str,
        callback: Optional[Callable[[str, int, int], None]] = None,
        timeout: float = 600.0,
    ) -> str:
        """
        Pulls/downloads an Ollama model using streaming JSON.
        Differentiates between actual new data download and verifying existing layers.
        Emits progress_updated Qt signal and renders an interactive CMD progress bar.

        Args:
            model_name: Name/tag of model, e.g. "qwen2.5-coder:14b".
            callback: Callable accepting (status: str, completed: int, total: int).
            timeout: Max idle timeout during stream chunks.

        Returns:
            "updated" if new layers were downloaded,
            "up_to_date" if model was already current and no new bytes were fetched,
            "" (empty string) on failure.
        """
        url = f"{self.host}/api/pull"
        payload = {"name": model_name, "stream": True}
        log_http_event(url, "POST", payload)

        had_new_download = False
        last_logged_milestone = -1
        start_time = time.time()
        last_bar_draw_time = 0.0
        bar_closed = False

        try:
            response = requests.post(
                url,
                json=payload,
                stream=True,
                timeout=(DEFAULT_CONNECT_TIMEOUT, timeout),
            )
            log_http_event(url, "POST", payload, status_code=response.status_code)

            if response.status_code != 200:
                logger.error("Failed to initiate pull for %s: HTTP %s", model_name, response.status_code)
                if callback:
                    callback(f"Error: HTTP {response.status_code}", 0, 0)
                return ""

            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line.decode("utf-8"))
                    if is_debug():
                        logger.debug("Ollama pull event chunk: %s", chunk)

                    status_text = chunk.get("status", "")
                    completed = chunk.get("completed", 0)
                    total = chunk.get("total", 0)

                    # Check if actual download activity happened
                    if completed > 0 or "downloading" in status_text.lower():
                        had_new_download = True

                    if total > 0 and completed >= 0:
                        completed_gb = completed / (1024.0 ** 3)
                        total_gb = total / (1024.0 ** 3)
                        percent = min(100, max(0, int((completed / total) * 100)))

                        # 1. Emit Qt signal to UI
                        self.progress_updated.emit(model_name, percent, completed_gb, total_gb)

                        # 2. Draw interactive CMD progress bar
                        # Example: [PULL] {model_name}:  45%|████▍     | 10.0G/22.2G [01:23<01:45, 115MB/s]
                        elapsed = time.time() - start_time
                        speed_bps = completed / elapsed if elapsed > 0.05 else 0.0
                        speed_mb = speed_bps / (1024.0 * 1024.0)
                        speed_str = f"{speed_mb:.0f}MB/s" if speed_mb < 1024.0 else f"{speed_mb / 1024.0:.1f}GB/s"
                        elapsed_str = time.strftime("%M:%S", time.gmtime(elapsed))
                        remaining_sec = (total - completed) / speed_bps if speed_bps > 0 else 0.0
                        eta_str = time.strftime("%M:%S", time.gmtime(remaining_sec))

                        bar_length = 10
                        filled = (bar_length * percent) / 100.0
                        full_blocks = int(filled)
                        fraction = filled - full_blocks
                        block_chars = ["", "▏", "▎", "▍", "▌", "▋", "▊", "▉"]
                        part_char = block_chars[int(fraction * 8)] if full_blocks < bar_length else ""
                        empty_len = max(0, bar_length - full_blocks - (1 if part_char else 0))
                        bar = "█" * full_blocks + part_char + " " * empty_len

                        bar_line = (
                            f"\r[PULL] {model_name}: {percent:>3}%|{bar}| "
                            f"{completed_gb:.1f}G/{total_gb:.1f}G [{elapsed_str}<{eta_str}, {speed_str}]"
                        )

                        now = time.time()
                        if now - last_bar_draw_time >= 0.08 or percent == 100:
                            try:
                                sys.stdout.write(bar_line)
                                sys.stdout.flush()
                            except Exception:
                                pass
                            last_bar_draw_time = now

                        # 3. Sende alle 10% eine dezente Statuszeile an das Live-Aktivitätslog der UI
                        milestone = percent // 10
                        if milestone > last_logged_milestone and percent > 0 and percent <= 100:
                            last_logged_milestone = milestone
                            status_msg = f"[DOWNLOAD] '{model_name}': {percent}% ({completed_gb:.1f} / {total_gb:.1f} GB)"
                            self.log_emitted.emit(status_msg, "INFO")

                    if callback:
                        callback(status_text, completed, total)

                    if status_text.lower() == "success":
                        if not bar_closed:
                            try:
                                sys.stdout.write("\n")
                                print(f"[SUCCESS] Download für '{model_name}' erfolgreich abgeschlossen.")
                                sys.stdout.flush()
                            except Exception:
                                pass
                            bar_closed = True
                        return "updated" if had_new_download else "up_to_date"

                    if "error" in chunk:
                        err_msg = chunk.get("error", "Unknown error")
                        if not bar_closed:
                            try:
                                sys.stdout.write("\n")
                            except Exception:
                                pass
                            bar_closed = True
                        logger.error("Ollama pull error for %s: %s", model_name, err_msg)
                        if callback:
                            callback(f"Error: {err_msg}", 0, 0)
                        return ""

                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue

            if not bar_closed:
                try:
                    sys.stdout.write("\n")
                    if had_new_download:
                        print(f"[SUCCESS] Download für '{model_name}' erfolgreich abgeschlossen.")
                    sys.stdout.flush()
                except Exception:
                    pass
                bar_closed = True

            return "updated" if had_new_download else "up_to_date"

        except (requests.RequestException, Exception) as exc:
            if not bar_closed:
                try:
                    sys.stdout.write("\n")
                except Exception:
                    pass
                bar_closed = True
            if is_debug():
                logger.error("Exception during streaming pull of model %s: %s", model_name, exc, exc_info=True)
            else:
                logger.error("Exception during streaming pull of model %s: %s", model_name, exc)
            if callback:
                callback(f"Connection error: {exc}", 0, 0)
            return ""

    def delete_model(self, model_name: str, timeout: float = 10.0) -> bool:
        """
        Deletes a model from local Ollama storage via DELETE /api/delete.

        Args:
            model_name: Exact name/tag of model to delete.
            timeout: Request timeout in seconds.

        Returns:
            True if HTTP 200, False otherwise.
        """
        url = f"{self.host}/api/delete"
        payload = {"name": model_name}
        log_http_event(url, "DELETE", payload)
        try:
            response = requests.delete(
                url,
                json=payload,
                timeout=(DEFAULT_CONNECT_TIMEOUT, timeout),
            )
            log_http_event(url, "DELETE", payload, status_code=response.status_code)
            return response.status_code == 200
        except (requests.RequestException, Exception) as exc:
            if is_debug():
                logger.error("Failed to delete model %s on %s: %s", model_name, self.host, exc, exc_info=True)
            else:
                logger.error("Failed to delete model %s on %s: %s", model_name, self.host, exc)
            return False

    def get_model_digest(self, model_name: str) -> Optional[str]:
        """
        Retrieves the local SHA256 digest of an installed model.
        Queries /api/tags or /api/show.
        """
        try:
            url = f"{self.host}/api/tags"
            resp = requests.get(url, timeout=(DEFAULT_CONNECT_TIMEOUT, 2.5))
            log_http_event(url, "GET", None, status_code=resp.status_code)
            if resp.status_code == 200:
                clean_target = model_name.strip().lower()
                for m in resp.json().get("models", []):
                    m_name = (m.get("name") or "").strip().lower()
                    if (
                        m_name == clean_target
                        or m_name.startswith(clean_target + ":")
                        or clean_target.startswith(m_name + ":")
                        or m_name == clean_target.split(":")[0]
                    ):
                        d = m.get("digest", "")
                        if d:
                            return d
        except Exception as exc:
            if is_debug():
                logger.debug("Could not retrieve digest for %s: %s", model_name, exc, exc_info=True)
            else:
                logger.debug("Could not retrieve digest for %s: %s", model_name, exc)
        return None

    def check_model_update(self, model_name: str, local_digest: Optional[str] = None) -> bool:
        """
        Checks whether a newer model manifest exists on the Ollama registry.
        1. Queries local digest via /api/tags if not provided.
        2. Sends GET to https://registry.ollama.ai/v2/{library}/{name}/manifests/{tag}.
        3. Compares header 'docker-content-digest' or manifest sha256 to local digest.
        4. Returns True if a newer remote digest exists, False otherwise.
        Silently catches network errors (timeout/offline) and returns False.
        """
        try:
            clean_name = model_name.strip()
            if not clean_name:
                return False

            if not local_digest:
                local_digest = self.get_model_digest(clean_name)
            if not local_digest:
                return False

            parts = clean_name.split(":")
            name_part = parts[0].strip()
            tag = parts[1].strip() if len(parts) > 1 else "latest"

            if "/" in name_part:
                path = name_part
            else:
                path = f"library/{name_part}"

            url = f"https://registry.ollama.ai/v2/{path}/manifests/{tag}"
            headers = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}
            log_http_event(url, "GET", headers)

            resp = requests.get(url, headers=headers, timeout=(DEFAULT_CONNECT_TIMEOUT, 3.5))
            log_http_event(url, "GET", headers, status_code=resp.status_code)
            if resp.status_code != 200:
                return False

            d = resp.headers.get("docker-content-digest")
            if d:
                remote_digest = d.replace("sha256:", "").strip()
            else:
                remote_digest = hashlib.sha256(resp.content).hexdigest()

            clean_local = local_digest.replace("sha256:", "").strip()
            has_update = bool(clean_local and remote_digest and clean_local.lower() != remote_digest.lower())
            if is_debug():
                logger.debug("Model update check for %s: local=%s, remote=%s, has_update=%s", clean_name, clean_local, remote_digest, has_update)
            return has_update

        except Exception as exc:
            if is_debug():
                logger.debug("Silently caught error checking update for %s: %s", model_name, exc, exc_info=True)
            else:
                logger.debug("Silently caught error checking update for %s: %s", model_name, exc)
            return False

    def delete_model(self, model_name: str, timeout: float = 10.0) -> bool:
        """
        Deletes a model from the local Ollama storage.
        Sends a DELETE request to /api/delete with JSON body {"name": model_name}.
        Returns True if deletion succeeded (HTTP 200), False otherwise.
        """
        clean_name = model_name.strip()
        if not clean_name:
            return False

        url = f"{self.host}/api/delete"
        payload = {"name": clean_name}
        try:
            log_http_event(url, "DELETE", payload=payload)
            response = requests.delete(
                url,
                json=payload,
                timeout=(DEFAULT_CONNECT_TIMEOUT, timeout),
            )
            log_http_event(url, "DELETE", payload=payload, status_code=response.status_code)
            if response.status_code == 200:
                logger.info("Successfully deleted model '%s' via Ollama API.", clean_name)
                self.log_emitted.emit(
                    f"[INFO] Modell '{clean_name}' erfolgreich von der Festplatte gelöscht.",
                    "INFO",
                )
                return True
            else:
                logger.warning(
                    "Failed to delete model '%s': status code %s (%s)",
                    clean_name,
                    response.status_code,
                    response.text,
                )
                self.log_emitted.emit(
                    f"[FEHLER] Löschen von '{clean_name}' fehlgeschlagen (HTTP {response.status_code}).",
                    "ERROR",
                )
                return False
        except Exception as exc:
            if is_debug():
                logger.error("Exception deleting model '%s': %s", clean_name, exc, exc_info=True)
            else:
                logger.error("Exception deleting model '%s': %s", clean_name, exc)
            self.log_emitted.emit(
                f"[FEHLER] Verbindungsfehler beim Löschen von '{clean_name}': {exc}",
                "ERROR",
            )
            return False


# Module-level convenience functions matching specification


def check_ollama_status(host: str = DEFAULT_OLLAMA_HOST) -> bool:
    """Prüft die Erreichbarkeit des lokalen Ollama-Servers."""
    return OllamaClient(host=host).check_status()


def get_installed_models(host: str = DEFAULT_OLLAMA_HOST) -> List[Dict[str, Any]]:
    """Ruft '/api/tags' ab und gibt Modellname, Größe in GB sowie Metadaten zurück."""
    return OllamaClient(host=host).get_installed_models()


def pull_model_stream(
    model_name: str,
    callback: Optional[Callable[[str, int, int], None]] = None,
    host: str = DEFAULT_OLLAMA_HOST,
) -> str:
    """
    Führt POST auf '/api/pull' mit stream=True aus und liefert:
    - 'updated', wenn neue Layer geladen wurden
    - 'up_to_date', wenn das Modell bereits auf dem neuesten Stand war
    - '', wenn ein Fehler aufgetreten ist.
    """
    return OllamaClient(host=host).pull_model_stream(model_name=model_name, callback=callback)


def delete_model(model_name: str, host: str = DEFAULT_OLLAMA_HOST) -> bool:
    """
    Sendet einen DELETE-Request an den Ollama-Endpunkt /api/delete mit JSON {"name": model_name}.
    Gibt True bei Erfolg (HTTP 200) oder False bei Fehlern zurück.
    """
    return OllamaClient(host=host).delete_model(model_name=model_name)


def check_model_update(
    model_name: str,
    host: str = DEFAULT_OLLAMA_HOST,
    local_digest: Optional[str] = None,
) -> bool:
    """Prüft über die Ollama-Registry, ob für ein Modell ein Update verfügbar ist."""
    return OllamaClient(host=host).check_model_update(model_name=model_name, local_digest=local_digest)
