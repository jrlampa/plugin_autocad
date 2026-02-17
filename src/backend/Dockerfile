FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for geospatial libraries (GDAL, etc.)
RUN apt-get update && apt-get install -y \
    binutils \
    libproj-dev \
    gdal-bin \
    libgdal-dev \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set env vars for GDAL compilation if needed
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Install Python dependencies
# Expecting context to be project root, so path is src/backend/requirements.txt
COPY src/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
# Expecting context to be project root
COPY src/backend /app/backend

# Expose default port
EXPOSE 8000

# Run the standalone script as a module
CMD ["python", "-m", "backend.standalone", "--host", "0.0.0.0", "--port", "8000"]
