# Stage 1: Build
FROM python:3.12-slim as builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Final
FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

RUN pip install --no-cache /wheels/*

# Create non-root user and directories
RUN addgroup --system sisrua && adduser --system --group sisrua \
    && mkdir -p /app/logs /app/cache && chown -R sisrua:sisrua /app

USER sisrua
COPY --chown=sisrua:sisrua . .

# Environment variables
ENV PORT=8000
ENV HOST=0.0.0.0

EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn backend.infrastructure.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
