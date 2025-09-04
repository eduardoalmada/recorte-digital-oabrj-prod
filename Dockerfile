# ========================
# STAGE 1 - BUILDER
# ========================
FROM python:3.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    CHROME_VERSION="140.0.7339.80" \
    CHROMEDRIVER_VERSION="140.0.7339.80"

WORKDIR /app

# ✅ Instalação de todos os pacotes e Chrome em um único comando RUN
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        wget curl unzip ca-certificates gnupg build-essential gcc libc-bin \
        fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 \
        libcups2 libdbus-1-3 libnspr4 libnss3 libx11-xcb1 \
        libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
        libxshmfence1 libdrm2 libxkbcommon0 libappindicator3-1; \
    \
    # Instalação do Chrome via .deb
    echo "Installing Chrome version: ${CHROME_VERSION}"; \
    wget -q -O /tmp/chrome.deb \
        "https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_${CHROME_VERSION}-1_amd64.deb"; \
    apt-get install -y /tmp/chrome.deb; \
    rm -f /tmp/chrome.deb; \
    \
    # Instalação do ChromeDriver e correção do caminho
    echo "Downloading ChromeDriver for version: ${CHROME_VERSION}"; \
    wget -q -O /tmp/chromedriver.zip \
        "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip"; \
    unzip -q /tmp/chromedriver.zip -d /tmp/; \
    mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/; \
    chmod +x /usr/local/bin/chromedriver; \
    rm -rf /tmp/chromedriver.zip /tmp/chromedriver-linux64; \
    \
    # Captura automática de dependências e limpeza
    mkdir -p /chrome-deps; \
    ldd /usr/bin/google-chrome | awk '/=>/ {print $3}' | grep -E '^/' | sort -u | xargs -I{} cp -v --parents {} /chrome-deps 2>/dev/null || true; \
    ldd /usr/local/bin/chromedriver | awk '/=>/ {print $3}' | grep -E '^/' | sort -u | xargs -I{} cp -v --parents {} /chrome-deps 2>/dev/null || true; \
    \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*;

# ✅ Copia o arquivo de requisitos e instala o Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip; \
    pip install --no-cache-dir --prefix=/install -r requirements.txt; \
    pip install --no-cache-dir --prefix=/install gunicorn;

# ========================
# STAGE 2 - RUNTIME SUPER ENXUTO
# ========================
FROM python:3.10-slim

ENV PATH="/usr/local/bin:$PATH"

WORKDIR /app

# ✅ Copia apenas o essencial
COPY --from=builder /install /usr/local
COPY --from=builder /chrome-deps/ /
COPY --from=builder /usr/bin/google-chrome /usr/bin/google-chrome
COPY --from=builder /opt/google/chrome/chrome-sandbox /opt/google/chrome/chrome-sandbox
COPY --from=builder /usr/local/bin/chromedriver /usr/local/bin/chromedriver

# Configuração de usuário seguro e limpeza final
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    mkdir -p /home/appuser/Downloads && \
    chown -R appuser:appuser /home/appuser /app && \
    chmod +x /usr/local/bin/chromedriver && \
    apt-get clean && rm -rf /var/lib/apt/lists/*;

USER appuser

COPY --chown=appuser:appuser . .

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-10000}/healthcheck || exit 1

CMD ["sh", "-c", "gunicorn main:app --bind 0.0.0.0:${PORT:-10000} --timeout 120 --workers 2 --preload"]
