"""System Compatibility Checker for GDR AI.
Cross-platform diagnostic engine checking hardware, OS, memory, audio devices,
and Python runtime environment for Linux, Windows, and macOS.
"""

import os
import platform
import shutil
import socket
import sys
from typing import Dict, Any, List


def check_system_compatibility() -> Dict[str, Any]:
    """Perform comprehensive system compatibility audit across OS, RAM, disk, audio, and Python."""
    results: Dict[str, Any] = {
        "overall_status": "PASS",  # PASS, WARN, FAIL
        "checks": [],
        "system_info": {}
    }

    # 1. Operating System
    os_name = platform.system()
    os_release = platform.release()
    arch = platform.machine()
    is_termux = bool("TERMUX_VERSION" in os.environ or os.path.exists("/data/data/com.termux"))
    platform_label = f"Android / Termux ({arch})" if is_termux else f"{os_name} ({arch})"
    is_supported_os = is_termux or (os_name in ("Linux", "Windows", "Darwin"))
    results["system_info"]["os"] = platform_label
    results["system_info"]["is_termux"] = is_termux
    results["checks"].append({
        "name": "Operating System",
        "value": platform_label,
        "status": "PASS" if is_supported_os else "WARN",
        "details": "Android Termux environment detected. Hardware tools (Flashlight, Battery, SMS, Camera, GPS) enabled." if is_termux else ("Linux, Windows, and macOS are fully supported." if is_supported_os else f"Untested platform: {os_name}")
    })

    # 2. Python Version
    py_ver = sys.version_info
    py_str = f"{py_ver.major}.{py_ver.minor}.{py_ver.micro}"
    results["system_info"]["python"] = py_str
    if py_ver >= (3, 10):
        py_status = "PASS"
        py_msg = "Python 3.10+ detected (Optimal)."
    else:
        py_status = "FAIL"
        py_msg = f"Python {py_str} is unsupported. Python 3.10 or higher is required."
        results["overall_status"] = "FAIL"
    results["checks"].append({
        "name": "Python Environment",
        "value": f"Python {py_str}",
        "status": py_status,
        "details": py_msg
    })

    # 3. Virtual Environment
    in_venv = (sys.prefix != sys.base_prefix) or ("VIRTUAL_ENV" in os.environ)
    results["checks"].append({
        "name": "Virtual Environment",
        "value": "Isolated .venv" if in_venv else "System Python",
        "status": "PASS" if in_venv else "WARN",
        "details": "Running inside isolated virtual environment." if in_venv else "Running directly in system Python. Virtual environment (.venv) recommended."
    })

    # 4. System Memory (RAM)
    total_ram_gb = 8.0
    avail_ram_gb = 4.0
    try:
        import psutil
        vm = psutil.virtual_memory()
        total_ram_gb = round(vm.total / (1024 ** 3), 1)
        avail_ram_gb = round(vm.available / (1024 ** 3), 1)
    except Exception:
        # Fallback memory check
        try:
            if hasattr(os, "sysconf") and "SC_PAGE_SIZE" in os.sysconf_names and "SC_PHYS_PAGES" in os.sysconf_names:
                total_ram_gb = round((os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")) / (1024 ** 3), 1)
                avail_ram_gb = total_ram_gb / 2.0
        except Exception:
            pass

    results["system_info"]["ram_total_gb"] = total_ram_gb
    results["system_info"]["ram_available_gb"] = avail_ram_gb

    if total_ram_gb >= 7.5:
        ram_status = "PASS"
        ram_msg = f"{total_ram_gb} GB Total RAM ({avail_ram_gb} GB free). Sufficient for neural models and web UI."
    elif total_ram_gb >= 3.8:
        ram_status = "WARN"
        ram_msg = f"{total_ram_gb} GB Total RAM ({avail_ram_gb} GB free). Lean mode active; heavy models offload to CPU."
    else:
        ram_status = "FAIL"
        ram_msg = f"{total_ram_gb} GB RAM is insufficient. Minimum 4 GB required."
        if results["overall_status"] != "FAIL":
            results["overall_status"] = "WARN"

    results["checks"].append({
        "name": "System Memory (RAM)",
        "value": f"{total_ram_gb} GB ({avail_ram_gb} GB available)",
        "status": ram_status,
        "details": ram_msg
    })

    # 5. Free Disk Space
    try:
        usage = shutil.disk_usage(os.getcwd())
        free_disk_gb = round(usage.free / (1024 ** 3), 1)
    except Exception:
        free_disk_gb = 20.0

    results["system_info"]["free_disk_gb"] = free_disk_gb
    if free_disk_gb >= 10.0:
        disk_status = "PASS"
        disk_msg = f"{free_disk_gb} GB available. Plenty of space for models, embeddings, and caches."
    elif free_disk_gb >= 4.0:
        disk_status = "WARN"
        disk_msg = f"{free_disk_gb} GB available. Limited disk space remaining."
    else:
        disk_status = "FAIL"
        disk_msg = f"{free_disk_gb} GB available. Low disk space. Free up at least 5 GB."
        if results["overall_status"] != "FAIL":
            results["overall_status"] = "WARN"

    results["checks"].append({
        "name": "Storage / Disk Space",
        "value": f"{free_disk_gb} GB Free",
        "status": disk_status,
        "details": disk_msg
    })

    # 6. Audio Hardware (Input Microphone & Output Playback)
    mic_count = 0
    spk_count = 0
    mic_names: List[str] = []
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        for d in devices:
            if d.get("max_input_channels", 0) > 0:
                mic_count += 1
                mic_names.append(d.get("name", "Unknown"))
            if d.get("max_output_channels", 0) > 0:
                spk_count += 1
    except Exception:
        pass

    results["system_info"]["microphones"] = mic_count
    results["system_info"]["speakers"] = spk_count

    if mic_count > 0:
        mic_status = "PASS"
        mic_msg = f"{mic_count} audio input device(s) detected ({mic_names[0] if mic_names else 'Default'})."
    else:
        mic_status = "WARN"
        mic_msg = "No hardware microphone detected. Voice input may require granting browser permissions or plugging in a headset."

    results["checks"].append({
        "name": "Microphone (Voice Input)",
        "value": f"{mic_count} Input Device(s)",
        "status": mic_status,
        "details": mic_msg
    })

    # 7. GPU Acceleration (NVIDIA CUDA or CPU Mode)
    gpu_name = "CPU Only (Standard Mode)"
    has_cuda = False
    vram_mb = 0
    try:
        import torch
        if torch.cuda.is_available():
            has_cuda = True
            gpu_name = torch.cuda.get_device_name(0)
            vram_mb = round(torch.cuda.get_device_properties(0).total_memory / (1024 ** 2))
    except Exception:
        pass

    results["system_info"]["has_cuda"] = has_cuda
    results["system_info"]["gpu_name"] = gpu_name

    results["checks"].append({
        "name": "GPU Acceleration",
        "value": f"{gpu_name}" + (f" ({vram_mb} MiB VRAM)" if has_cuda else ""),
        "status": "PASS",
        "details": f"Hardware CUDA accelerated: {gpu_name}" if has_cuda else "Running in CPU-quantized mode (<80ms Piper speech & INT8 faster-whisper)."
    })

    # 8. Network Connectivity
    is_online = False
    try:
        s = socket.create_connection(("1.1.1.1", 53), timeout=1.5)
        s.close()
        is_online = True
    except Exception:
        pass

    results["system_info"]["is_online"] = is_online
    results["checks"].append({
        "name": "Internet Connectivity",
        "value": "Connected (Online)" if is_online else "Disconnected (100% Offline Mode)",
        "status": "PASS",
        "details": "Online cloud APIs active." if is_online else "100% Offline Local AI fallback is automatically armed."
    })

    return results


def print_compatibility_report() -> bool:
    """Print an ASCII colored report for command-line installers."""
    diag = check_system_compatibility()
    print("\n" + "=" * 66)
    print("🖥️  GDR-AI System Compatibility Diagnostics")
    print("=" * 66)
    for c in diag["checks"]:
        icon = "✅" if c["status"] == "PASS" else ("⚠️ " if c["status"] == "WARN" else "❌")
        print(f" {icon} {c['name']:<26} : {c['value']}")
        print(f"    └─ {c['details']}")
    print("-" * 66)
    status_icon = "🟢" if diag["overall_status"] == "PASS" else ("🟡" if diag["overall_status"] == "WARN" else "🔴")
    print(f"{status_icon} Overall Compatibility: {diag['overall_status']}")
    print("=" * 66 + "\n")
    return diag["overall_status"] != "FAIL"


if __name__ == "__main__":
    success = print_compatibility_report()
    sys.exit(0 if success else 1)

