"""Hugging Face Model Downloader & Registry for GDR-AI.
Enables downloading GGUF and local models from Hugging Face with progress tracking
and switching between Cloud (Sarvam, Claude, OpenRouter) and Local models on the fly.
"""

import os
import time
import json
import threading
import urllib.request
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

from gdr.config import load_config, save_config

logger = logging.getLogger(__name__)

MODELS_DIR = Path(os.environ.get("GDR_CONFIG_DIR", Path.home() / ".config" / "gdr")) / "models"


def ensure_models_dir() -> Path:
    """Ensure models directory exists lazily."""
    try:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return MODELS_DIR

# Curated Hugging Face Model Presets
HF_PRESETS: List[Dict[str, Any]] = [
    {
        "id": "qwen2.5-coder-1.5b",
        "name": "Qwen 2.5 Coder 1.5B (Fast & Coding)",
        "repo_id": "Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF",
        "filename": "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf",
        "url": "https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf",
        "size_mb": 986,
        "vram_req": "1.5 GB",
        "description": "Ultra-fast instruction model tailored for Python coding, shell automation, and Linux debugging."
    },
    {
        "id": "llama-3.2-1b",
        "name": "Llama 3.2 1B Instruct (Ultra Lightweight)",
        "repo_id": "bartowski/Llama-3.2-1B-Instruct-GGUF",
        "filename": "Llama-3.2-1B-Instruct-Q4_K_M.gguf",
        "url": "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf",
        "size_mb": 800,
        "vram_req": "1.0 GB",
        "description": "Meta's most compact high-speed model. Runs smoothly on any CPU or laptop without GPU."
    },
    {
        "id": "llama-3.2-3b",
        "name": "Llama 3.2 3B Instruct (Balanced Powerhouse)",
        "repo_id": "bartowski/Llama-3.2-3B-Instruct-GGUF",
        "filename": "Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        "url": "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        "size_mb": 2020,
        "vram_req": "2.8 GB",
        "description": "High general intelligence, strong reasoning, and natural conversational dialogue."
    },
    {
        "id": "qwen2.5-3b",
        "name": "Qwen 2.5 3B Instruct (Multilingual & Sharp)",
        "repo_id": "Qwen/Qwen2.5-3B-Instruct-GGUF",
        "filename": "qwen2.5-3b-instruct-q4_k_m.gguf",
        "url": "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf",
        "size_mb": 2150,
        "vram_req": "3.0 GB",
        "description": "Exceptional English, Hindi, and multilingual performance with strong logic skills."
    }
]

# Cloud Provider Catalog
CLOUD_MODELS: List[Dict[str, Any]] = [
    {
        "provider": "sarvam",
        "model_id": "sarvam-105b",
        "name": "Sarvam 105B (Flagship Indian AI)",
        "description": "Flagship 105B parameter model with deep reasoning and native Hindi/Hinglish/English fluency.",
        "requires_key": "SARVAM_API_KEY",
    },
    {
        "provider": "sarvam",
        "model_id": "sarvam-2b",
        "name": "Sarvam 2B (Ultra Fast Cloud)",
        "description": "Lightweight, low-latency cloud model for rapid queries.",
        "requires_key": "SARVAM_API_KEY",
    },
    {
        "provider": "claude",
        "model_id": "claude-3-7-sonnet-latest",
        "name": "Anthropic Claude 3.7 Sonnet (Hybrid Reasoning)",
        "description": "State-of-the-art hybrid reasoning model for advanced coding and architecture.",
        "requires_key": "ANTHROPIC_API_KEY",
    },
    {
        "provider": "claude",
        "model_id": "claude-3-5-sonnet-20241022",
        "name": "Anthropic Claude 3.5 Sonnet",
        "description": "High coding precision, document analysis, and system control.",
        "requires_key": "ANTHROPIC_API_KEY",
    },
    {
        "provider": "openrouter",
        "model_id": "meta-llama/llama-3.3-70b-instruct",
        "name": "Llama 3.3 70B (via OpenRouter)",
        "description": "70B parameter open-weight powerhouse with extensive benchmark performance.",
        "requires_key": "OPENROUTER_API_KEY",
    },
    {
        "provider": "openrouter",
        "model_id": "deepseek/deepseek-chat",
        "name": "DeepSeek V3 (via OpenRouter)",
        "description": "Fast and intelligent reasoning model.",
        "requires_key": "OPENROUTER_API_KEY",
    }
]


