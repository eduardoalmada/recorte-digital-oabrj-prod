# Usa imagem leve com Python
FROM python:3.10-slim

# Evita criação de arquivos .pyc e força flush de stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala dependências do sistema e o Google Chrome
RUN apt-get update && \
    apt-get install -y wget curl gnupg unzip ca-certificates \
    fonts-liberation libappindicator3-1 libasound2 libatk-bridge2.0-0 libatk1.0-0 \
    libcups2 libdbus-1-3 libgdk-pixbuf2.0-0 libnspr4 libnss3 libx11-xcb1 \
    libxcomposite1 libxdamage1 libxrandr2 xdg-utils libu2f-udev && \
    curl -sSL https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -o chrome.deb && \
    apt install -y ./chrome.deb && \
    rm chrome.deb && \
    apt-get clean

# Define a pasta de trabalho
WORKDIR /app

# Copia o conteúdo do projeto
COPY . .

# Instala o pip globalmente e todas as dependências do projeto
RUN python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt

# Garante que gunicorn está no PATH (por segurança)
RUN ln -s /usr/local/bin/gunicorn /usr/bin/gunicorn

# Comando padrão (Web service)
CMD ["gunicorn", "main:app"]
