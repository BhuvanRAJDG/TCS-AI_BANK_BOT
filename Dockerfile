# -------------------------------------------------
# Multi‑stage Docker build for SentinelBank AI
# -------------------------------------------------

# ---------- Stage 1: Tailwind CSS build ----------
FROM node:20-alpine AS tailwind-builder
WORKDIR /build
COPY app/static/tailwind/ .
RUN npm install -g tailwindcss@3.4.1 && \
    npx tailwindcss -i ./input.css -o ../static/css/tailwind.css --minify

# ---------- Stage 2: Python backend ----------
FROM python:3.11-slim

# System dependencies for MySQL client & build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libmariadb-dev && \
    rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy compiled Tailwind CSS from builder stage
COPY --from=tailwind-builder /app/static/css/tailwind.css ./app/static/css/tailwind.css

# Expose Flask port
EXPOSE 5000

# Run with gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:app"]
