import argparse
import json
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def load(db_path):
    with open(db_path) as f:
        return json.load(f)

def plot(data, out_path):
    fig, ax = plt.subplots(figsize=(10, 5))
    plotted = 0

    for asin, points in data.items():
        times, values = [], []
        for pt in points:
            if pt.get("status") == "ok" and pt.get("value") is not None:
                times.append(datetime.fromisoformat(pt["timestamp"]))
                values.append(pt["value"])
        if len(times) >= 1:
            ax.plot(times, values, marker="o", linewidth=2, label=asin)
            plotted += 1

    if plotted == 0:
        raise SystemExit("No usable price points found yet. Let the tracker collect a few first.")

    ax.set_title("Amazon price history")
    ax.set_xlabel("Time")
    ax.set_ylabel("Price")
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d %H:%M"))
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    print(f"Chart saved to {out_path}  ({plotted} product(s) plotted)")

def main():
    p = argparse.ArgumentParser(description="Chart Amazon price history")
    p.add_argument("--db", default="price_history.json")
    p.add_argument("--out", default="price_chart.png")
    args = p.parse_args()
    plot(load(args.db), args.out)

if __name__ == "__main__":
    main()
