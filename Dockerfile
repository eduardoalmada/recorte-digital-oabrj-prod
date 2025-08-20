# ========================
# STAGE 1 - BUILDER
# ========================
FROM python:3.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Instalar dependências mínimas só para build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc curl unzip ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependências Python em /install
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

# Instalar dependências do Chrome + ChromeDriver
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget curl unzip ca-certificates \
    fonts-liberation libappindicator3-1 libasound2 \
    libatk-bridge2.0-0 libatk1.0-0 libcups2 libdbus-1-3 \
    libnspr4 libnss3 libx11-xcb1 libxcomposite1 \
    libxdamage1 libxrandr2 xdg-utils libu2f-udev && \
    (apt-get install -y --no-install-recommends libgdk-pixbuf-2.0-0t64 || apt-get install -y --no-install-recommends libgdk-pixbuf-2.0-0 || true) && \
    # Instala o Google Chrome versão estável
    curl -sSL https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -o chrome.deb && \
    apt-get install -y ./chrome.deb && rm chrome.deb && \
    # Baixa o ChromeDriver compatível
    wget -q "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" -O /tmp/chromedriver.zip && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin/ && rm /tmp/chromedriver.zip && \
    chmod +x /usr/local/bin/chromedriver && \
    # Limpeza final
    apt-get autoremove -y && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /var/cache/apt/*

WORKDIR /app

# Copiar dependências instaladas do builder
COPY --from=builder /install /usr/local
# Copiar código da aplicação
COPY . .

# Porta padrão do Render
EXPOSE 10000

CMD ["sh", "-c", "gunicorn main:app --bind 0.0.0.0:${PORT:-10000}"]
