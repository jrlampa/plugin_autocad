# Dockerfile for the Python backend

# ===== STAGE 1: Builder (Compilação) =====
FROM python:3.11-slim AS builder

# Install system dependencies required for GIS libraries (like GDAL)
RUN apt-get update && apt-get install -y \
    build-essential \
    libgdal-dev \
    gdal-bin \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Cria o ambiente virtual e ativa
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY src/backend/requirements.txt src/backend/requirements-ci.txt ./src/backend/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r src/backend/requirements-ci.txt

# ===== STAGE 2: Runtime (Produção) =====
FROM python:3.11-slim

# Instala apenas as dependências de execução (sem build-essential ou pacotes -dev)
RUN apt-get update && apt-get install -y \
    gdal-bin \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia apenas o ambiente virtual empacotado do stage builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="${PYTHONPATH}:/app/src/backend"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]