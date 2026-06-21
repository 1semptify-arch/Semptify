#!/usr/bin/env bash
# install_termux.sh — No-root AI host installer for LG Stylo 4 (and other ARM64 phones)
# Run from inside Termux. Tested on LG Stylo 4 (LM-Q710), Snapdragon 450, 2GB RAM.
set -euo pipefail

echo "=== AI Host Installer (No-Root) ==="
echo "Device: $(getprop ro.product.model 2>/dev/null || echo 'unknown')"
echo "Arch:   $(uname -m)"
echo "RAM:    $(awk '/MemTotal/ {print int($2/1024) " MB"}' /proc/meminfo)"
echo ""

# Sanity check: must be aarch64
if [ "$(uname -m)" != "aarch64" ]; then
  echo "ERROR: This installer targets aarch64. Your device is $(uname -m)."
  echo "For older 32-bit phones, use a smaller model and a 32-bit llama.cpp build."
  exit 1
fi

# 1. Update Termux packages
echo ">>> Updating Termux packages..."
pkg update -y && pkg upgrade -y

# 2. Install build deps
echo ">>> Installing build dependencies..."
pkg install -y git cmake clang make wget curl coreutils \
                termux-api termux-wake-lock

# 3. Create working directory
WORKDIR="$HOME/ai_host"
mkdir -p "$WORKDIR"
cd "$WORKDIR"

# 4. Clone llama.cpp
if [ ! -d "llama.cpp" ]; then
  echo ">>> Cloning llama.cpp..."
  git clone --depth 1 https://github.com/ggerganov/llama.cpp.git
else
  echo ">>> llama.cpp already cloned, pulling latest..."
  cd llama.cpp && git pull --ff-only && cd ..
fi

# 5. Build llama.cpp for ARM64 with NEON optimizations
echo ">>> Building llama.cpp (this takes ~15 min on Stylo 4)..."
cd llama.cpp
mkdir -p build && cd build

# Use clang (faster on ARM than gcc in Termux)
cmake .. \
  -DCMAKE_C_COMPILER=clang \
  -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_BUILD_TYPE=Release \
  -DLLAMA_ARM_NATIVE=ON \
  -DLLAMA_AVX2=OFF \
  -DLLAMA_AVX=OFF \
  -DLLAMA_FMA=OFF \
  -DLLAMA_F16C=OFF \
  -DLLAMA_NEON=ON \
  -DLLAMA_OPENMP=ON \
  -DBUILD_SHARED_LIBS=OFF \
  -DLLAMA_BUILD_TESTS=OFF \
  -DLLAMA_BUILD_EXAMPLES=OFF \
  -DLLAMA_BUILD_SERVER=ON

cmake --build . --config Release --target llama-server -- -j$(nproc)

# Verify the server binary exists
if [ ! -f "bin/llama-server" ]; then
  echo "ERROR: llama-server binary not found after build."
  echo "Look in $WORKDIR/llama.cpp/build/ for the binary."
  exit 1
fi

echo ">>> Build complete: $WORKDIR/llama.cpp/build/bin/llama-server"

# 6. Download a small model that fits in ~600 MB RAM
cd "$WORKDIR"
mkdir -p models
MODEL_URL="https://huggingface.co/Qwen/Qwen2-0.5B-Instruct-GGUF/resolve/main/qwen2-0_5b-instruct-q4_k_m.gguf"
MODEL_FILE="models/qwen2-0.5b-instruct-q4_k_m.gguf"

if [ ! -f "$MODEL_FILE" ]; then
  echo ">>> Downloading Qwen2-0.5B-Instruct Q4_K_M (~400 MB)..."
  wget --show-progress -O "$MODEL_FILE" "$MODEL_URL"
else
  echo ">>> Model already present: $MODEL_FILE"
fi

# 7. Install start/stop scripts
echo ">>> Installing start/stop scripts..."
cp "$WORKDIR/../01_no_root_prototype/start_ai_server.sh" "$WORKDIR/" 2>/dev/null || true
cp "$WORKDIR/../01_no_root_prototype/stop_ai_server.sh" "$WORKDIR/" 2>/dev/null || true

# If scripts aren't found at that path, write them in place
if [ ! -f "$WORKDIR/start_ai_server.sh" ]; then
  echo ">>> Writing start script inline (scripts dir not found)..."
  cat > "$WORKDIR/start_ai_server.sh" <<'START_EOF'
#!/usr/bin/env bash
set -euo pipefail
WORKDIR="$HOME/ai_host"
SERVER="$WORKDIR/llama.cpp/build/bin/llama-server"
MODEL="$WORKDIR/models/qwen2-0.5b-instruct-q4_k_m.gguf"
PORT=8080
THREADS=4
CTX=2048

if [ ! -f "$SERVER" ]; then echo "ERROR: $SERVER not found. Run install_termux.sh first."; exit 1; fi
if [ ! -f "$MODEL" ];  then echo "ERROR: $MODEL not found. Run install_termux.sh first."; exit 1; fi

# Prevent Android from killing us
termux-wake-lock

# Drop filesystem caches (best-effort, no root)
sync; echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true

echo ">>> Starting llama-server on 0.0.0.0:$PORT"
echo ">>> Model: $MODEL"
echo ">>> Threads: $THREADS, Context: $CTX"
echo ">>> Test: curl http://127.0.0.1:$PORT/v1/chat/completions ..."
exec "$SERVER" \
  -m "$MODEL" \
  --host 0.0.0.0 \
  --port "$PORT" \
  -t "$THREADS" \
  -c "$CTX" \
  -ngl 0 \
  --color
START_EOF
  chmod +x "$WORKDIR/start_ai_server.sh"
fi

if [ ! -f "$WORKDIR/stop_ai_server.sh" ]; then
  cat > "$WORKDIR/stop_ai_server.sh" <<'STOP_EOF'
#!/usr/bin/env bash
pkill -f "llama-server" 2>/dev/null && echo "Stopped llama-server." || echo "llama-server not running."
termux-wake-unlock 2>/dev/null || true
STOP_EOF
  chmod +x "$WORKDIR/stop_ai_server.sh"
fi

# 8. Done
echo ""
echo "=== Install complete ==="
echo "Next steps:"
echo "  cd ~/ai_host"
echo "  bash start_ai_server.sh"
echo ""
echo "From another device on the same Wi-Fi:"
echo "  curl http://<phone-ip>:8080/v1/chat/completions \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"model\":\"qwen2-0.5b\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello\"}]}'"
echo ""
echo "To find the phone's IP:  ip addr show wlan0 | grep inet"
