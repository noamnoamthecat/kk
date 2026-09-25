FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 OMP_NUM_THREADS=2
COPY pyproject.toml README.md ./
COPY regimeml ./regimeml
RUN pip install --no-cache-dir ".[yahoo]"
# Default: daily dry-run signal. Override args, e.g.
#   docker run --env-file .env regimeml --provider alpaca --execute
ENTRYPOINT ["python", "-m", "regimeml.live"]
CMD ["--provider", "yahoo"]
