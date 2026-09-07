FROM ghcr.io/home-assistant/base:latest

# Install system dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    tzdata \
    curl

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt /app/
RUN python3 -m pip install --no-cache-dir -r requirements.txt --break-system-packages

# Copy application code
COPY . /app/

# Create required directories
RUN mkdir -p /share/su_urunleri_bot/logs \
    && chmod 755 /share/su_urunleri_bot/logs \
    && chmod +x /app/run.sh

# Set environment
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Run the bot
CMD [ "python3", "-u", "/app/run.py" ]
