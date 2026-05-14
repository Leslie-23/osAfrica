#!/usr/bin/env bash
set -euo pipefail

# Boot the osAfrica ISO in QEMU for testing.
# Usage: ./scripts/test-qemu.sh [path-to-iso]

ISO="${1:-distro/live-build/live-image-amd64.hybrid.iso}"
RAM="${OSA_QEMU_RAM:-4096}"
CPUS="${OSA_QEMU_CPUS:-2}"

if [ ! -f "$ISO" ]; then
    echo "Error: ISO not found at $ISO"
    echo "Build it first: cd distro/live-build && sudo lb build"
    exit 1
fi

echo "=== osAfrica QEMU Test ==="
echo "ISO:  $ISO"
echo "RAM:  ${RAM}M"
echo "CPUs: $CPUS"
echo ""

# Create a temporary disk for install testing
DISK="/tmp/osafrica-test-disk.qcow2"
if [ ! -f "$DISK" ]; then
    qemu-img create -f qcow2 "$DISK" 30G
fi

qemu-system-x86_64 \
    -enable-kvm \
    -m "$RAM" \
    -smp "$CPUS" \
    -cdrom "$ISO" \
    -drive file="$DISK",format=qcow2 \
    -boot d \
    -vga virtio \
    -display gtk \
    -device virtio-net-pci,netdev=net0 \
    -netdev user,id=net0 \
    -usb \
    -device usb-tablet \
    -name "osAfrica Test"
