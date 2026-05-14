# osAfrica Development Guide

## Project Overview
osAfrica is an AI-native Linux OS. Dual-model architecture: Llama 3 8B (general) + Qwen Coder 14B/30B (code). Built on Debian Trixie.

## Build Commands

### AI Core (Python)
```bash
cd ai-core && pip install -e ".[dev]"    # Install
python -m pytest tests/ -v               # Test
python -m ruff check osa_core/ tests/    # Lint
osa-shell                                # Run AI shell
osa-routerd                              # Run router daemon
```

### System Components (C++)
```bash
cd system/osa-hwdetect && cmake -B build && cmake --build build
cd system/osa-sandbox && cmake -B build && cmake --build build
```

### ISO Build (requires Debian + root)
```bash
./scripts/build-iso.sh                   # Full ISO
./scripts/test-qemu.sh path/to.iso       # Test in QEMU
```

## Architecture
- `ai-core/` — Python: router daemon, AI shell, system agents, code intelligence
- `inference/` — llama-swap config, model management, systemd units
- `desktop/` — Wayland compositor (C), GTK4 panel (C++), terminal (C++)
- `system/` — C++ daemons: hardware detection, sandboxing, updater
- `distro/` — Debian live-build ISO config, Calamares installer, Plymouth theme

## Key Patterns
- IPC: Unix sockets with JSON-line protocol at `/run/osa/`
- AI routing: keyword classifier dispatches to Llama 3 or Qwen Coder
- Security: bubblewrap sandbox for all AI-generated commands
- Hardware tiers: 8GB/16GB/32GB/GPU auto-detected at boot
