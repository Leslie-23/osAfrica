#!/usr/bin/env bash
set -euo pipefail

# osAfrica Development Environment Setup
# Run this on Debian/Ubuntu or WSL2 to set up the dev environment.

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODEL_DIR="/opt/osa/models"

echo "=== osAfrica Dev Setup ==="
echo "Repo: $REPO_ROOT"
echo ""

# --- System dependencies ---
echo "[1/5] Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    build-essential cmake git curl wget \
    python3 python3-pip python3-venv \
    libcurl4-openssl-dev \
    bubblewrap \
    2>/dev/null

# --- llama.cpp ---
echo "[2/5] Building llama.cpp..."
LLAMA_DIR="$REPO_ROOT/.deps/llama.cpp"
if [ ! -d "$LLAMA_DIR" ]; then
    git clone --depth 1 https://github.com/ggerganov/llama.cpp.git "$LLAMA_DIR"
fi
cd "$LLAMA_DIR"
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j "$(nproc)"
sudo cp build/bin/llama-server /usr/local/bin/llama-server
echo "  llama-server installed: $(llama-server --version 2>&1 | head -1 || echo 'ok')"

# --- llama-swap ---
echo "[3/5] Installing llama-swap..."
SWAP_VERSION="v0.3.0"
SWAP_URL="https://github.com/mostlygeek/llama-swap/releases/download/${SWAP_VERSION}/llama-swap-linux-amd64"
if [ ! -f /usr/local/bin/llama-swap ]; then
    sudo wget -q -O /usr/local/bin/llama-swap "$SWAP_URL" || echo "  (download URL may need updating)"
    sudo chmod +x /usr/local/bin/llama-swap
fi

# --- Python AI core ---
echo "[4/5] Setting up Python environment..."
cd "$REPO_ROOT/ai-core"
python3 -m venv "$REPO_ROOT/.venv"
source "$REPO_ROOT/.venv/bin/activate"
pip install -e ".[dev]" -q

# --- Model directory ---
echo "[5/5] Creating model directory..."
sudo mkdir -p "$MODEL_DIR"
sudo chown "$(whoami)" "$MODEL_DIR"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Download models:  ./inference/models/download-models.sh"
echo "  2. Activate venv:    source .venv/bin/activate"
echo "  3. Run AI shell:     osa-shell"
echo "  4. Run router:       osa-routerd"
echo ""
echo "For GPU support (NVIDIA), rebuild llama.cpp with CUDA:"
echo "  cd .deps/llama.cpp && cmake -B build -DGGML_CUDA=ON && cmake --build build -j \$(nproc)"
