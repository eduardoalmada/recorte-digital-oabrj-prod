# install_playwright.py
import os
from playwright.sync_api import sync_playwright

# Defina o diretório de instalação dos navegadores
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/app/ms-playwright"

with sync_playwright() as p:
    print("🚀 Instalando navegadores Playwright...")
    p.install()
    print("✅ Navegadores instalados em /app/ms-playwright")
