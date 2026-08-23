#!/bin/bash
set -e

# The model was already pulled at image-build time (see Dockerfile) --
# `ollama serve` finds the blobs already on disk, no download needed here.
ollama serve &

for i in $(seq 1 60); do
  curl -sf http://localhost:11434 >/dev/null && break
  sleep 2
done

exec streamlit run app/ui/streamlit_app.py \
    --server.port "${PORT:-7860}" \
    --server.address 0.0.0.0 \
    --server.headless true
