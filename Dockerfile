# Bundles Ollama itself alongside the app -- this project has no hosted-API
# dependency to configure at deploy time, which is the whole point of using
# a local model. The model is pulled at BUILD time (baked into the image),
# not at container start: HF's free CPU Spaces sleep after inactivity, and a
# multi-GB re-download on every cold start would make the demo unusable.
# Uses a smaller model tag than local dev's default (llama3.2:1b vs.
# llama3.2) so an interactive demo on a free, CPU-only Space stays responsive.

FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://ollama.com/install.sh | sh

WORKDIR /app
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --no-cache-dir -e .

ENV GUARDIAN_LLM_MODEL=ollama:llama3.2:1b
ENV GUARDIAN_OLLAMA_BASE_URL=http://localhost:11434
ENV OLLAMA_HOST=0.0.0.0:11434
ENV PORT=7860

# Start the daemon just long enough to pull the model, then stop it -- the
# downloaded blobs persist as part of this layer, so `ollama serve` at
# container start finds them already present.
RUN ollama serve & \
    for i in $(seq 1 60); do curl -sf http://localhost:11434 >/dev/null && break; sleep 2; done && \
    ollama pull "${GUARDIAN_LLM_MODEL#ollama:}" && \
    kill %1 || true

COPY docker/start.sh /app/docker/start.sh
RUN chmod +x /app/docker/start.sh

EXPOSE 7860
CMD ["/app/docker/start.sh"]
