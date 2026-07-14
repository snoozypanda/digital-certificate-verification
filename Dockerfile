# --- Stage 1: Base ---
FROM python:3.11-slim AS base

# Prevents Python from writing .pyc files and enables unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN rm -f /etc/apt/sources.list.d/debian.sources && \
    printf "deb http://cloudflaremirrors.com/debian trixie main\ndeb http://cloudflaremirrors.com/debian trixie-updates main\n" > /etc/apt/sources.list

# Install system dependencies required by psycopg2 and Pillow
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        libjpeg-dev \
        zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

# --- Stage 2: Dependencies ---
FROM base AS dependencies

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Stage 3: Application ---
FROM dependencies AS application

# Copy application code
COPY . .

# Create required directories
RUN mkdir -p static/certificates static/qr_codes uploads

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]