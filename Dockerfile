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

# 🔧 CORREÇÕES CRÍTICAS - INSTALAÇÃO SIMPLIFICADA E CONFIÁVEL
RUN set -eux; \
    apt-get update; \
    # ✅ INSTALA APENAS DEPENDÊNCIAS ESSENCIAIS
    apt-get install -y --no-install-recommends \
      wget curl unzip ca-certificates \
      fonts-liberation libappindicator3-1 libasound2 \
      libatk-bridge2.0-0 libatk1.0-0 libcups2 libdbus-1-3 \
      libnspr4 libnss3 libx11-xcb1 libxcomposite1 \
      libxdamage1 libxrandr2 libu2f-udev \
      libgbm1 libxshmfence1 libdrm2 libxkbcommon0; \
    \
    # ✅ CHROME ESTÁVEL - VERSÃO COMPATÍVEL
    wget -q -O /tmp/chrome.deb \
      "https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_139.0.7258.138-1_amd64.deb"; \
    apt-get install -y /tmp/chrome.deb; \
    rm -f /tmp/chrome.deb; \
    \
    # ✅ CHROMEDRIVER - VERSÃO COMPATÍVEL FIXA
    wget -q -O /tmp/chromedriver.zip \
      "https://chromedriver.storage.googleapis.com/139.0.7258.138/chromedriver_linux64.zip"; \
    unzip -q /tmp/chromedriver.zip -d /usr/local/bin/; \
    chmod +x /usr/local/bin/chromedriver; \
    rm -f /tmp/chromedriver.zip; \
    \
    # ✅ VERIFICA INSTALAÇÃO
    echo "Chrome version:"; \
    google-chrome --version; \
    echo "Chromedriver version:"; \
    chromedriver --version; \
    \
    # ✅ LIMPEZA SEGURA
    apt-get autoremove -y --purge; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/* /tmp/* /var/tmp/*;

WORKDIR /app

# Copia libs Python já instaladas no builder
COPY --from=builder /install /usr/local

# ✅ CRIA USUÁRIO NÃO-ROOT PARA SEGURANÇA
RUN groupadd -r chromeuser && useradd -r -g chromeuser -G audio,video chromeuser && \
    mkdir -p /home/chromeuser/Downloads && \
    chown -R chromeuser:chromeuser /home/chromeuser && \
    chown -R chromeuser:chromeuser /app && \
    chmod 755 /usr/local/bin/chromedriver

# ✅ ALTERA PARA USUÁRIO NÃO-ROOT 
USER chromeuser

# Copia o código da aplicação
COPY --chown=chromeuser:chromeuser . .

# Porta padrão (Render usa ${PORT})
EXPOSE 10000

# ✅ HEALTH CHECK SIMPLIFICADO
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-10000}/healthcheck || exit 1

# Web: Gunicorn; Workers/Beat usam startCommand no render.yaml
CMD ["sh", "-c", "gunicorn main:app --bind 0.0.0.0:${PORT:-10000} --timeout 120 --workers 1 --preload"]
