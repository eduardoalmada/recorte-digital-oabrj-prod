FROM python:3.10-slim

WORKDIR /app

# ✅ Instala Chrome + dependências (para todos os serviços)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates wget unzip gnupg \
        libnss3 libatk1.0-0 libatk-bridge2.0-0 \
        libx11-xcb1 libxcomposite1 libxdamage1 libxfixes3 \
        libxrandr2 libgbm1 libasound2 \
        libxkbcommon0 libwayland-client0 libwayland-server0 \
        libminizip1 libevent-2.1-7 libharfbuzz0b \
        libsecret-1-0 fonts-liberation \
        libappindicator3-1 xdg-utils && \
    \
    wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get install -y --no-install-recommends /tmp/chrome.deb && \
    rm -f /tmp/chrome.deb && \
    \
    CHROME_VERSION=$(google-chrome --version | awk '{print $3}') && \
    wget -q -O /tmp/chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip" && \
    unzip /tmp/chromedriver.zip -d /tmp/ && \
    mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/ && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /tmp/chromedriver.zip /tmp/chromedriver-linux64 && \
    \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ✅ Instalação Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ✅ Usuário seguro
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    chown -R appuser:appuser /app
USER appuser

COPY --chown=appuser:appuser . .

EXPOSE 10000
# ✅ SEM CMD fixo - definido no render.yaml
