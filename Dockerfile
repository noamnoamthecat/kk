FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 OMP_NUM_THREADS=2 REGIMEML_STATE_DIR=/data REGIMEML_PROFILES=/data/subscribers.json
COPY pyproject.toml README.md ./
COPY regimeml ./regimeml
RUN pip install --no-cache-dir ".[yahoo]" && mkdir -p /data
VOLUME ["/data"]
EXPOSE 8000
# Web dashboard + live engine. Configure with REGIMEML_* env vars (see README / .env.example).
CMD ["sh", "-c", "uvicorn regimeml.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
