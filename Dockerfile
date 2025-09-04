# ========================
# STAGE 1 - BUILDER
# ========================
FROM python:3.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# ✅ Copia requirements primeiro para melhor cache
COPY requirements.txt .

# ✅ Instala tudo em um único layer para otimização
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget curl unzip ca-certificates gnupg && \
    \
    # Instala Chrome estável (versão mais compatível)
    wget -q -O /tmp/chrome.deb \
        https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get install -y /tmp/chrome.deb && \
    rm -f /tmp/chrome.deb && \
    \
    # Instala ChromeDriver compatível
    CHROME_VERSION=$(google-chrome --version | awk '{print $3}') && \
    echo "Detected Chrome version: ${CHROME_VERSION}" && \
    wget -q -O /tmp/chromedriver.zip \
        "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip" && \
    unzip /tmp/chromedriver.zip -d /tmp/ && \
    mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/ && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /tmp/chromedriver.zip /tmp/chromedriver-linux64 && \
    \
    # Instala dependências Python
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt && \
    \
    # Limpeza
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# ========================
# STAGE 2 - RUNTIME (SIMPLIFICADO E CONFIÁVEL)
# ========================
FROM python:3.10-slim

WORKDIR /app

# ✅ Copia apenas o essencial
COPY --from=builder /install /usr/local
COPY --from=builder /usr/bin/google-chrome /usr/bin/
COPY --from=builder /usr/local/bin/chromedriver /usr/local/bin/
COPY --from=builder /opt/google/chrome/chrome-sandbox /opt/google/chrome/

# ✅ Instala dependências de runtime manualmente (CONFIÁVEL)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libnss3 libatk1.0-0 libatk-bridge2.0-0 \
        libx11-xcb1 libxcomposite1 libxdamage1 \
        libxfixes3 libxrandr2 libgbm1 libasound2 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ✅ Configuração de usuário seguro
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    mkdir -p /home/appuser/Downloads && \
    chown -R appuser:appuser /home/appuser /app && \
    chmod +x /usr/local/bin/chromedriver

USER appuser

COPY --chown=appuser:appuser . .

EXPOSE 10000

CMD ["sh", "-c", "gunicorn main:app --bind 0.0.0.0:${PORT:-10000} --timeout 120 --workers 2 --preload"]
