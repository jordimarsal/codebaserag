#!/usr/bin/env bash
# Start a llama.cpp embedding+completion server for codebaserag.
#
# Configure via environment variables (all optional except LLAMACPP_MODEL):
#   LLAMACPP_DIR       llama.cpp checkout dir (default: /home/jordi/ia/llama/llama.cpp)
#   LLAMACPP_MODEL     path to the .gguf model to serve (REQUIRED for --embeddings use)
#   LLAMACPP_HOST      bind host             (default: 0.0.0.0)
#   LLAMACPP_PORT      listen port           (default: 8080)
#   LLAMACPP_GPU       gpu layers (-ngl); -1 = all on GPU (default: -1)
#   LLAMACPP_CTX       context size          (default: 8192)
#   LLAMACPP_EMBEDDINGS 1 to enable /v1/embeddings (default: 1)
#   LLAMACPP_LOG       log file              (default: /tmp/llamacpp-server.log)
set -euo pipefail

LLAMACPP_DIR="${LLAMACPP_DIR:-/home/jordi/ia/llama/llama.cpp}"
LLAMACPP_HOST="${LLAMACPP_HOST:-0.0.0.0}"
LLAMACPP_PORT="${LLAMACPP_PORT:-8080}"
LLAMACPP_GPU="${LLAMACPP_GPU:-99}"
LLAMACPP_CTX="${LLAMACPP_CTX:-8192}"
LLAMACPP_BATCH="${LLAMACPP_BATCH:-2048}"
LLAMACPP_EMBEDDINGS="${LLAMACPP_EMBEDDINGS:-1}"
LLAMACPP_LOG="${LLAMACPP_LOG:-/tmp/llamacpp-server.log}"

if [[ -z "${LLAMACPP_MODEL:-}" ]]; then
  echo "ERROR: set LLAMACPP_MODEL to the .gguf to serve (e.g. nomic-embed-text-v1.5.Q4_K_M.gguf)" >&2
  exit 2
fi
if [[ ! -f "$LLAMACPP_MODEL" ]]; then
  echo "ERROR: LLAMACPP_MODEL not found: $LLAMACPP_MODEL" >&2
  exit 2
fi

SERVER_BIN="${LLAMACPP_DIR}/build/bin/llama-server"
if [[ ! -x "$SERVER_BIN" ]]; then
  echo "ERROR: llama-server not found at $SERVER_BIN (build llama.cpp first)" >&2
  exit 2
fi

# Fail fast if something is already on the port.
if curl -s --max-time 2 "http://localhost:${LLAMACPP_PORT}/health" >/dev/null 2>&1; then
  echo "llama.cpp server already answering on :${LLAMACPP_PORT} (health OK). Nothing to do." >&2
  exit 0
fi

EMB_FLAG=()
if [[ "$LLAMACPP_EMBEDDINGS" == "1" ]]; then
  EMB_FLAG=(--embeddings)
fi

echo "Starting llama-server:"
echo "  bin : $SERVER_BIN"
echo "  model: $LLAMACPP_MODEL"
echo "  endpoint: http://${LLAMACPP_HOST}:${LLAMACPP_PORT}  (embeddings=$([[ "$LLAMACPP_EMBEDDINGS" == "1" ]] && echo on || echo off))"
echo "  log : $LLAMACPP_LOG"

nohup "$SERVER_BIN" \
  --model "$LLAMACPP_MODEL" \
  --host "$LLAMACPP_HOST" \
  --port "$LLAMACPP_PORT" \
  --n-gpu-layers "$LLAMACPP_GPU" \
  --ctx-size "$LLAMACPP_CTX" \
  --batch-size "$LLAMACPP_BATCH" \
  --ubatch-size "$LLAMACPP_BATCH" \
  "${EMB_FLAG[@]}" \
  </dev/null >"$LLAMACPP_LOG" 2>&1 &

PID=$!
echo "launched pid=$PID"

# Wait for readiness.
for _ in $(seq 1 60); do
  if curl -s --max-time 2 "http://localhost:${LLAMACPP_PORT}/health" >/dev/null 2>&1; then
    echo "llama.cpp server is UP on :${LLAMACPP_PORT}"
    exit 0
  fi
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "ERROR: llama-server exited early. Tail of log:" >&2
    tail -n 20 "$LLAMACPP_LOG" >&2
    exit 1
  fi
  sleep 1
done

echo "WARNING: server not ready after 60s; check $LLAMACPP_LOG (pid=$PID still running)" >&2
exit 0
