FROM python:3.11-slim

WORKDIR /app

# Create darwin user
RUN useradd -m -u 1000 darwin && \
    chown -R darwin:darwin /app

# System dependencies (gosu for safe privilege drop in entrypoint)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code
COPY --chown=darwin:darwin . .

# Create necessary directories
RUN mkdir -p /app/data /app/logs /backup && \
    chown -R darwin:darwin /app/data /app/logs /backup

# Entrypoint fixes volume permissions then drops to darwin
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
