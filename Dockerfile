FROM python:3.10-slim

WORKDIR /app

# ✅ Instala Chrome minimalista e seguro
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates wget unzip && \
    mkdir -p /tmp/chrome && cd /tmp/chrome && \
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    # ✅ CORREÇÃO: Extrai todos os arquivos e identifica o data.tar.*
    ar x google-chrome-stable_current_amd64.deb && \
    tar -xf data.tar.* && \
    mv ./opt/google/chrome /opt/ && \
    mv ./usr/bin/google-chrome-stable /usr/bin/google-chrome && \
    ln -sf /usr/bin/google-chrome /opt/google/chrome/chrome && \
    rm -rf /tmp/chrome && \
    google-chrome --version && \
    # ✅ Limpeza no mesmo RUN
    apt-get clean && rm -rf /var/lib/apt/lists/*
    
# ... (O restante do Dockerfile segue inalterado)

# ✅ Instalação Python com cache
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ✅ Usuário seguro
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    chown -R appuser:appuser /app
USER appuser

COPY --chown=appuser:appuser . .

EXPOSE 10000
CMD ["sh", "-c", "gunicorn main:app --bind 0.0.0.0:${PORT:-10000} --timeout 120 --workers 2 --preload"]
