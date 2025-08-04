"""All experiments, checks and the report."""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from . import engine, plotting
from .engine import ROOT
from .report import md_table


def _check(checks, area, name, ok, detail, warn=False):
    checks.append(
        {"area": area, "check": name, "status": "PASS" if ok else ("WARN" if warn else "FAIL"), "detail": detail}
    )


def run(cfg_path=None, out=None, fast: bool = False) -> dict:
    cfg = yaml.safe_load(open(cfg_path or ROOT / "configs" / "default.yaml"))
    out = Path(out) if out else ROOT / "reports"
    (out / "figures").mkdir(parents=True, exist_ok=True)
    if not engine.available():
        raise SystemExit("Rust solver not built: run `make build` first")
    r = engine.load_returns()
    sizes = [20, 40, 60] if fast else cfg["sizes"]
    ref_max = 40 if fast else cfg["reference_max"]
    penalties = cfg["penalties"][:3] if fast else cfg["penalties"]
    n_bt = 60 if fast else r.shape[1]
    train, step, cap = cfg["train_days"], cfg["rebalance_days"], cfg["cap"]
    checks: list[dict] = []

    # 1. accuracy and speed on three problem types
    rows = []
    for n in sizes:
        cov = 252 * engine.covariance(r[:train, :n], cfg["shrinkage"])
        mu = 252 * r[:train, :n].mean(0)
        w0 = np.full(n, 1 / n)
        capn = max(cap, 2.0 / n)
        for label, gamma, kappa in [
            ("minimum variance", 0.0, 0.0),
            ("mean-variance", 0.3, 0.0),
            ("minimum variance with trading cost", 0.0, 0.002),
        ]:
            s = engine.solve(cov, mu, gamma, kappa, w0, capn)
            w = s["weights"]
            row = {
                "assets": n,
                "problem": label,
                "iterations": s["iterations"],
                "milliseconds": 1e3 * s["seconds"],
                "optimality violation": engine.kkt_violation(w, cov, mu, gamma, kappa, w0, capn),
                "budget error": s["budget_error"],
                "weights at a bound": int(((w < 1e-9) | (w > capn - 1e-9)).sum()),
                "weights left untouched": int((np.abs(w - w0) < 1e-12).sum()),
            }
            if n <= ref_max and kappa == 0.0:
                t0 = time.perf_counter()
                ref = engine.reference(cov, mu, gamma, capn)
                row["SLSQP milliseconds"] = 1e3 * (time.perf_counter() - t0)
                row["largest weight difference to SLSQP"] = float(np.abs(ref - w).max())
                row["objective minus SLSQP objective"] = engine.objective(w, cov, mu, gamma, 0, w0) - engine.objective(
                    ref, cov, mu, gamma, 0, w0
                )
            rows.append(row)
    acc = pd.DataFrame(rows)
    has_ref = acc["SLSQP milliseconds"].notna()
    _check(
        checks,
        "Accuracy",
        "optimality conditions satisfied on every problem",
        float(acc["optimality violation"].max()) < 1e-5,
        f"largest violation {acc['optimality violation'].max():.1e} of the gradient size, {len(acc)} problems",
    )
    _check(
        checks,
        "Accuracy",
        "weights agree with SciPy SLSQP",
        float(acc.loc[has_ref, "largest weight difference to SLSQP"].max()) < 1e-5,
        f"largest difference {acc.loc[has_ref, 'largest weight difference to SLSQP'].max():.1e}",
    )
    _check(
        checks,
        "Accuracy",
        "objective never worse than SLSQP by more than 1e-9",
        float(acc.loc[has_ref, "objective minus SLSQP objective"].max()) < 1e-9,
        f"worst case {acc.loc[has_ref, 'objective minus SLSQP objective'].max():+.1e}",
    )
    _check(
        checks,
        "Accuracy",
        "budget constraint met",
        float(acc["budget error"].max()) < 1e-6,
        f"largest error {acc['budget error'].max():.1e}",
    )
    big = acc[has_ref & (acc["assets"] == acc.loc[has_ref, "assets"].max())]
    ratio = float((big["SLSQP milliseconds"] / big["milliseconds"]).min())
    _check(
        checks,
        "Speed",
        "faster than SLSQP at the largest common size",
        ratio > 1,
        f"at least {ratio:.0f}x at {int(big['assets'].iloc[0])} assets",
        warn=True,
    )
    cost_rows = acc[acc["problem"].str.contains("trading cost")]
    _check(
        checks,
        "Sparsity",
        "the trading cost leaves positions exactly untouched",
        bool((cost_rows["weights left untouched"] > 0).all()),
        ", ".join(
            f"{int(a)} of {int(b)}"
            for a, b in zip(cost_rows["weights left untouched"], cost_rows["assets"], strict=True)
        ),
    )

    # 2. rolling minimum-variance portfolio: what the trading cost buys
    rr = r[:, :n_bt]
    starts = list(range(train, len(rr) - step + 1, step))
    bt = {}
    for kappa in penalties:
        w = np.full(n_bt, 1 / n_bt)
        rets, turn, traded, secs, its = [], [], [], 0.0, 0
        for t in starts:
            cov = 252 * engine.covariance(rr[t - train : t], cfg["shrinkage"])
            s = engine.solve(cov, kappa=kappa, w0=w, cap=cap)
            new = s["weights"] / s["weights"].sum()
            turn.append(np.abs(new - w).sum() / 2)
            traded.append(int((np.abs(new - w) > 1e-6).sum()))
            secs += s["seconds"]
            its += s["iterations"]
            block = rr[t : t + step]
            growth = np.cumprod(1 + block, axis=0)
            rets.extend(np.diff(np.concatenate([[1.0], growth @ new])) / np.concatenate([[1.0], growth @ new])[:-1])
            w = new * growth[-1] / (new @ growth[-1])  # weights drift with prices until the next rebalance
        rets = np.array(rets)
        bt[kappa] = {
            "realised volatility %": 100 * rets.std() * np.sqrt(252),
            "turnover per rebalance %": 100 * float(np.mean(turn[1:])),
            "first rebalance turnover %": 100 * turn[0],
            "stocks traded per rebalance": float(np.mean(traded[1:])),
            "annual turnover %": 100 * float(np.mean(turn[1:])) * 252 / step,
            "mean solver milliseconds": 1e3 * secs / len(starts),
            "mean iterations": its / len(starts),
        }
    bt = pd.DataFrame(bt).T
    bt.index.name = "trading-cost coefficient"
    ew = rr[train : train + step * len(starts)].mean(1)
    ew_vol = 100 * ew.std() * np.sqrt(252)
    base, best = bt.iloc[0], bt.iloc[min(2, len(bt) - 1)]
    _check(
        checks,
        "Backtest",
        "minimum variance has lower realised volatility than equal weights",
        base["realised volatility %"] < ew_vol,
        f"{base['realised volatility %']:.1f}% against {ew_vol:.1f}%",
    )
    _check(
        checks,
        "Backtest",
        "turnover falls monotonically with the trading cost",
        bool(np.all(np.diff(bt["turnover per rebalance %"]) < 0)),
        ", ".join(f"{v:.1f}%" for v in bt["turnover per rebalance %"]),
    )
    _check(
        checks,
        "Backtest",
        "turnover cut by more than half for less than one point of volatility",
        best["turnover per rebalance %"] < 0.5 * base["turnover per rebalance %"]
        and best["realised volatility %"] < base["realised volatility %"] + 1.0,
        f"turnover {base['turnover per rebalance %']:.1f}% to {best['turnover per rebalance %']:.1f}%, volatility {base['realised volatility %']:.2f}% to {best['realised volatility %']:.2f}%",
        warn=True,
    )

    plotting.overview(acc, bt, ew_vol, out / "figures" / "overview.png")

    val = pd.DataFrame(checks)
    counts = val["status"].value_counts().to_dict()
    L = [
        "# SplitFolio report",
        "",
        f"Problem: minimise 1/2 w'Cw - gamma mu'w + kappa |w - w0|_1 with sum(w) = 1 and 0 <= w <= cap. Covariance from {train} days of returns "
        f"(shrunk {100 * cfg['shrinkage']:.0f}% to its diagonal, annualised), cap {100 * cap:g}% (or 2/n when larger). Tolerance 1e-9 on both residuals.",
        "",
        "## 1. Accuracy and speed",
        "",
        md_table(acc, 3, index=False),
        "",
        f"## 2. Rolling minimum-variance portfolio ({n_bt} stocks, {len(starts)} rebalances, every {step} days)",
        "",
        f"Equal-weight portfolio over the same period: realised volatility {ew_vol:.1f}%.",
        "",
        md_table(bt, 2),
        "",
        "## Validation",
        "",
        f"{counts.get('PASS', 0)} PASS, {counts.get('WARN', 0)} WARN, {counts.get('FAIL', 0)} FAIL. See `validation.md`.",
        "",
    ]
    (out / "report.md").write_text("\n".join(L))
    (out / "validation.md").write_text("# Validation checks\n\n" + md_table(val, index=False) + "\n")
    stable = acc.drop(columns=["milliseconds", "SLSQP milliseconds"])
    metrics = {
        "accuracy": json.loads(stable.to_json(orient="records")),
        "backtest": {str(k): v for k, v in bt.drop(columns=["mean solver milliseconds"]).to_dict("index").items()},
        "equal_weight_volatility": ew_vol,
        "checks": [c for c in checks if c["area"] != "Speed"],
    }
    (out / "metrics.json").write_text(json.dumps(metrics, indent=1, default=float))
    return {**metrics, "checks": checks}
