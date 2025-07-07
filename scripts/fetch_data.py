"""Rebuild data/raw/prices_300_stocks.csv.gz from the Nasdaq price panel of the skfolio datasets repository.

Usage:  python scripts/fetch_data.py [--out data/raw]

Keeps stocks with a complete history, no daily move above 60% and fewer than 5% unchanged closes, then draws 300 of
them with a fixed seed. Calendar dates are replaced by a day counter.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

URL = "https://raw.githubusercontent.com/skfolio/skfolio-datasets/main/datasets/nasdaq_dataset.csv.gz"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "data" / "raw"))
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    px = pd.read_csv(URL, index_col=0).dropna(axis=1)
    r = px.pct_change().iloc[1:]
    px = px.loc[:, (r.abs().max() < 0.6) & ((r == 0).mean() < 0.05)]
    keep = sorted(np.random.default_rng(5).choice(px.columns, 300, replace=False))
    px = px[keep]
    px.index = range(len(px))
    px.index.name = "day"
    px.round(4).to_csv(out / "prices_300_stocks.csv.gz")
    print(f"prices_300_stocks.csv.gz: {px.shape[0]} days, {px.shape[1]} stocks")


if __name__ == "__main__":
    main()
