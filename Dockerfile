# ========================
# STAGE 1 - BUILDER
# ========================
FROM python:3.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    CHROME_VERSION="140.0.7339.80"

WORKDIR /app

# ✅ Copia requirements PRIMEIRO (evita cache busting desnecessário)
COPY requirements.txt .

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        wget curl unzip ca-certificates gnupg build-essential gcc \
        fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 \
        libcups2 libdbus-1-3 libnspr4 libnss3 libx11-xcb1 \
        libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
        libxshmfence1 libdrm2 libxkbcommon0 libappindicator3-1; \
    \
    # Instala Chrome
    echo "Installing Chrome version: ${CHROME_VERSION}"; \
    wget -q -O /tmp/chrome.deb \
        "https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_${CHROME_VERSION}-1_amd64.deb"; \
    apt-get install -y /tmp/chrome.deb; \
    rm -f /tmp/chrome.deb; \
    \
    # Instala ChromeDriver
    echo "Downloading ChromeDriver for version: ${CHROME_VERSION}"; \
    wget -q -O /tmp/chromedriver.zip \
        "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip"; \
    unzip -q /tmp/chromedriver.zip -d /tmp/; \
    mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/; \
    chmod +x /usr/local/bin/chromedriver; \
    rm -rf /tmp/chromedriver.zip /tmp/chromedriver-linux64; \
    \
    # ✅ Instala dependências Python (AGORA COM requirements.txt DISPONÍVEL)
    pip install --no-cache-dir --upgrade pip; \
    pip install --no-cache-dir --prefix=/install -r requirements.txt; \
    pip install --no-cache-dir --prefix=/install gunicorn; \
    \
    # Captura dependências
    mkdir -p /chrome-deps; \
    ldd /usr/bin/google-chrome | awk '/=>/ {print $3}' | grep -E '^/' | sort -u | xargs -I{} cp -v --parents {} /chrome-deps 2>/dev/null || true; \
    ldd /usr/local/bin/chromedriver | awk '/=>/ {print $3}' | grep -E '^/' | sort -u | xargs -I{} cp -v --parents {} /chrome-deps 2>/dev/null || true; \
    \
    # Limpeza
    apt-get clean; \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*;

# ========================
# STAGE 2 - RUNTIME SUPER ENXUTO
# ========================
FROM python:3.10-slim

WORKDIR /app  # ✅ ADICIONADO: WORKDIR essencial

# ✅ Cópia SEGURA e COMPLETA das dependências
COPY --from=builder /install /usr/local
COPY --from=builder /usr/bin/google-chrome /usr/bin/google-chrome
COPY --from=builder /usr/local/bin/chromedriver /usr/local/bin/chromedriver
COPY --from=builder /opt/google/chrome/chrome-sandbox /opt/google/chrome/chrome-sandbox
COPY --from=builder /chrome-deps/. /  # ✅ MELHOR: Copia TUDO de forma segura

# ✅ Configuração completa e limpeza
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    mkdir -p /home/appuser/Downloads && \
    chown -R appuser:appuser /home/appuser /app && \
    chmod +x /usr/local/bin/chromedriver && \
    apt-get update && apt-get clean && rm -rf /var/lib/apt/lists/*;  # ✅ LIMPEZA ADICIONADA

USER appuser

COPY --chown=appuser:appuser . .

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-10000}/healthcheck || exit 1

CMD ["sh", "-c", "gunicorn main:app --bind 0.0.0.0:${PORT:-10000} --timeout 120 --workers 2 --preload"]
