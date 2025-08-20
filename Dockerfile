# ========================
# STAGE 1 - BUILDER
# ========================
FROM python:3.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Dependências mínimas para build de libs Python nativas
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc curl unzip ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Instala deps Python no prefixo /install (copiado no runtime)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt && \
    pip install --no-cache-dir --prefix=/install gunicorn

# ========================
# STAGE 2 - RUNTIME
# ========================
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/usr/local/bin:$PATH"

# Chrome + ChromeDriver e libs de runtime pró Selenium
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      wget curl unzip ca-certificates \
      fonts-liberation libappindicator3-1 libasound2 \
      libatk-bridge2.0-0 libatk1.0-0 libcups2 libdbus-1-3 \
      libnspr4 libnss3 libx11-xcb1 libxcomposite1 \
      libxdamage1 libxrandr2 xdg-utils libu2f-udev; \
    # gdk-pixbuf com fallback (Debian 12 mudou o nome)
    (apt-get install -y --no-install-recommends libgdk-pixbuf-2.0-0t64 || \
     apt-get install -y --no-install-recommends libgdk-pixbuf-2.0-0 || true); \
    # Chrome estável
    curl -sSL https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -o /tmp/chrome.deb; \
    apt-get install -y /tmp/chrome.deb; rm -f /tmp/chrome.deb; \
    # Descobre versão exata do Chrome e baixa o ChromeDriver correspondente (Chrome for Testing)
    CHROME_VERSION="$(google-chrome --version | awk '{print $3}')"; \
    echo "Chrome version: ${CHROME_VERSION}"; \
    wget -q "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip" -O /tmp/chromedriver.zip; \
    unzip -q /tmp/chromedriver.zip -d /tmp/; \
    mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver; \
    chmod +x /usr/local/bin/chromedriver; \
    rm -rf /tmp/chromedriver*; \
    # Limpeza
    apt-get autoremove -y; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/*

WORKDIR /app

# Copia libs Python já instaladas no builder
COPY --from=builder /install /usr/local
# Copia o código da aplicação
COPY . .

# Porta padrão (Render usa ${PORT})
EXPOSE 10000

# Web: Gunicorn; Workers/Beat usam startCommand no render.yaml
CMD ["sh", "-c", "gunicorn main:app --bind 0.0.0.0:${PORT:-10000}"]
