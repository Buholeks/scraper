from playwright.sync_api import Page
import click
import time
from functools import wraps

class CaptchaDetected(Exception):
    pass

def monitor_for_captcha(page: Page) -> bool:
    selectors = [
        ".geetest_panel_box",
        ".captcha_click_wrapper",
        "[captcha-click-image]",
        ".captcha_btn_click_wrapper",
        "#captchaContainer",
    ]
    for selector in selectors:
        el = page.locator(selector)
        try:
            if el.count() > 0 and el.first.is_visible(timeout=500):
                print(f"[CAPTCHA] Detectado: {selector}")
                return True
        except:
            continue
    return False

def handle_manual_captcha(page: Page, timeout: int = 180):
    click.secho("🧠 Captcha detectado. Por favor, resuélvelo manualmente...", fg="yellow")
    start_time = time.time()
    resolved = False

    while time.time() - start_time < timeout:
        if not monitor_for_captcha(page):
            # Damos un segundo más para evitar el rechazo por respuesta inmediata
            time.sleep(1)
            click.secho("✅ Captcha resuelto manualmente.", fg="green")
            resolved = True
            break
        time.sleep(1)

    if not resolved:
        click.secho("❌ Tiempo agotado esperando la resolución del captcha.", fg="red")
    return resolved

def with_captcha_check(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        page = next((a for a in args if hasattr(a, "locator")), None)
        if not page:
            return func(*args, **kwargs)

        if monitor_for_captcha(page):
            if not handle_manual_captcha(page):
                raise CaptchaDetected("Captcha no resuelto a tiempo (manual)")

        result = func(*args, **kwargs)

        if monitor_for_captcha(page):
            if not handle_manual_captcha(page):
                raise CaptchaDetected("Captcha no resuelto después de la ejecución")

        return result

    return wrapper
