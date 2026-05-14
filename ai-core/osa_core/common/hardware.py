"""Hardware detection for model profile selection."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GpuInfo:
    vendor: str = ""
    name: str = ""
    vram_mb: int = 0
    driver: str = ""


@dataclass
class HardwareProfile:
    total_ram_mb: int = 0
    available_ram_mb: int = 0
    cpu_cores: int = 0
    cpu_model: str = ""
    gpus: list[GpuInfo] = field(default_factory=list)
    disk_free_gb: int = 0
    tier: str = "8gb"

    @property
    def has_nvidia_gpu(self) -> bool:
        return any(g.vendor == "nvidia" for g in self.gpus)

    @property
    def best_gpu_vram_mb(self) -> int:
        return max((g.vram_mb for g in self.gpus), default=0)


def detect_ram() -> tuple[int, int]:
    try:
        with open("/proc/meminfo") as f:
            mem = {}
            for line in f:
                parts = line.split()
                if parts[0] in ("MemTotal:", "MemAvailable:"):
                    mem[parts[0].rstrip(":")] = int(parts[1]) // 1024
        return mem.get("MemTotal", 0), mem.get("MemAvailable", 0)
    except (FileNotFoundError, KeyError):
        return 0, 0


def detect_cpu() -> tuple[int, str]:
    cores = os.cpu_count() or 0
    model = ""
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    model = line.split(":", 1)[1].strip()
                    break
    except FileNotFoundError:
        pass
    return cores, model


def detect_nvidia_gpu() -> list[GpuInfo]:
    gpus = []
    if not shutil.which("nvidia-smi"):
        return gpus
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3:
                gpus.append(GpuInfo(
                    vendor="nvidia",
                    name=parts[0],
                    vram_mb=int(float(parts[1])),
                    driver=parts[2],
                ))
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass
    return gpus


def detect_disk_free(path: str = "/") -> int:
    try:
        stat = os.statvfs(path)
        return (stat.f_bavail * stat.f_frsize) // (1024 ** 3)
    except (OSError, AttributeError):
        return 0


def select_tier(profile: HardwareProfile) -> str:
    if profile.has_nvidia_gpu and profile.best_gpu_vram_mb >= 8000:
        return "gpu-nvidia"
    if profile.total_ram_mb >= 28000:
        return "32gb"
    if profile.total_ram_mb >= 14000:
        return "16gb"
    return "8gb"


def detect_hardware() -> HardwareProfile:
    total_ram, avail_ram = detect_ram()
    cores, cpu_model = detect_cpu()
    gpus = detect_nvidia_gpu()
    disk_free = detect_disk_free()

    profile = HardwareProfile(
        total_ram_mb=total_ram,
        available_ram_mb=avail_ram,
        cpu_cores=cores,
        cpu_model=cpu_model,
        gpus=gpus,
        disk_free_gb=disk_free,
    )
    profile.tier = select_tier(profile)
    return profile
