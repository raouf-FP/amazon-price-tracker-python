import argparse
import csv
import random
import time
from datetime import datetime
from urllib.parse import quote_plus

import requests

BLOCK_MARKERS = [
    "robot check",
    "enter the characters you see below",
    "type the characters you see in this image",
    "we just need to make sure you're not a robot",
    "/errors/validatecaptcha",
]

BARE_HEADERS = {
    "User-Agent": "python-requests/2.x",
}

REALISTIC_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

def classify(resp):
    if resp.status_code == 429:
        return "blocked_429_rate_limited"
    if resp.status_code == 503:
        return "blocked_503_unavailable"
    if resp.status_code == 403:
        return "blocked_403_forbidden"
    low = resp.text.lower()
    if any(marker in low for marker in BLOCK_MARKERS):
        return "blocked_captcha"
    if resp.status_code == 200:
        return "ok"
    return f"http_{resp.status_code}"

def build_targets(asin, search_terms):
    if search_terms:
        return [(f"search:{t}", f"https://www.amazon.com/s?k={quote_plus(t)}") for t in search_terms]
    return [(f"product:{asin}", f"https://www.amazon.com/dp/{asin}")]

def run(asin, mode, max_attempts, delay, jitter, outfile, proxy=None, search_terms=None):
    headers = BARE_HEADERS if mode == "bare" else REALISTIC_HEADERS
    proxies = {"http": proxy, "https": proxy} if proxy else None
    targets = build_targets(asin, search_terms)
    rows = []
    blocked_at = None

    label = f"{mode}{' + proxy' if proxy else ''}{' + search' if search_terms else ''}"
    print(f"Mode: {label}  |  cycling {len(targets)} target(s)\n")
    for attempt in range(1, max_attempts + 1):
        tlabel, url = targets[(attempt - 1) % len(targets)]
        try:
            resp = requests.get(url, headers=headers, proxies=proxies, timeout=30)
            outcome = classify(resp)
            code = resp.status_code
        except requests.RequestException as e:
            outcome, code = f"error_{type(e).__name__}", "-"

        stamp = datetime.now().isoformat(timespec="seconds")
        rows.append({"attempt": attempt, "timestamp": stamp, "target": tlabel, "http": code, "outcome": outcome})
        print(f"  attempt {attempt:>3}  [{tlabel:<18}]  http={code}  -> {outcome}")

        if outcome.startswith("blocked"):
            blocked_at = attempt
            break

        time.sleep(delay + random.uniform(0, jitter))

    with open(outfile, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["attempt", "timestamp", "target", "http", "outcome"])
        writer.writeheader()
        writer.writerows(rows)

    print("\n" + "-" * 48)
    if blocked_at:
        print(f"RESULT ({label}): blocked after {blocked_at} request(s).")
    else:
        print(f"RESULT ({label}): survived all {max_attempts} requests without a detected block.")
    print(f"Log written to {outfile}")

def main():
    p = argparse.ArgumentParser(description="Measure how fast Amazon blocks a naive scraper")
    p.add_argument("--asin", default="B0CL5KNB9M")
    p.add_argument("--search", nargs="+", default=None,
                   help="Search terms to hit /s?k=... pages (far more heavily protected than product pages)")
    p.add_argument("--mode", choices=["bare", "realistic"], default="bare")
    p.add_argument("--max", type=int, default=30, dest="max_attempts", help="Max requests (keep modest)")
    p.add_argument("--delay", type=float, default=2.0, help="Base seconds between requests")
    p.add_argument("--jitter", type=float, default=1.5, help="Extra random seconds added to delay")
    p.add_argument("--proxy", default=None,
                   help="Proxy URL, e.g. http://user:pass@host:port (residential rotating recommended)")
    args = p.parse_args()

    kind = "search" if args.search else args.mode
    suffix = f"{kind}{'_proxy' if args.proxy else ''}"
    outfile = f"block_test_{suffix}.csv"
    run(args.asin, args.mode, args.max_attempts, args.delay, args.jitter,
        outfile, proxy=args.proxy, search_terms=args.search)

if __name__ == "__main__":
    main()
