#!/usr/bin/env bash
set -euo pipefail

# Build the osAfrica ISO image.
# Must be run on Debian/Ubuntu with live-build installed.
# Requires root (sudo) for chroot operations.

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$REPO_ROOT/distro/live-build"

echo "=== osAfrica ISO Builder ==="
echo "Build dir: $BUILD_DIR"
echo ""

# Check dependencies
for cmd in lb debootstrap; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "Error: $cmd not found. Install with:"
        echo "  sudo apt install live-build debootstrap"
        exit 1
    fi
done

# Build AI core Python package
echo "[1/4] Building AI core package..."
cd "$REPO_ROOT/ai-core"
pip install build -q 2>/dev/null || true
python -m build -q 2>/dev/null || echo "  (Python build skipped — will install from source)"

# Build C++ system components
echo "[2/4] Building system components..."
for component in osa-hwdetect osa-sandbox; do
    if [ -d "$REPO_ROOT/system/$component" ]; then
        cd "$REPO_ROOT/system/$component"
        cmake -B build -DCMAKE_BUILD_TYPE=Release 2>/dev/null || echo "  ($component skipped — missing deps)"
        cmake --build build -j "$(nproc)" 2>/dev/null || true
    fi
done

# Configure live-build
echo "[3/4] Configuring live-build..."
cd "$BUILD_DIR"
chmod +x auto/*
lb clean 2>/dev/null || true
lb config

# Copy osAfrica files into the chroot overlay
OVERLAY="$BUILD_DIR/config/includes.chroot"
mkdir -p "$OVERLAY/usr/local/bin"
mkdir -p "$OVERLAY/etc/osa"
mkdir -p "$OVERLAY/etc/systemd/system"
mkdir -p "$OVERLAY/opt/osa/models"
mkdir -p "$OVERLAY/opt/osa-core"
mkdir -p "$OVERLAY/usr/share/osa/session"
mkdir -p "$OVERLAY/usr/share/osa/skel"
mkdir -p "$OVERLAY/usr/share/osa/grub-theme"
mkdir -p "$OVERLAY/usr/share/wayland-sessions"
mkdir -p "$OVERLAY/etc/greetd"

# Copy AI core source for in-chroot install
cp -r "$REPO_ROOT/ai-core/"* "$OVERLAY/opt/osa-core/"

# Copy systemd units
for unit in "$REPO_ROOT"/inference/systemd/*.service "$REPO_ROOT"/inference/systemd/*.target; do
    [ -f "$unit" ] && cp "$unit" "$OVERLAY/etc/systemd/system/"
done

# Copy llama-swap config
mkdir -p "$OVERLAY/etc/osa/llama-swap"
cp "$REPO_ROOT/inference/llama-swap/config.yaml" "$OVERLAY/etc/osa/llama-swap/"

# Copy C++ binaries if built
for bin in osa-hwdetect osa-sandbox osa-updater; do
    if [ -f "$REPO_ROOT/system/$bin/build/$bin" ]; then
        cp "$REPO_ROOT/system/$bin/build/$bin" "$OVERLAY/usr/local/bin/"
    fi
done

# Copy desktop session files
cp "$REPO_ROOT/desktop/session/osafrica.desktop" "$OVERLAY/usr/share/wayland-sessions/"
cp "$REPO_ROOT/desktop/session/osa-session" "$OVERLAY/usr/share/osa/session/"
cp "$REPO_ROOT/desktop/session/osa-ai-agents.desktop" "$OVERLAY/usr/share/osa/session/"

# Copy GRUB theme
cp "$REPO_ROOT/distro/grub/theme/"* "$OVERLAY/usr/share/osa/grub-theme/" 2>/dev/null || true

# Copy greetd config
cp "$REPO_ROOT/distro/greetd/config.toml" "$OVERLAY/etc/greetd/"
cp -r "$REPO_ROOT/distro/greetd/osa-greeter" "$OVERLAY/usr/share/osa/"

# Copy skeleton user config
cp -r "$REPO_ROOT/distro/skel/." "$OVERLAY/usr/share/osa/skel/"

# Copy Plymouth theme
mkdir -p "$OVERLAY/usr/share/plymouth/themes/osafrica"
cp "$REPO_ROOT/distro/plymouth/themes/osafrica/"* "$OVERLAY/usr/share/plymouth/themes/osafrica/" 2>/dev/null || true

# Copy Calamares branding
if [ -d "$REPO_ROOT/distro/calamares" ]; then
    mkdir -p "$OVERLAY/etc/calamares"
    cp "$REPO_ROOT/distro/calamares/settings.conf" "$OVERLAY/etc/calamares/"
    cp -r "$REPO_ROOT/distro/calamares/branding" "$OVERLAY/etc/calamares/" 2>/dev/null || true
fi

# Build the ISO
echo "[4/4] Building ISO..."
sudo lb build 2>&1 | tee build.log

ISO_FILE=$(ls -1 "$BUILD_DIR"/*.iso 2>/dev/null | head -1)
if [ -n "$ISO_FILE" ]; then
    echo ""
    echo "=== Build Complete ==="
    echo "ISO: $ISO_FILE"
    echo "Size: $(du -h "$ISO_FILE" | cut -f1)"
    echo ""
    echo "Test with: ./scripts/test-qemu.sh $ISO_FILE"
else
    echo "Error: ISO build failed. Check build.log for details."
    exit 1
fi
