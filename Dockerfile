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

# 🔧 CORREÇÕES CRÍTICAS PARA SELENIUM NO RENDER
# Chrome + ChromeDriver e libs de runtime pró Selenium
RUN set -eux; \
    apt-get update; \
    # ✅ INSTALA DEPENDÊNCIAS ESSENCIAIS PRIMEIRO
    apt-get install -y --no-install-recommends \
      wget curl unzip ca-certificates \
      fonts-liberation libappindicator3-1 libasound2 \
      libatk-bridge2.0-0 libatk1.0-0 libcups2 libdbus-1-3 \
      libnspr4 libnss3 libx11-xcb1 libxcomposite1 \
      libxdamage1 libxrandr2 xdg-utils libu2f-udev \
      # ✅ DEPENDÊNCIAS NOVAS ESSENCIAIS
      libgbm-dev libxshmfence-dev libnss3-tools \
      libdrm-dev libxkbcommon-dev libxcb-icccm4-dev \
      libxcb-image0-dev libxcb-keysyms1-dev libxcb-render-util0-dev; \
    \
    # ✅ GDK-PIXBUF - CORREÇÃO PARA DEBIAN 12
    (apt-get install -y --no-install-recommends libgdk-pixbuf-2.0-0t64 || \
     apt-get install -y --no-install-recommends libgdk-pixbuf-2.0-0 || \
     apt-get install -y --no-install-recommends libgdk-pixbuf2.0-0 || true); \
    \
    # ✅ CHROME ESTÁVEL - BAIXA VERSÃO COMPATÍVEL
    # Usa a versão específica que funciona no Render
    curl -sSL https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -o /tmp/chrome.deb; \
    apt-get install -y /tmp/chrome.deb; \
    rm -f /tmp/chrome.deb; \
    \
    # ✅ CHROMEDRIVER - BAIXA VERSÃO COMPATÍVEL COM O CHROME
    CHROME_VERSION=$(google-chrome --version | awk '{print $3}'); \
    echo "Chrome version: ${CHROME_VERSION}"; \
    \
    # ✅ BAIXA CHROMEDRIVER DA FONTE CORRETA (Google Storage)
    CHROME_MAJOR_VERSION=$(echo $CHROME_VERSION | cut -d'.' -f1); \
    CHROME_DRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_MAJOR_VERSION}"); \
    echo "Chromedriver version: ${CHROME_DRIVER_VERSION}"; \
    \
    wget -q "https://chromedriver.storage.googleapis.com/${CHROME_DRIVER_VERSION}/chromedriver_linux64.zip" -O /tmp/chromedriver.zip; \
    unzip -q /tmp/chromedriver.zip -d /usr/local/bin/; \
    chmod +x /usr/local/bin/chromedriver; \
    rm -f /tmp/chromedriver.zip; \
    \
    # ✅ VERIFICA INSTALAÇÃO
    echo "Chromedriver info:"; \
    /usr/local/bin/chromedriver --version; \
    \
    # ✅ LIMPEZA OTIMIZADA (mantém dependências necessárias)
    apt-get autoremove -y --purge; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/* /tmp/* /var/tmp/*;

WORKDIR /app

# Copia libs Python já instaladas no builder
COPY --from=builder /install /usr/local

# ✅ GARANTE PERMISSÕES CORRETAS PARA CHROMEDRIVER
RUN chmod 755 /usr/local/bin/chromedriver && \
    # ✅ CRIA USUário não-root para segurança
    groupadd -r chromeuser && useradd -r -g chromeuser -G audio,video chromeuser && \
    mkdir -p /home/chromeuser/Downloads && \
    chown -R chromeuser:chromeuser /home/chromeuser && \
    chown -R chromeuser:chromeuser /app

# ✅ ALTERA PARA USUÁRIO NÃO-ROOT (mais seguro e estável)
USER chromeuser

# Copia o código da aplicação
COPY --chown=chromeuser:chromeuser . .

# Porta padrão (Render usa ${PORT})
EXPOSE 10000

# ✅ COMANDO DE HEALTH CHECK PARA VERIFICAR CHROME
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD google-chrome --version && chromedriver --version

# Web: Gunicorn; Workers/Beat usam startCommand no render.yaml
CMD ["sh", "-c", "gunicorn main:app --bind 0.0.0.0:${PORT:-10000}"]
