from playwright.sync_api import sync_playwright
from random import choice, randint
from .user_agents import USER_AGENTS
import random
import time
import json
import os

USER_DATA_DIR = "user_data"

def get_hardware_concurrency():
    return choice([2, 4, 6, 8, 12])

def get_device_memory():
    return choice([4, 8, 16])

def get_viewport():
    return choice([
        {"width": 1280, "height": 800},
        {"width": 1366, "height": 768},
        {"width": 1440, "height": 900},
        {"width": 1920, "height": 1080},
    ])

def get_browser_context():
    p = sync_playwright().start()

    context = p.chromium.launch_persistent_context(
        user_data_dir=USER_DATA_DIR,
        headless=False,
        user_agent=choice(USER_AGENTS),
        viewport=get_viewport(),
        java_script_enabled=True,
        ignore_https_errors=True,
        locale="es-MX",
        timezone_id="America/Mexico_City",
    )

    # Carga cookies persistentes si existen
    cookies_path = f"{USER_DATA_DIR}.json"
    if os.path.exists(cookies_path):
        with open(cookies_path, "r") as f:
            cookies = json.load(f)
            context.add_cookies(cookies)

    return p, context

def save_browser_state(context):
    try:
        cookies = context.cookies()
        os.makedirs(USER_DATA_DIR, exist_ok=True)
        with open(f"{USER_DATA_DIR}.json", "w") as f:
            json.dump(cookies, f)
    except Exception as e:
        print(f"[ERROR] No se pudo guardar estado: {e}")

def simulate_user_interaction(page):
    try:
        page.mouse.move(100, 200)
        page.keyboard.press("Tab")
        page.mouse.wheel(0, randint(200, 800))
        time.sleep(1.5)
    except Exception as e:
        print(f"[WARN] No se pudo simular interacción: {e}")
