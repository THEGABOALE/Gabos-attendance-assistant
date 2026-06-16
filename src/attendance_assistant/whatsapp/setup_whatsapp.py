import sys
import asyncio
from pathlib import Path
from loguru import logger
from playwright.async_api import async_playwright

src_path = str(Path(__file__).resolve().parent.parent.parent)
if src_path not in sys.path:
    sys.path.append(src_path)

from attendance_assistant.config.settings import config

# Definimos una CARPETA de perfil en lugar de un archivo .json
PROFILE_DIR = config.BASE_DIR / "state" / "wa_profile"

async def main():
    logger.info("Inicializando configuración de WhatsApp Web con Perfil Persistente...")
    
    async with async_playwright() as p:
        # Usamos un contexto persistente para guardar todo el disco duro del navegador (IndexedDB)
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        # En los contextos persistentes, la página principal ya viene abierta
        page = context.pages[0] if context.pages else await context.new_page()

        await page.goto("https://web.whatsapp.com/")
        logger.info("ATENCIÓN: Por favor escanea el código QR con la app de WhatsApp en tu dispositivo móvil.")

        try:
            # Esperamos a que aparezca el panel lateral
            await page.wait_for_selector("#pane-side", timeout=120000)
            logger.success("Autenticación exitosa. Sincronizando llaves criptográficas...")
            
            # CRÍTICO: Esperamos 10 segundos extra para asegurar que WhatsApp guarde todo en la base de datos
            await page.wait_for_timeout(10000)
            logger.info(f"Perfil de sesión guardado exitosamente en la carpeta: {PROFILE_DIR.name}")
            
        except Exception as e:
            logger.error(f"Error al escanear el QR o tiempo de espera agotado: {e}")
        finally:
            await context.close()

if __name__ == "__main__":
    asyncio.run(main())