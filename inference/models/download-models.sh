#!/usr/bin/env bash
set -euo pipefail

# Download GGUF models for osAfrica
# Automatically selects models based on available RAM.

MODEL_DIR="${OSA_MODEL_DIR:-/opt/osa/models}"
MANIFEST="$(dirname "$0")/model-manifest.json"

echo "=== osAfrica Model Downloader ==="
echo "Model directory: $MODEL_DIR"
mkdir -p "$MODEL_DIR"

# Detect available RAM
TOTAL_RAM_MB=$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print int($2/1024)}' || echo "0")
echo "Detected RAM: ${TOTAL_RAM_MB} MB"

# Determine tier
if [ "$TOTAL_RAM_MB" -ge 28000 ]; then
    TIER="32gb"
elif [ "$TOTAL_RAM_MB" -ge 14000 ]; then
    TIER="16gb"
else
    TIER="8gb"
fi

# Check for NVIDIA GPU
if command -v nvidia-smi &>/dev/null; then
    VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1 || echo "0")
    if [ "${VRAM:-0}" -ge 8000 ]; then
        TIER="gpu-nvidia"
    fi
fi

echo "Selected tier: $TIER"
echo ""

# Download Llama 3 8B
echo "[1/2] Downloading Llama 3 8B Instruct..."
if [ "$TIER" = "8gb" ]; then
    LLAMA_FILE="Meta-Llama-3-8B-Instruct-Q4_K_S.gguf"
    LLAMA_DEST="llama-3-8b-instruct.Q4_K_S.gguf"
else
    LLAMA_FILE="Meta-Llama-3-8B-Instruct-Q4_K_M.gguf"
    LLAMA_DEST="llama-3-8b-instruct.Q4_K_M.gguf"
fi

LLAMA_URL="https://huggingface.co/bartowski/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/${LLAMA_FILE}"
if [ -f "$MODEL_DIR/$LLAMA_DEST" ]; then
    echo "  Already downloaded: $LLAMA_DEST"
else
    echo "  Downloading: $LLAMA_URL"
    wget -q --show-progress -O "$MODEL_DIR/$LLAMA_DEST" "$LLAMA_URL"
fi

# Download Qwen Coder (if tier supports it)
if [ "$TIER" = "8gb" ]; then
    echo "[2/2] Skipping Qwen Coder (not enough RAM on 8GB tier)"
else
    echo "[2/2] Downloading Qwen Coder..."
    echo "  NOTE: You will need to manually download the Qwen Coder GGUF from HuggingFace."
    echo "  Visit: https://huggingface.co/models?search=qwen+coder+gguf"
    echo ""
    if [ "$TIER" = "16gb" ]; then
        echo "  For 16GB systems, download Qwen Coder 14B (Q4_K_M):"
        echo "  Place it at: $MODEL_DIR/qwen-coder.gguf"
    else
        echo "  For 32GB+ systems, download Qwen Coder 30B (Q4_K_M):"
        echo "  Place it at: $MODEL_DIR/qwen-coder.gguf"
    fi
fi

echo ""
echo "=== Download Complete ==="
echo "Models directory: $MODEL_DIR"
ls -lh "$MODEL_DIR/" 2>/dev/null || true
