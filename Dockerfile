FROM python:3.10-slim

WORKDIR /app

# ✅ Instala Chrome minimalista e seguro
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates wget unzip binutils && \
    mkdir -p /tmp/chrome && cd /tmp/chrome && \
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    ar x google-chrome-stable_current_amd64.deb && \
    tar -xf data.tar.* && \
    mv ./opt/google/chrome /opt/ && \
    mv ./usr/bin/google-chrome-stable /usr/bin/google-chrome && \
    ln -sf /usr/bin/google-chrome /opt/google/chrome/chrome && \
    rm -rf /tmp/chrome && \
    google-chrome --version && \
    apt-get purge -y binutils && \
    apt-get autoremove -y && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ✅ Instala ChromeDriver compatível
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}') && \
    wget -q -O /tmp/chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip" && \
    unzip /tmp/chromedriver.zip -d /tmp/ && \
    mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/ && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /tmp/chromedriver.zip /tmp/chromedriver-linux64

# ✅ Dependências runtime mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
        libnss3 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libx11-xcb1 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libasound2 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ✅ Instalação Python com cache
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ✅ Usuário seguro
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    chown -R appuser:appuser /app
USER appuser

COPY --chown=appuser:appuser . .

EXPOSE 10000
CMD ["sh", "-c", "gunicorn main:app --bind 0.0.0.0:${PORT:-10000} --timeout 120 --workers 2 --preload"]
