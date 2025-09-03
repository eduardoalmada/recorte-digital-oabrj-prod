# ========================
# STAGE 1 - BUILDER
# ========================
FROM python:3.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# ✅ COPIA O chrome-libs.txt DA RAIZ PARA O BUILDER (LINHA ADICIONADA)
COPY chrome-libs.txt /chrome-libs-fallback.txt

# ✅ INSTALA TUDO + IDENTIFICA LIBS EXATAS DO CHROME
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      wget curl unzip ca-certificates gnupg build-essential gcc \
      fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 \
      libcups2 libdbus-1-3 libnspr4 libnss3 libx11-xcb1 \
      libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
      libxshmfence1 libdrm2 libxkbcommon0 libappindicator3-1; \
    \
    # Chrome estável
    wget -q -O /tmp/chrome.deb \
      "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"; \
    apt-get install -y /tmp/chrome.deb; \
    rm -f /tmp/chrome.deb; \
    \
    # Chromedriver compatível
    CHROME_VERSION=$(google-chrome --version | awk '{print $3}'); \
    for VERSION in "${CHROME_VERSION}" "${CHROME_VERSION%.*}"; do \
      wget -q -O /tmp/chromedriver.zip \
        "https://storage.googleapis.com/chrome-for-testing-public/${VERSION}/linux64/chromedriver-linux64.zip" && break; \
      wget -q -O /tmp/chromedriver.zip \
        "https://chromedriver.storage.googleapis.com/${VERSION}/chromedriver_linux64.zip" && break; \
    done; \
    unzip -q /tmp/chromedriver.zip -d /usr/local/bin/; \
    if [ -d "/usr/local/bin/chromedriver-linux64" ]; then \
      mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/; \
      rm -rf /usr/local/bin/chromedriver-linux64; \
    fi; \
    chmod +x /usr/local/bin/chromedriver; \
    rm -f /tmp/chromedriver.zip; \
    \
    # ✅ IDENTIFICA LIBS EXATAS DO CHROME (SEM ldd NO RUNTIME)
    mkdir -p /chrome-libs; \
    ldd /usr/bin/google-chrome | awk '/=>/ {print $3}' | grep -E '^(/usr|/lib)' | sort -u > /chrome-libs.txt; \
    ldd /usr/local/bin/chromedriver | awk '/=>/ {print $3}' | grep -E '^(/usr|/lib)' | sort -u >> /chrome-libs.txt; \
    sort -u /chrome-libs.txt -o /chrome-libs.txt; \
    \
    # ✅ COMBINA COM FALLBACK (LINHA ADICIONADA)
    cat /chrome-libs.txt /chrome-libs-fallback.txt 2>/dev/null | sort -u > /chrome-libs-complete.txt; \
    mv /chrome-libs-complete.txt /chrome-libs.txt; \
    \
    # Python deps
    pip install --no-cache-dir --upgrade pip; \
    pip install --no-cache-dir --prefix=/install -r requirements.txt; \
    pip install --no-cache-dir --prefix=/install gunicorn; \
    \
    # Limpeza
    apt-get clean; \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*;

# ========================
# STAGE 2 - RUNTIME SUPER ENXUTO E PREVISÍVEL
# ========================
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/usr/local/bin:$PATH"

WORKDIR /app

# ✅ COPIA LIBS PYTHON
COPY --from=builder /install /usr/local

# ✅ COPIA BINÁRIOS ESSENCIAIS
COPY --from=builder /usr/local/bin/chromedriver /usr/local/bin/chromedriver
COPY --from=builder /usr/bin/google-chrome /usr/bin/google-chrome

# ✅ COPIA APENAS AS LIBS NECESSÁRIAS (LISTA EXPLÍCITA)
COPY --from=builder /chrome-libs.txt /chrome-libs.txt

# ✅ INSTALA APENAS AS LIBS EXATAS DO CHROME (SEM ldd!)
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      # ✅ LIBS CORE (SISTEMA)
      libasound2 libatk-bridge2.0-0 libatk1.0-0 libcups2 \
      libdbus-1-3 libdrm2 libgbm1 libnspr4 libnss3 \
      libx11-6 libx11-xcb1 libxcb1 libxcomposite1 \
      libxdamage1 libxext6 libxfixes3 libxrandr2 \
      libxshmfence1 libxkbcommon0 \
      # ✅ LIBS ESPECÍFICAS DO CHROME (DO ARQUIVO)
      $(cat /chrome-libs.txt | xargs -n1 basename | sed 's/.*\/\([^/]*\)/\1/' | sort -u); \
    \
    # ✅ COPIA LIBS PERSONALIZADAS DO CHROME (SE HOUVER)
    while read -r LIB; do \
      if [ -f "$LIB" ] && ! dpkg -S "$LIB" >/dev/null 2>&1; then \
        cp --parents "$LIB" /; \
      fi; \
    done < /chrome-libs.txt; \
    \
    # Limpeza
    rm -f /chrome-libs.txt; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*;

# ✅ USUÁRIO E PERMISSÕES
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    mkdir -p /home/appuser/Downloads && \
    chown -R appuser:appuser /home/appuser /app /usr/local/bin/chromedriver;

USER appuser

COPY --chown=appuser:appuser . .

EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-10000}/healthcheck || exit 1

CMD ["sh", "-c", "gunicorn main:app --bind 0.0.0.0:${PORT:-10000} --timeout 120 --workers 2 --preload"]
