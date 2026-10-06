#!/usr/bin/env python3
"""
Staples RTX 5080 stock monitor.

Monitors Staples item 24764611 and sends an ntfy push notification when the
product becomes purchasable after previously being unavailable.

Requirements:
    pip install -r requirements.txt
    playwright install chromium

Set:
    NTFY_TOPIC="your-private-random-topic"

Optional:
    CHECK_INTERVAL_SECONDS=120
    STATE_FILE="staples_stock_state.json"
"""

import json
import os
import re
import time
from datetime import datetime, timezone

import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

URL = "https://www.staples.com/zotac-solid-oc-nvidia-geforce-rtx-5080-pci-express-5-0-16gb-gddr7-gaming-graphics-card-2640mhz-white-zt-b50800q-10a/product_24764611"
ITEM = "24764611"
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL_SECONDS", "120"))
STATE_FILE = os.getenv("STATE_FILE", "staples_stock_state.json")
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "")

# Text that strongly indicates the item is unavailable.
OUT_OF_STOCK_PATTERNS = [
    r"\bout of stock\b",
    r"\bunavailable\b",
    r"\bcurrently unavailable\b",
    r"\bnot available\b",
]

# Text/buttons that indicate a purchase action is possible.
PURCHASE_PATTERNS = [
    r"\badd to cart\b",
    r"\bbuy now\b",
    r"\bship it\b",
]

def load_previous_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"in_stock": False}

def save_state(in_stock, price=None):
    state = {
        "in_stock": in_stock,
        "price": price,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def notify_ntfy(price=None):
    if not NTFY_TOPIC:
        print("STOCK ALERT (NTFY_TOPIC is not configured):", URL)
        return

    message = f"ZOTAC RTX 5080 WHITE IS IN STOCK at Staples!\nItem {ITEM}"
    if price:
        message += f"\nPrice shown: {price}"
    message += f"\n{URL}"

    response = requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={
            "Title": "RTX 5080 IN STOCK",
            "Priority": "max",
            "Tags": "rotating_light,computer",
            "Click": URL,
        },
        timeout=15,
    )
    response.raise_for_status()
    print("Notification sent.")

def extract_price(text):
    matches = re.findall(r"\$[\d,]+(?:\.\d{2})?", text)
    return matches[0] if matches else None

def check_page(page):
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)

    # Give Staples' client-side inventory controls time to render.
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except PlaywrightTimeoutError:
        pass

    page.wait_for_timeout(3000)

    text = page.locator("body").inner_text(timeout=15000)
    lower = text.lower()

    # Inspect visible buttons/links separately because some stock text can
    # appear in unrelated recommendation modules.
    controls = page.locator("button, a")
    control_text = ""
    try:
        control_text = controls.all_inner_texts()
    except Exception:
        pass
    controls_lower = " ".join(control_text).lower()

    out_of_stock = any(re.search(p, lower) for p in OUT_OF_STOCK_PATTERNS)
    purchase_available = any(re.search(p, controls_lower) for p in PURCHASE_PATTERNS)

    # A purchase control is the stronger signal. If the page explicitly says
    # out of stock and has no purchase control, treat it as unavailable.
    in_stock = purchase_available and not out_of_stock

    price = extract_price(text)
    return in_stock, price

def main():
    previous = load_previous_state()
    previous_stock = bool(previous.get("in_stock", False))

    print(f"Monitoring Staples item {ITEM}")
    print(f"Check interval: {CHECK_INTERVAL}s")
    print(URL)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1440, "height": 1200},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/140.0.0.0 Safari/537.36"
            ),
        )

        try:
            while True:
                try:
                    in_stock, price = check_page(page)
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"[{now}] in_stock={in_stock} price={price}")

                    # Only alert on an actual transition from unavailable -> available.
                    if in_stock and not previous_stock:
                        notify_ntfy(price)

                    save_state(in_stock, price)
                    previous_stock = in_stock

                except Exception as exc:
                    print(f"Check failed: {type(exc).__name__}: {exc}")

                time.sleep(CHECK_INTERVAL)
        finally:
            browser.close()

if __name__ == "__main__":
    main()
