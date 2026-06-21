# Amazon Price Tracker (Python)

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A small Amazon price tracker built with Selenium, plus a few scripts I used to work out what actually gets a scraper blocked and why a basic one keeps grabbing the wrong price.

I wrote up the whole thing here: **[How to Build an Amazon Price Tracker in Python](https://www.flashproxy.com/blog)** (swap in the final post link once it's up).

## What's in here

- `tracker.py` reads a product's price and saves it over time.
- It grabs the actual buy-box price instead of the first `.a-price` it finds (which can be an accessory, or the value duplicated into `$449.00$449.00`).
- `plot_prices.py` draws a chart from the saved history.
- `proxy_helper.py` lets you run the browser through a proxy that needs a username/password, without the Chrome login popup.
- A few diagnostic scripts (`block_test.py`, `search_browser_test.py`, `price_compare.py`) that I used while testing, kept here in case they're useful.

![clean price](assets/clean-price.png)

![price chart](assets/price-chart.png)

## Setup

You need Python 3.9+ and Chrome installed.

```bash
pip install -r requirements.txt
```

Selenium pulls the right ChromeDriver itself, so there's no extra setup.

## Running it

Grab a product's ASIN (the code after `/dp/` in the URL) and run:

```bash
python tracker.py --asins B0F1J12R6N --headed
```

`--headed` opens a visible Chrome window. Drop it to run in the background. A few more options:

```bash
python tracker.py --asins B0F1J12R6N B0CL5KNB9M       # track a few at once
python tracker.py --asins B0F1J12R6N --loop --every 6 # re-check every 6h
```

Readings go to `price_history.json`. Then chart it:

```bash
python plot_prices.py --out price_chart.png
```

### Using a proxy

Amazon shows prices based on where it thinks you are, so without a proxy you can end up tracking the wrong country's price (or none at all). Point it at a proxy for your target country:

```bash
python tracker.py --asins B0F1J12R6N --proxy "http://user:pass@host:port" --headed
```

`proxy_helper.py` handles the auth side so Chrome doesn't pop a login box. No selenium-wire, no extensions.

### The test scripts

These just measure behaviour, they don't try to get around anything:

```bash
python block_test.py --asin B0F1J12R6N --mode bare
python search_browser_test.py --term "ps5" --headed
python price_compare.py --asin B0F1J12R6N --proxy "http://user:pass@host:port"
```

## What I found

Short version, from running the scripts above against Amazon:

| Setup | Result |
| --- | --- |
| Product page, plain requests | 150 requests, no blocks |
| Search page, plain requests | blocked on the first request (503) |
| Search page, better headers | still blocked |
| Search page, requests + proxy | still blocked |
| Search page, real browser | works (16 results) |
| Search page, browser + proxy | works (22 results) |

![search works in a browser](assets/search-success.png)

So product pages barely care, search pages block straight away, and the block has more to do with not being a real browser than with your IP. Longer explanation is in the blog post.

## A note on usage

This is for learning and small-scale price monitoring of public data. Stick to sites you're allowed to scrape, respect robots.txt and the site's terms, and keep the request rate low. The scripts default to polite settings. Nothing here tries to break CAPTCHAs or other protections.

## License

[MIT](LICENSE). Do what you want with it.

<sub>Proxy testing done with [FlashProxy](https://www.flashproxy.com).</sub>
