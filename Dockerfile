FROM python:3.10-slim

# Configurações Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Variável para escolher versão do ChromeDriver compatível
ENV CHROME_VERSION=127.0.6533.119-1
ENV CHROMEDRIVER_VERSION=127.0.6533.119

# Instalar dependências do sistema + Chrome + ChromeDriver
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget curl unzip ca-certificates \
    fonts-liberation libappindicator3-1 libasound2 libatk-bridge2.0-0 libatk1.0-0 \
    libcups2 libdbus-1-3 libgdk-pixbuf-2.0-0 libnspr4 libnss3 libx11-xcb1 \
    libxcomposite1 libxdamage1 libxrandr2 xdg-utils libu2f-udev && \
    # Instala o Google Chrome versão estável
    curl -sSL https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -o chrome.deb && \
    apt-get install -y ./chrome.deb && \
    rm chrome.deb && \
    # Baixa o ChromeDriver na versão compatível
    wget -q "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" -O /tmp/chromedriver.zip && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
    rm /tmp/chromedriver.zip && \
    chmod +x /usr/local/bin/chromedriver && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Definir diretório de trabalho
WORKDIR /app

# Copiar código do projeto
COPY . .

# Atualizar pip e instalar dependências Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# Garantir que Chrome e ChromeDriver estejam no PATH
ENV PATH="/usr/local/bin:$PATH"

# Comando padrão (Gunicorn para produção)
CMD ["sh", "-c", "gunicorn main:app --bind 0.0.0.0:${PORT:-10000}"]
