"""Static figures for the report (matplotlib, PNG for the README)."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# Validated categorical order (fixed, never cycled) + recessive ink.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
NEUTRAL = "#8a8985"
CRITICAL = "#c4271a"

plt.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID,
        "axes.labelcolor": INK2,
        "xtick.color": INK2,
        "ytick.color": INK2,
        "text.color": INK,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.titleweight": "bold",
        "legend.frameon": False,
        "lines.linewidth": 1.6,
        "figure.dpi": 150,
        "axes.axisbelow": True,
    }
)


def _save(fig, path):
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def overview(acc, bt, ew_vol, path):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.1))
    for i, (name, g) in enumerate(acc.groupby("problem", sort=False)):
        a1.loglog(g["assets"], g["milliseconds"], "o-", color=SERIES[i], label=name)
    ref = acc.dropna(subset=["SLSQP milliseconds"]).groupby("assets")["SLSQP milliseconds"].mean()
    a1.loglog(ref.index, ref.to_numpy(), "s--", color=NEUTRAL, label="SciPy SLSQP (no trading cost)")
    a1.set_xlabel("number of assets")
    a1.set_ylabel("milliseconds per solve")
    a1.set_title("Solve time", loc="left")
    a1.legend(fontsize=7)
    a2.plot(bt["turnover per rebalance %"], bt["realised volatility %"], "o-", color=SERIES[0])
    for k, row in bt.iterrows():
        xy = (row["turnover per rebalance %"], row["realised volatility %"])
        a2.annotate(f"{k:g}", xy, textcoords="offset points", xytext=(5, 5), fontsize=7, color=INK2)
    a2.set_xlabel("turnover per rebalance, % (labels: trading-cost coefficient)")
    a2.set_ylabel("realised volatility, % per year")
    a2.set_title(f"Risk against trading (equal weights: {ew_vol:.1f}%)", loc="left")
    _save(fig, path)
