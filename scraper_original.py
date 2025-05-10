import time
import random
import re
import json
import os
from typing import Dict
from playwright.sync_api import sync_playwright


class CaptchaDetected(Exception):
    pass


# ------------------------- CONFIGURACIÓN -------------------------
STEALTH_SETTINGS = {
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "viewport": {"width": 1280, "height": 800},
    "locale": "es-MX",
    "args": ["--disable-blink-features=AutomationControlled", "--start-maximized"],
}

HEADERS = {"Accept-Language": "es-MX,es;q=0.9", "Referer": "https://www.shein.com.mx/"}


# ------------------------- CACHÉ DE SELECTORES -------------------------
class SelectorCache:
    def __init__(self):
        self.cache_file = "shein_selectors.json"
        self.cache = self._load_cache()

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            with open(self.cache_file, "r") as f:
                return json.load(f)
        return {
            "price": ["#productMainPriceId", "[id*='Price']"],
            "original_price": [
                "#productDiscountId .productDiscountInfo__retail",
                "[class*='retail']",
            ],
            "image": [".crop-image-container"],
        }

    def save_cache(self):
        with open(self.cache_file, "w") as f:
            json.dump(self.cache, f)

    def get_selectors(self, element_type):
        return self.cache.get(element_type, [])


# ------------------------- FUNCIONES AUXILIARES -------------------------
def random_delay(min_sec: float, max_sec: float):
    time.sleep(random.uniform(min_sec, max_sec))


def simulate_human_interaction(page):
    try:
        page.mouse.move(random.randint(100, 500), random.randint(100, 500))
        random_delay(0.1, 0.3)
        page.mouse.wheel(0, random.randint(200, 400))
        random_delay(0.2, 0.5)
    except Exception as e:
        print(f"[WARN] Error en interacción simulada: {e}")


def detect_captcha(page) -> bool:
    captcha_selectors = [
        ".geetest_panel_box",
        ".verify-wrap",
        "#captchaContainer",
        "iframe[src*='captcha']",
    ]

    for selector in captcha_selectors:
        try:
            if page.locator(selector).first.is_visible(timeout=1000):
                print(f"[CAPTCHA] Detectado: {selector}")
                return True
        except:
            continue
    return False


def handle_captcha(page, timeout=120):
    if not detect_captcha(page):
        return True

    print("\n🛑 CAPTCHA detectado. Por favor resuélvelo manualmente...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        if not detect_captcha(page):
            random_delay(1, 2)
            if not detect_captcha(page):
                print("✅ CAPTCHA resuelto correctamente")
                return True
        random_delay(2, 3)

    raise CaptchaDetected("Tiempo agotado para resolver CAPTCHA")


def process_image_url(image_url: str) -> str:
    if not image_url:
        return None

    if image_url.startswith("//"):
        return f"https:{image_url}"
    elif image_url.startswith("/"):
        return f"https://www.shein.com.mx{image_url}"

    return image_url


# ------------------------- EXTRACCIÓN RESISTENTE -------------------------
def extract_with_fallback(page, selector_type, cache):
    """Extrae elementos con sistema de fallback inteligente"""
    selectors = cache.get_selectors(selector_type)

    for selector in selectors:
        try:
            element = page.locator(selector).first
            if element.count() > 0:
                return element
        except:
            continue

    # Fallback 1: Búsqueda semántica
    if selector_type == "price":
        elements = page.locator("[id*='price'], [class*='price']").all()
        if len(elements) > 0:
            return elements[0]

    # Fallback 2: Análisis visual básico
    visual_elements = page.evaluate(
        """(selector_type) => {
        const elements = Array.from(document.querySelectorAll('span, div, p'));
        return elements.filter(el => {
            const text = el.textContent.trim();
            const style = getComputedStyle(el);
            
            if (selector_type === 'price') {
                return /\\$[0-9,.]+/.test(text) && 
                       (style.color.includes('38') || style.fontWeight >= '600');
            }
            return false;
        });
    }""",
        selector_type,
    )

    return visual_elements[0] if visual_elements else None


def extract_prices_resistant(page, cache):
    """Extracción robusta de precios"""
    # Precio actual
    price_element = extract_with_fallback(page, "price", cache)
    current_price = price_element.text_content().strip() if price_element else None

    # Precio original
    original_element = extract_with_fallback(page, "original_price", cache)
    original_price = (
        original_element.text_content().strip() if original_element else None
    )

    # Limpieza de precios
    if current_price:
        current_price = re.sub(r"\s+", "", current_price.split()[0])
    if original_price:
        original_price = re.sub(r"\s+", "", original_price.split()[0])

    return current_price, original_price


# ------------------------- FUNCIÓN PRINCIPAL -------------------------
def scrape_single_product(url: str) -> Dict:
    result = {
        "url": url,
        "sku": None,
        "title": None,
        "price": None,
        "price_original": None,
        "images": [],
        "image": None,
        "status": "error",
        "message": "Error desconocido",
        "scraped_at": int(time.time()),
    }

    selector_cache = SelectorCache()

    with sync_playwright() as p:
        browser = None
        try:
            # Configuración del navegador
            browser = p.chromium.launch_persistent_context(
                user_data_dir="./shein_profile",
                headless=False,
                viewport=STEALTH_SETTINGS["viewport"],
                user_agent=STEALTH_SETTINGS["user_agent"],
                locale=STEALTH_SETTINGS["locale"],
                args=STEALTH_SETTINGS["args"],
            )

            page = browser.new_page()
            page.set_extra_http_headers(HEADERS)
            page.add_init_script(
                """
                delete navigator.__proto__.webdriver;
                Object.defineProperty(navigator, 'webdriver', { get: () => false });
            """
            )

            # Navegación
            print(f"🌐 Navegando a: {url}")
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            random_delay(1, 2)

            # Interacciones
            simulate_human_interaction(page)
            handle_captcha(page)

            # Extracción de datos
            # 1. Precios (con sistema resistente)
            result["price"], result["price_original"] = extract_prices_resistant(
                page, selector_cache
            )

            # 2. SKU
            try:
                sku_element = page.locator(".product-intro__head-sku-text").first
                if sku_element.count() > 0:
                    result["sku"] = (
                        sku_element.text_content().strip().replace("SKU:", "").strip()
                    )
            except:
                pass

            # 3. Título
            try:
                title_element = page.locator(".product-intro__head-name").first
                if title_element.count() > 0:
                    result["title"] = title_element.text_content().strip()
            except:
                pass

            # 4. Imagen (con caché de selectores)
            try:
                img_container = extract_with_fallback(page, "image", selector_cache)
                if img_container:
                    src = img_container.get_attribute("data-before-crop-src")
                    if src:
                        result["image"] = process_image_url(src)
                        result["images"] = [result["image"]]
            except Exception as e:
                print(f"[WARN] Error obteniendo imagen: {e}")

            # Validación final
            if result["price"] and (result["sku"] or result["title"]):
                result["status"] = "success"
                result["message"] = "Scraping completado"
            else:
                result["message"] = "Faltan datos esenciales"

        except CaptchaDetected as e:
            result["message"] = str(e)
            result["status"] = "captcha_error"
        except Exception as e:
            result["message"] = str(e)
        finally:
            if browser:
                browser.close()
            selector_cache.save_cache()

    return result


# ------------------------- EJECUCIÓN DIRECTA (OPCIONAL) -------------------------
if __name__ == "__main__":
    # Solo para pruebas locales
    print("⚠️ Este script está diseñado para integrarse con Laravel")
    print("Por favor usa la función scrape_single_product(url) desde tu aplicación")
