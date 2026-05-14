"""First-run setup wizard — configures osAfrica on first boot.

Detects hardware, selects model quantization, downloads models,
and configures inference services.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

BANNER = """\033[1;32m
╔═══════════════════════════════════════════════════════╗
║                                                       ║
║          Welcome to osAfrica Setup                    ║
║          AI-Native Linux Operating System             ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
\033[0m"""

MARKER = Path("/etc/osa/.setup-complete")
HARDWARE_PROFILE = Path("/etc/osa/hardware-profile.json")
MODEL_DIR = Path("/opt/osa/models")
CONFIG_DIR = Path("/etc/osa")


def detect_hardware() -> dict:
    hw = {"ram_gb": 0, "cpu_cores": 0, "gpu": None, "tier": "8gb"}

    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    hw["ram_gb"] = round(kb / 1024 / 1024, 1)
                    break
    except FileNotFoundError:
        pass

    hw["cpu_cores"] = os.cpu_count() or 1

    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(",")
            hw["gpu"] = {"name": parts[0].strip(), "vram_mb": int(parts[1].strip().split()[0])}
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    ram = hw["ram_gb"]
    if hw["gpu"]:
        hw["tier"] = "gpu-nvidia"
    elif ram >= 28:
        hw["tier"] = "32gb"
    elif ram >= 14:
        hw["tier"] = "16gb"
    else:
        hw["tier"] = "8gb"

    return hw


TIER_CONFIGS = {
    "8gb": {
        "description": "8GB RAM — Llama 3 8B only (Q4_K_S)",
        "models": [
            {"name": "llama3-8b", "file": "llama-3-8b-instruct-q4_k_s.gguf",
             "url": "https://huggingface.co/QuantFactory/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_S.gguf",
             "size_gb": 4.3},
        ],
        "concurrent": False,
    },
    "16gb": {
        "description": "16GB RAM — Llama 3 8B + Qwen Coder 14B (swap mode)",
        "models": [
            {"name": "llama3-8b", "file": "llama-3-8b-instruct-q4_k_m.gguf",
             "url": "https://huggingface.co/QuantFactory/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf",
             "size_gb": 4.9},
            {"name": "qwen-coder-14b", "file": "qwen2.5-coder-14b-instruct-q4_k_m.gguf",
             "url": "https://huggingface.co/Qwen/Qwen2.5-Coder-14B-Instruct-GGUF/resolve/main/qwen2.5-coder-14b-instruct-q4_k_m.gguf",
             "size_gb": 8.5},
        ],
        "concurrent": False,
    },
    "32gb": {
        "description": "32GB+ RAM — Llama 3 8B + Qwen Coder 30B (concurrent)",
        "models": [
            {"name": "llama3-8b", "file": "llama-3-8b-instruct-q4_k_m.gguf",
             "url": "https://huggingface.co/QuantFactory/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf",
             "size_gb": 4.9},
            {"name": "qwen-coder-30b", "file": "qwen2.5-coder-32b-instruct-q4_k_m.gguf",
             "url": "https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct-GGUF/resolve/main/qwen2.5-coder-32b-instruct-q4_k_m.gguf",
             "size_gb": 18.5},
        ],
        "concurrent": True,
    },
    "gpu-nvidia": {
        "description": "NVIDIA GPU detected — Llama 3 8B + Qwen Coder (GPU accelerated)",
        "models": [
            {"name": "llama3-8b", "file": "llama-3-8b-instruct-q4_k_m.gguf",
             "url": "https://huggingface.co/QuantFactory/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf",
             "size_gb": 4.9},
            {"name": "qwen-coder-14b", "file": "qwen2.5-coder-14b-instruct-q4_k_m.gguf",
             "url": "https://huggingface.co/Qwen/Qwen2.5-Coder-14B-Instruct-GGUF/resolve/main/qwen2.5-coder-14b-instruct-q4_k_m.gguf",
             "size_gb": 8.5},
        ],
        "concurrent": True,
    },
}


def print_hardware(hw: dict):
    print(f"\033[1mHardware detected:\033[0m")
    print(f"  RAM:  {hw['ram_gb']} GB")
    print(f"  CPU:  {hw['cpu_cores']} cores")
    if hw["gpu"]:
        print(f"  GPU:  {hw['gpu']['name']} ({hw['gpu']['vram_mb']} MB VRAM)")
    else:
        print(f"  GPU:  None (CPU-only inference)")
    print(f"  Tier: {hw['tier']}")
    print()


def prompt_choice(question: str, options: list[str], default: int = 0) -> int:
    print(f"\033[1m{question}\033[0m")
    for i, opt in enumerate(options):
        marker = " >" if i == default else "  "
        print(f"  {marker} [{i + 1}] {opt}")
    while True:
        try:
            raw = input(f"\n  Choice [{default + 1}]: ").strip()
            if not raw:
                return default
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return idx
        except (ValueError, EOFError):
            pass
        print("  Invalid choice, try again.")


def download_model(model: dict) -> bool:
    dest = MODEL_DIR / model["file"]
    if dest.exists():
        print(f"  ✓ {model['name']} already downloaded")
        return True

    print(f"  Downloading {model['name']} ({model['size_gb']} GB)...")
    try:
        result = subprocess.run(
            ["wget", "-q", "--show-progress", "-O", str(dest), model["url"]],
            timeout=7200,
        )
        if result.returncode == 0:
            print(f"  ✓ {model['name']} downloaded")
            return True
        else:
            print(f"  ✗ Download failed for {model['name']}")
            dest.unlink(missing_ok=True)
            return False
    except subprocess.TimeoutExpired:
        print(f"  ✗ Download timed out for {model['name']}")
        dest.unlink(missing_ok=True)
        return False


def save_hardware_profile(hw: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(HARDWARE_PROFILE, "w") as f:
        json.dump(hw, f, indent=2)
    print(f"  Saved hardware profile to {HARDWARE_PROFILE}")


def prompt_safety_level() -> str:
    idx = prompt_choice(
        "Default safety level for AI command execution?",
        [
            "normal — confirm destructive commands, auto-allow safe ones (recommended)",
            "safe — confirm ALL commands before execution",
            "expert — auto-execute everything (use with caution)",
        ],
        default=0,
    )
    return ["normal", "safe", "expert"][idx]


def main():
    if MARKER.exists():
        print("osAfrica setup already completed. To re-run: sudo rm /etc/osa/.setup-complete")
        sys.exit(0)

    print(BANNER)

    hw = detect_hardware()
    print_hardware(hw)

    tier_config = TIER_CONFIGS[hw["tier"]]
    print(f"\033[1mSelected profile:\033[0m {tier_config['description']}\n")

    override = prompt_choice(
        "Use this profile?",
        ["Yes, use detected profile", "No, let me choose manually"],
        default=0,
    )

    if override == 1:
        tiers = list(TIER_CONFIGS.keys())
        labels = [TIER_CONFIGS[t]["description"] for t in tiers]
        chosen = prompt_choice("Select profile:", labels)
        hw["tier"] = tiers[chosen]
        tier_config = TIER_CONFIGS[hw["tier"]]
        print()

    save_hardware_profile(hw)

    safety = prompt_safety_level()
    print(f"\n  Safety level: {safety}\n")

    download = prompt_choice(
        "Download AI models now?",
        [
            f"Yes, download now ({sum(m['size_gb'] for m in tier_config['models']):.1f} GB total)",
            "No, download later (AI features won't work until models are downloaded)",
        ],
        default=0,
    )

    if download == 0:
        print()
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        for model in tier_config["models"]:
            download_model(model)
        print()

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    MARKER.touch()

    print("\033[1;32m")
    print("  ╔═══════════════════════════════════════╗")
    print("  ║    osAfrica setup complete!            ║")
    print("  ║    Reboot or start osa-shell to begin. ║")
    print("  ╚═══════════════════════════════════════╝")
    print("\033[0m")


if __name__ == "__main__":
    main()
