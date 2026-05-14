"""Tests for hardware detection and tier selection."""

import sys

from osa_core.common.hardware import HardwareProfile, GpuInfo, select_tier


class TestTierSelection:
    def test_8gb_tier(self):
        profile = HardwareProfile(total_ram_mb=8000)
        assert select_tier(profile) == "8gb"

    def test_16gb_tier(self):
        profile = HardwareProfile(total_ram_mb=16000)
        assert select_tier(profile) == "16gb"

    def test_32gb_tier(self):
        profile = HardwareProfile(total_ram_mb=32000)
        assert select_tier(profile) == "32gb"

    def test_gpu_tier(self):
        profile = HardwareProfile(
            total_ram_mb=16000,
            gpus=[GpuInfo(vendor="nvidia", name="RTX 4060", vram_mb=8000)],
        )
        assert select_tier(profile) == "gpu-nvidia"

    def test_gpu_low_vram_uses_ram_tier(self):
        profile = HardwareProfile(
            total_ram_mb=16000,
            gpus=[GpuInfo(vendor="nvidia", name="GTX 1050", vram_mb=4000)],
        )
        assert select_tier(profile) == "16gb"

    def test_has_nvidia_property(self):
        profile = HardwareProfile(
            gpus=[GpuInfo(vendor="nvidia", vram_mb=8000)]
        )
        assert profile.has_nvidia_gpu is True

    def test_no_nvidia_property(self):
        profile = HardwareProfile(gpus=[])
        assert profile.has_nvidia_gpu is False

    def test_best_vram(self):
        profile = HardwareProfile(
            gpus=[
                GpuInfo(vendor="nvidia", vram_mb=8000),
                GpuInfo(vendor="nvidia", vram_mb=16000),
            ]
        )
        assert profile.best_gpu_vram_mb == 16000
