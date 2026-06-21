import argparse
import time
from urllib.parse import quote_plus

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

BLOCK_MARKERS = [
    "robot check",
    "enter the characters you see below",
    "type the characters you see in this image",
    "we just need to make sure you're not a robot",
    "/errors/validatecaptcha",
    "something went wrong on our end",
]

def make_driver(headed, proxy):
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
    from selenium import webdriver
    return webdriver.Chrome(service=Service(), options=opts)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--term", default="ps5")
    p.add_argument("--proxy", default=None)
    p.add_argument("--headed", action="store_true")
    args = p.parse_args()

    url = f"https://www.amazon.com/s?k={quote_plus(args.term)}"
    label = f"browser{' + proxy' if args.proxy else ''}"
    print(f"Mode: {label}  |  {url}\n")

    driver = make_driver(args.headed, args.proxy)
    try:
        driver.get(url)
        time.sleep(5)
        page = driver.page_source.lower()

        if any(m in page for m in BLOCK_MARKERS):
            print(f"RESULT ({label}): BLOCKED (CAPTCHA / robot check page).")
            return

        results = driver.find_elements(By.CSS_SELECTOR, "div[data-component-type='s-search-result']")
        if results:
            print(f"RESULT ({label}): SUCCESS, loaded {len(results)} search results.")
        else:
            print(f"RESULT ({label}): UNCLEAR, no block detected, but no result tiles found either.")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