class ModelDownloadState:
    def __init__(self):
        self.lock = threading.Lock()
        self.status: str = "idle"  # idle | downloading | completed | error
        self.model_name: str = ""
        self.filename: str = ""
        self.downloaded_bytes: int = 0
        self.total_bytes: int = 0
        self.percent: float = 0.0
        self.speed_mb_s: float = 0.0
        self.error: Optional[str] = None
        self._cancel_flag = False

    def reset(self):
        with self.lock:
            self.status = "idle"
            self.model_name = ""
            self.filename = ""
            self.downloaded_bytes = 0
            self.total_bytes = 0
            self.percent = 0.0
            self.speed_mb_s = 0.0
            self.error = None
            self._cancel_flag = False

    def to_dict(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "status": self.status,
                "model_name": self.model_name,
                "filename": self.filename,
                "downloaded_mb": round(self.downloaded_bytes / (1024 * 1024), 1),
                "total_mb": round(self.total_bytes / (1024 * 1024), 1) if self.total_bytes > 0 else 0,
                "percent": round(self.percent, 1),
                "speed_mb": round(self.speed_mb_s, 2),
                "error": self.error,
            }


_DOWNLOAD_STATE = ModelDownloadState()


def get_download_state() -> ModelDownloadState:
    return _DOWNLOAD_STATE


def list_local_models() -> List[Dict[str, Any]]:
    """Scan MODELS_DIR for downloaded .gguf and bin files."""
    models = []
    if not MODELS_DIR.exists():
        return models

    for f in sorted(MODELS_DIR.glob("*.gguf")):
        size_mb = round(f.stat().st_size / (1024 * 1024), 1)
        models.append({
            "filename": f.name,
            "path": str(f.resolve()),
            "size_mb": size_mb,
            "modified_time": f.stat().st_mtime,
        })
    return models


def list_ollama_models() -> List[Dict[str, Any]]:
    """Query local Ollama instance for installed models if running."""
    import urllib.request
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", headers={"User-Agent": "GDR-AI"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [
                {
                    "name": m.get("name"),
                    "size_mb": round(m.get("size", 0) / (1024 * 1024), 1),
                    "modified_at": m.get("modified_at")
                }
                for m in data.get("models", [])
            ]
    except Exception:
        return []


def start_model_download(url: str, filename: str, model_name: str) -> Dict[str, Any]:
    """Initiate a background model download from Hugging Face."""
    state = get_download_state()
    with state.lock:
        if state.status == "downloading":
            return {"success": False, "error": f"Another download is already in progress: {state.model_name}"}

        state.reset()
        state.status = "downloading"
        state.model_name = model_name
        state.filename = filename

    dest_path = ensure_models_dir() / filename

    def _worker():
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 GDR-AI-ModelHub",
                    "Accept": "*/*"
                }
            )
            with urllib.request.urlopen(req, timeout=60.0) as resp:
                total_len = resp.headers.get("Content-Length")
                total_bytes = int(total_len) if total_len else 0
                with state.lock:
                    state.total_bytes = total_bytes

                downloaded = 0
                start_time = time.time()
                last_time = start_time
                last_bytes = 0

                temp_path = dest_path.with_suffix(".tmp")
                with open(temp_path, "wb") as f_out:
                    chunk_size = 512 * 1024  # 512 KB
                    while True:
                        if state._cancel_flag:
                            temp_path.unlink(missing_ok=True)
                            with state.lock:
                                state.status = "idle"
                                state.error = "Download cancelled by user."
                            return

                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f_out.write(chunk)
                        downloaded += len(chunk)

                        now = time.time()
                        if now - last_time >= 0.5:
                            speed = (downloaded - last_bytes) / (now - last_time) / (1024 * 1024)
                            last_time = now
                            last_bytes = downloaded
                            pct = (downloaded / total_bytes * 100) if total_bytes > 0 else 0
                            with state.lock:
                                state.downloaded_bytes = downloaded
                                state.percent = pct
                                state.speed_mb_s = speed

                # Rename tmp to final
                temp_path.rename(dest_path)
                with state.lock:
                    state.status = "completed"
                    state.percent = 100.0
                    state.downloaded_bytes = total_bytes or downloaded

                # Automatically register in config as default local GGUF model
                cfg = load_config()
                if "provider" not in cfg:
                    cfg["provider"] = {}
                cfg["provider"]["model_path"] = str(dest_path.resolve())
                cfg["provider"]["local_model_name"] = model_name
                save_config(cfg)
                logger.info(f"Model download completed and registered: {dest_path}")

        except Exception as e:
            logger.error(f"Error downloading model {model_name}: {e}")
            with state.lock:
                state.status = "error"
                state.error = str(e)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    return {"success": True, "message": f"Started downloading {model_name} from Hugging Face."}


def cancel_model_download():
    """Cancel the active model download."""
    state = get_download_state()
    with state.lock:
        state._cancel_flag = True
    return {"success": True}
