import sys
import asyncio
from pathlib import Path
from loguru import logger
from playwright.async_api import async_playwright

# Resolución de rutas
src_path = str(Path(__file__).resolve().parent.parent.parent)
if src_path not in sys.path:
    sys.path.append(src_path)

from attendance_assistant.config.settings import config

async def main():
    logger.info("Inicializando configuración de WhatsApp Web...")
    
    async with async_playwright() as p:
        # Headless debe ser False para que puedas ver y escanear el QR
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://web.whatsapp.com/")
        logger.info("ATENCIÓN: Por favor escanea el código QR con la app de WhatsApp en tu dispositivo móvil.")

        try:
            # Esperamos a que aparezca el panel lateral de chats (indicador de login exitoso)
            await page.wait_for_selector("#pane-side", timeout=120000)
            logger.success("Autenticación de WhatsApp exitosa.")

            # Guardamos el estado de forma persistente
            config.WA_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            await context.storage_state(path=config.WA_STATE_FILE)
            logger.info(f"Credenciales de sesión almacenadas en: {config.WA_STATE_FILE.name}")
            
        except Exception as e:
            logger.error("Tiempo de espera agotado o error al escanear el QR. Intenta nuevamente.")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())