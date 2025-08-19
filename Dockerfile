FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependências do sistema + Chrome + ChromeDriver
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget curl unzip ca-certificates gnupg2 \
    fonts-liberation libappindicator3-1 libasound2 \
    libatk-bridge2.0-0 libatk1.0-0 libcups2 libdbus-1-3 \
    libnspr4 libnss3 libx11-xcb1 libxcomposite1 \
    libxdamage1 libxrandr2 xdg-utils libu2f-udev && \
    # Instala libgdk-pixbuf (com fallback para nomes diferentes)
    (apt-get install -y --no-install-recommends libgdk-pixbuf-2.0-0t64 || apt-get install -y --no-install-recommends libgdk-pixbuf-2.0-0 || true) && \
    # Instala o Google Chrome versão estável
    curl -sSL https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -o chrome.deb && \
    apt-get install -y ./chrome.deb && rm chrome.deb && \
    # Baixa o ChromeDriver compatível
    wget -q "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" -O /tmp/chromedriver.zip && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin/ && rm /tmp/chromedriver.zip && \
    chmod +x /usr/local/bin/chromedriver && \
    # Limpeza pesada para reduzir imagem
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/*

WORKDIR /app
COPY . .

# Instala dependências Python (com cache desabilitado)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

ENV PATH="/usr/local/bin:$PATH"

CMD ["sh", "-c", "gunicorn main:app --bind 0.0.0.0:${PORT:-10000}"]
