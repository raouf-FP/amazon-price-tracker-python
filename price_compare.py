import argparse
import re

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

PRICE_ANCHORS = [
    "corePriceDisplay_desktop_feature_div",
    "corePrice_feature_div",
    "apex_desktop",
    "priceblock_ourprice",
    "priceblock_dealprice",
]

def extract_price(html):
    for anchor in PRICE_ANCHORS:
        idx = html.find(anchor)
        if idx != -1:
            window = html[idx:idx + 2500]
            m = re.search(r'a-offscreen"?[^>]*>\s*([^<]+)</span>', window)
            if m:
                return m.group(1).strip()
    m = re.search(r'class="a-offscreen">\s*([^<]+)</span>', html)
    return m.group(1).strip() if m else None

def detect_location(html):
    m = re.search(r'glow-ingress-line2[^>]*>\s*([^<]+?)\s*<', html)
    return m.group(1).strip() if m else "unknown"

def ship_status(html):
    low = html.lower()
    if "cannot be shipped to your selected delivery location" in low:
        return "RESTRICTED, cannot ship to detected location"
    if "no featured offers available" in low:
        return "no featured offer shown"
    return "normal / shippable view"

def fetch(asin, proxy):
    url = f"https://www.amazon.com/dp/{asin}"
    proxies = {"http": proxy, "https": proxy} if proxy else None
    try:
        r = requests.get(url, headers=HEADERS, proxies=proxies, timeout=30)
    except requests.RequestException as e:
        return {"error": f"{type(e).__name__}: {e}"}
    html = r.text
    return {
        "http": r.status_code,
        "location": detect_location(html),
        "shipping": ship_status(html),
        "price": extract_price(html),
    }

def show(title, data):
    print(f"\n=== {title} ===")
    if "error" in data:
        print(f"  ERROR: {data['error']}")
        return
    print(f"  HTTP:      {data['http']}")
    print(f"  Deliver to: {data['location']}")
    print(f"  Shipping:  {data['shipping']}")
    print(f"  Price:     {data['price'] if data['price'] else '(none found)'}")

def main():
    p = argparse.ArgumentParser(description="Compare Amazon price by location (direct vs proxy)")
    p.add_argument("--asin", required=True)
    p.add_argument("--proxy", default=None, help="Proxy URL, e.g. http://user:pass@host:port")
    args = p.parse_args()

    show("DIRECT (your real connection)", fetch(args.asin, None))
    if args.proxy:
        show("VIA US PROXY", fetch(args.asin, args.proxy))
        print("\nDifferences between the two mean Amazon is serving different data")
        print("based on where the request appears to come from.")
    else:
        print("\n(Run again with --proxy to compare against a proxied request.)")

if __name__ == "__main__":
    main()
