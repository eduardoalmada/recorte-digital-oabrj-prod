FROM python:3.10-slim

WORKDIR /app

# ✅ Instala Chrome via dpkg (MUITO MAIS ROBUSTO)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates wget unzip && \
    mkdir -p /tmp/chrome && cd /tmp/chrome && \
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    # ✅ CORREÇÃO: Usa dpkg que gerencia automaticamente diretórios e dependências
    dpkg -i google-chrome-stable_current_amd64.deb || apt-get install -f -y && \
    rm -rf /tmp/chrome && \
    google-chrome --version && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ✅ Instala ChromeDriver compatível (VERSÃO FUTURO-PROVA)
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}') && \
    echo "Installing ChromeDriver for Chrome $CHROME_VERSION" && \
    wget -q -O /tmp/chromedriver.zip \
        "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/$CHROME_VERSION/linux64/chromedriver-linux64.zip" || \
    wget -q -O /tmp/chromedriver.zip \
        "https://storage.googleapis.com/chrome-for-testing-public/$CHROME_VERSION/linux64/chromedriver-linux64.zip" && \
    unzip /tmp/chromedriver.zip -d /tmp/ && \
    mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/ && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /tmp/chromedriver.zip /tmp/chromedriver-linux64

# ✅ Dependências runtime mínimas (ESSENCIAIS)
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

# ✅ Instalação Python otimizada para RAM limitada
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    # Instala em lotes para evitar estouro de RAM
    pip install --no-cache-dir -r requirements.txt

# ✅ Usuário seguro com permissões adequadas
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    mkdir -p /home/appuser/Downloads && \
    chown -R appuser:appuser /app /home/appuser && \
    chmod 755 /home/appuser

USER appuser

# ✅ Configura variáveis de ambiente consistentes
ENV PORT=10000
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver

COPY --chown=appuser:appuser . .

EXPOSE 10000
CMD ["sh", "-c", "gunicorn main:app --bind 0.0.0.0:${PORT} --timeout 120 --workers 2 --preload"]
