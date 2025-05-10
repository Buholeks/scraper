import click
import time
import json
import re
from typing import Dict
from utils.browser_config import get_browser_context
from utils.page_handler import setup_page_handlers
from utils.captcha_monitor import (
    with_captcha_check,
    CaptchaDetected,
)


def process_image_url(image_url: str) -> str:
    if image_url.startswith("//"):
        image_url = "https:" + image_url
    return image_url


@with_captcha_check
def navigate_to_product(page, url: str, delay: int = 2):
    page.goto(url)
    time.sleep(delay)


@with_captcha_check
def scrape_product_details(page, url: str) -> Dict:
    retry_count = 0
    max_retries = 3

    while retry_count < max_retries:
        try:
            navigate_to_product(page, url)
            page.wait_for_selector(
                ".product-intro__head-sku-text, .product-intro__head-name",
                timeout=10000,
                state="visible",
            )

            sku_element = page.locator(".product-intro__head-sku-text").first
            sku = (
                sku_element.text_content().strip().replace("SKU:", "").strip()
                if sku_element
                else None
            )

            title_element = page.locator(".product-intro__head-name").first
            title = title_element.text_content().strip() if title_element else None

            price = None
            price_original = None

            try:
                print("[ORIGINAL] Buscando precio actual en: div.from.original")
                price_div = page.locator("div.from.original").first
                if price_div:
                    text = price_div.inner_text().strip()
                    match = re.search(r"\$MXN[\d.,]+", text)
                    if match:
                        price = match.group(0)
                        print(f"✅ Precio original: {price}")
                    else:
                        print("⚠️ No se encontró precio en texto original.")

                    print("[ORIGINAL] Buscando precio tachado en: del.del-price")
                    original_del = page.locator("del.del-price").first
                    if original_del:
                        price_original = original_del.text_content().strip()
                    print(f"📉 Precio tachado: {price_original}")

            except Exception as e:
                click.secho(
                    f"[WARN] Error obteniendo precios (estimated): {str(e)}",
                    fg="yellow",
                )
            image_url = None
            try:
                container = page.locator(".crop-image-container").first
                if container.count() > 0:
                    src = container.get_attribute("data-before-crop-src")
                    if src:
                        image_url = process_image_url(src)
            except Exception as e:
                print(f"[WARN] Error obteniendo imagen principal: {e}")

            images = [image_url] if image_url else []

            if not (sku or title):
                raise Exception("No se pudo extraer información básica del producto")

            return {
                "url": url,
                "sku": sku,
                "title": title,
                "price": price,
                "price_original": price_original,
                "images": images,
                "modo": "original",
                "scraped_at": int(time.time()),
            }

        except CaptchaDetected:
            raise

        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                raise Exception(f"Falló tras varios intentos: {str(e)}")
            click.secho(f"[Retry] {retry_count}/{max_retries} – {str(e)}", fg="yellow")
            time.sleep(2 * retry_count)

    return {}


def scrape_single_product(url: str) -> dict:
    from utils.browser_config import get_browser_context
    from utils.page_handler import setup_page_handlers

    playwright, browser, context = get_browser_context()
    result = {}

    try:
        page = context.new_page()
        setup_page_handlers(page)
        navigate_to_product(page, "https://shein.com.mx")
        result = scrape_product_details(page, url)
    except Exception as e:
        print(f"Error al scrapear el producto: {str(e)}")
    finally:
        context.close()
        browser.close()
        playwright.stop()

    return result
