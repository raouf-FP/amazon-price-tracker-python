import argparse
import json
import os
import random
import re
import time
from datetime import datetime, timezone

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

PRICE_SELECTORS = [
    "#corePriceDisplay_desktop_feature_div .a-price .a-offscreen",
    "#corePrice_feature_div .a-price .a-offscreen",
    "#corePriceDisplay_desktop_feature_div .a-offscreen",
    "#corePrice_feature_div .a-offscreen",
    "#apex_desktop .a-price .a-offscreen",
    "#buybox .a-price .a-offscreen",
    ".a-price .a-offscreen",
]

BLOCK_MARKERS = [
    "robot check",
    "enter the characters you see below",
    "type the characters you see in this image",
    "we just need to make sure you're not a robot",
    "automated access to amazon data",
    "/errors/validatecaptcha",
]

def parse_price(raw):
    if not raw:
        return None, None
    text = raw.replace("\n", " ").strip()
    m = re.search(r"([^\d\s]{0,3})\s?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)", text)
    if not m:
        return None, None
    currency = (m.group(1) or "").strip() or "?"
    num = m.group(2)
    if "," in num and "." in num:
        if num.rfind(",") > num.rfind("."):
            num = num.replace(".", "").replace(",", ".")
        else:
            num = num.replace(",", "")
    elif "," in num:
        num = num.replace(",", ".") if re.search(r",\d{2}$", num) else num.replace(",", "")
    try:
        return float(num), currency
    except ValueError:
        return None, None

def make_driver(headed=False, proxy=None):
    opts = Options()
    if not headed:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    if proxy:
        from proxy_helper import apply_proxy
        apply_proxy(opts, proxy)
    return webdriver.Chrome(service=Service(), options=opts)

def looks_blocked(page_source):
    low = page_source.lower()
    return any(marker in low for marker in BLOCK_MARKERS)

def scrape_price(driver, asin):
    url = f"https://www.amazon.com/dp/{asin}"
    driver.get(url)
    time.sleep(random.uniform(2.0, 4.0))

    if looks_blocked(driver.page_source):
        return {"status": "blocked"}

    for selector in PRICE_SELECTORS:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        if not elements:
            continue
        raw = (elements[0].get_attribute("textContent") or "").strip()
        value, currency = parse_price(raw)
        if value is not None:
            return {"status": "ok", "raw": raw, "value": value, "currency": currency}

    return {"status": "price_not_found"}

def record(asin, result, db_path):
    data = {}
    if os.path.exists(db_path):
        with open(db_path) as f:
            data = json.load(f)
    data.setdefault(asin, []).append(
        {"timestamp": datetime.now(timezone.utc).isoformat(), **result}
    )
    with open(db_path, "w") as f:
        json.dump(data, f, indent=2)

def run_once(asins, headed, db_path, proxy=None):
    driver = make_driver(headed=headed, proxy=proxy)
    try:
        for asin in asins:
            result = scrape_price(driver, asin)
            record(asin, result, db_path)
            stamp = datetime.now().strftime("%H:%M:%S")
            if result["status"] == "ok":
                print(f"[{stamp}] {asin}: {result['currency']}{result['value']}  (raw: {result['raw']!r})")
            else:
                print(f"[{stamp}] {asin}: {result['status'].upper()}")
            time.sleep(random.uniform(3.0, 6.0))
    finally:
        driver.quit()

def main():
    p = argparse.ArgumentParser(description="Track Amazon product prices")
    p.add_argument("--asins", nargs="+", required=True, help="One or more Amazon ASINs")
    p.add_argument("--headed", action="store_true", help="Show the browser window")
    p.add_argument("--db", default="price_history.json", help="JSON history file")
    p.add_argument("--loop", action="store_true", help="Keep running on a schedule")
    p.add_argument("--every", type=float, default=12, help="Hours between checks with --loop")
    p.add_argument("--proxy", default=None, help="Proxy URL, e.g. http://user:pass@host:port")
    args = p.parse_args()

    run_once(args.asins, args.headed, args.db, proxy=args.proxy)
    if args.loop:
        print(f"Looping every {args.every} h. Ctrl+C to stop.")
        while True:
            time.sleep(args.every * 3600)
            run_once(args.asins, args.headed, args.db, proxy=args.proxy)

if __name__ == "__main__":
    main()
