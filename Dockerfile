# ========================
# STAGE 1 - BUILDER
# ========================
FROM python:3.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    CHROME_VERSION=140.0.7339.80 \
    CHROMEDRIVER_VERSION=140.0.7339.80

WORKDIR /app

# Instala dependências e o Google Chrome
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget unzip ca-certificates fontconfig locales \
    libglib2.0-0 libnss3 libx11-6 libx11-xcb1 libxcomposite1 \
    libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 \
    libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
    libpango-1.0-0 libcairo2 libasound2 \
    && wget -O /tmp/chrome.deb \
    "https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_${CHROME_VERSION}-1_amd64.deb" \
    && apt-get install -y --no-install-recommends /tmp/chrome.deb \
    && rm -f /tmp/chrome.deb \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Instala ChromeDriver fixado e move para o PATH
RUN wget -O /tmp/chromedriver.zip \
    "https://storage.googleapis.com/chrome-for-testing-public/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip" \
    && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
    && chmod +x /usr/local/bin/chromedriver \
    && rm -f /tmp/chromedriver*

# Extrai dependências do Chrome
RUN mkdir -p /chrome-deps && \
    ldd /usr/bin/google-chrome | tr -s '[:blank:]' '\n' | grep '^/' | \
    xargs -I {} cp --parents -v {} /chrome-deps/ || true

# Instala dependências Python
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt


# ========================
# STAGE 2 - FINAL IMAGE
# ========================
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/root/.local/bin:$PATH

WORKDIR /app

# Copia dependências do Chrome do builder
COPY --from=builder /chrome-deps/ /

# Copia binários do Chrome e ChromeDriver
COPY --from=builder /usr/bin/google-chrome /usr/bin/google-chrome
COPY --from=builder /usr/local/bin/chromedriver /usr/local/bin/chromedriver

# Copia dependências Python já instaladas
COPY --from=builder /root/.local /root/.local

# Copia código da aplicação
COPY . .

# Porta padrão do Flask/Gunicorn
EXPOSE 8000

# Comando de inicialização
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:8000", "--workers", "2"]
