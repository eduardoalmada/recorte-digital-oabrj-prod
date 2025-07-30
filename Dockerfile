# Usa imagem leve com Python
FROM python:3.10-slim

# Evita criação de arquivos .pyc e força flush de stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala dependências do sistema e o Google Chrome
RUN apt-get update && \
    apt-get install -y wget curl gnupg unzip ca-certificates gnupg2 --no-install-recommends && \
    apt-get install -y \
    fonts-liberation libappindicator3-1 libasound2 libatk-bridge2.0-0 libatk1.0-0 \
    libcups2 libdbus-1-3 libgdk-pixbuf2.0-0 libnspr4 libnss3 libx11-xcb1 \
    libxcomposite1 libxdamage1 libxrandr2 xdg-utils libu2f-udev --no-install-recommends && \
    curl -sSL https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -o chrome.deb && \
    apt install -y ./chrome.deb && \
    rm chrome.deb && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Define a pasta de trabalho
WORKDIR /app

# Copia os arquivos do projeto
COPY . .

# Instala pip e dependências com caminho explícito
RUN /usr/local/bin/python -m pip install --upgrade pip && \
    /usr/local/bin/python -m pip install -r requirements.txt

# Comando padrão (Web service)
ENV PATH="/usr/local/bin:$PATH"
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:$PORT"]
