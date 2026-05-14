.PHONY: setup test lint clean build-iso

# Development
setup:
	./scripts/dev-setup.sh

test:
	cd ai-core && python -m pytest tests/ -v

lint:
	cd ai-core && python -m ruff check osa_core/ tests/

format:
	cd ai-core && python -m ruff format osa_core/ tests/

# Run services (dev mode)
router:
	cd ai-core && python -m osa_core.router.router_daemon

shell:
	cd ai-core && python -m osa_core.shell.osa_shell

# Build
build-hwdetect:
	cd system/osa-hwdetect && cmake -B build && cmake --build build

# ISO (Phase 2)
build-iso:
	cd distro/live-build && sudo lb build

clean:
	cd ai-core && rm -rf build/ dist/ *.egg-info __pycache__
	cd system/osa-hwdetect && rm -rf build/
	cd distro/live-build && sudo lb clean 2>/dev/null || true
