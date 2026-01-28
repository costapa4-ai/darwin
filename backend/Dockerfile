FROM python:3.11-slim

WORKDIR /app

# Segurança
RUN useradd -m -u 1000 darwin && \
    chown -R darwin:darwin /app

# Dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código
COPY --chown=darwin:darwin . .

# Criar diretórios necessários
RUN mkdir -p /app/data /app/logs && \
    chown -R darwin:darwin /app/data /app/logs

USER darwin

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
