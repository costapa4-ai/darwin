FROM python:3.11-slim

WORKDIR /sandbox

# Install minimal dependencies
RUN pip install --no-cache-dir numpy

# Create non-root user
RUN useradd -m -u 1000 sandbox && \
    chown -R sandbox:sandbox /sandbox

# Copy runner script
COPY runner.py .

USER sandbox

# Keep container running
CMD ["python", "-u", "runner.py"]
