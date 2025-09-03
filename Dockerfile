# ========================
# STAGE 1 - BUILDER
# ========================
FROM python:3.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# ✅ INSTALA TODAS AS DEPENDÊNCIAS + CHROME + CHROMEDRIVER EM UMA ÚNICA CAMADA
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      wget curl unzip ca-certificates gnupg build-essential gcc \
      fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 \
      libcups2 libdbus-1-3 libnspr4 libnss3 libx11-xcb1 \
      libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
      libxshmfence1 libdrm2 libxkbcommon0; \
    \
    # Baixa e instala Chrome estável
    wget -q -O /tmp/chrome.deb \
      "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"; \
    apt-get install -y /tmp/chrome.deb; \
    rm -f /tmp/chrome.deb; \
    \
    # Ajusta Chromedriver compatível
    CHROME_VERSION=$(google-chrome --version | awk '{print $3}'); \
    CHROME_MAJOR=$(echo $CHROME_VERSION | cut -d. -f1); \
    CHROME_MINOR=$(echo $CHROME_VERSION | cut -d. -f2); \
    CHROME_PATCH=$(echo $CHROME_VERSION | cut -d. -f3); \
    echo "Chrome version: ${CHROME_VERSION}"; \
    \
    for VERSION in "${CHROME_VERSION}" "${CHROME_MAJOR}.${CHROME_MINOR}.${CHROME_PATCH}" "${CHROME_MAJOR}.${CHROME_MINOR}.0" "${CHROME_MAJOR}"; do \
      echo "Trying version: $VERSION"; \
      wget -q -O /tmp/chromedriver.zip \
        "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/${VERSION}/linux64/chromedriver-linux64.zip" && break; \
      wget -q -O /tmp/chromedriver.zip \
        "https://storage.googleapis.com/chrome-for-testing-public/${VERSION}/linux64/chromedriver-linux64.zip" && break; \
      wget -q -O /tmp/chromedriver.zip \
        "https://chromedriver.storage.googleapis.com/${VERSION}/chromedriver_linux64.zip" && break; \
    done; \
    \
    unzip -q /tmp/chromedriver.zip -d /usr/local/bin/; \
    if [ -d "/usr/local/bin/chromedriver-linux64" ]; then \
      mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/; \
      rm -rf /usr/local/bin/chromedriver-linux64; \
    fi; \
    chmod +x /usr/local/bin/chromedriver; \
    rm -f /tmp/chromedriver.zip; \
    \
    echo "Chromedriver installed:"; \
    ls -lh /usr/local/bin/chromedriver; \
    chromedriver --version; \
    \
    # Limpeza
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Instala deps Python no prefixo /install
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt && \
    pip install --no-cache-dir --prefix=/install gunicorn

# ========================
# STAGE 2 - RUNTIME OTIMIZADO
# ========================
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/usr/local/bin:$PATH"

WORKDIR /app

# ✅ Copia dependências essenciais já resolvidas do builder
COPY --from=builder /install /usr/local
COPY --from=builder /usr/local/bin/chromedriver /usr/local/bin/chromedriver
COPY --from=builder /usr/bin/google-chrome /usr/bin/google-chrome
COPY --from=builder /opt/google/chrome /opt/google/chrome

# ✅ Usuário não-root
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    mkdir -p /home/appuser/Downloads && \
    chown -R appuser:appuser /home/appuser /app && \
    chmod 755 /usr/local/bin/chromedriver

USER appuser

COPY --chown=appuser:appuser . .

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-10000}/healthcheck || exit 1

CMD ["sh", "-c", "gunicorn main:app --bind 0.0.0.0:${PORT:-10000} --timeout 120 --workers 1 --preload"]
