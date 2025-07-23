"""Python side of the Rust solver, data loading and reference solutions."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[2]
BINARY = ROOT / "engine" / "target" / "release" / "splitfolio-engine"


def available() -> bool:
    return BINARY.exists()


def load_returns(root: Path = ROOT) -> np.ndarray:
    px = pd.read_csv(root / "data" / "raw" / "prices_300_stocks.csv.gz", index_col=0)
    return px.pct_change().iloc[1:].to_numpy()


def covariance(r: np.ndarray, shrinkage: float = 0.2) -> np.ndarray:
    c = np.cov(r.T)
    return (1 - shrinkage) * c + shrinkage * np.diag(np.diag(c))


def objective(w, cov, mu, gamma, kappa, w0) -> float:
    return float(0.5 * w @ cov @ w - gamma * mu @ w + kappa * np.abs(w - w0).sum())


def solve(cov, mu=None, gamma=0.0, kappa=0.0, w0=None, cap=1.0, rho=None, tol=1e-9, max_iter=20000) -> dict:
    """Minimise 1/2 w'Cw - gamma mu'w + kappa |w - w0|_1 with sum(w) = 1 and 0 <= w <= cap."""
    n = len(cov)
    mu = np.zeros(n) if mu is None else np.asarray(mu, float)
    w0 = np.full(n, 1 / n) if w0 is None else np.asarray(w0, float)
    rho = float(np.trace(cov) / n) if rho is None else rho  # the scale of the quadratic term
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(f"{n} {gamma:.17g} {kappa:.17g} {cap:.17g} {rho:.17g} {tol:.17g} {max_iter}\n")
        f.write(" ".join(f"{v:.17g}" for v in mu) + "\n" + " ".join(f"{v:.17g}" for v in w0) + "\n")
        np.savetxt(f, cov, fmt="%.17g")
        path = f.name
    try:
        out = subprocess.run([str(BINARY), path], capture_output=True, text=True, check=True).stdout
    finally:
        Path(path).unlink(missing_ok=True)
    res: dict = {}
    for line in out.splitlines():
        key, _, rest = line.partition(" ")
        res[key] = np.array(rest.split(), float) if key == "weights" else float(rest)
    res["iterations"] = int(res["iterations"])
    return res


def kkt_violation(w, cov, mu, gamma, kappa, w0, cap, eps: float = 1e-8) -> float:
    """Largest violation of the optimality conditions, relative to the size of the gradient.

    With g = C w - gamma mu, w is optimal when one number nu satisfies a_i <= nu - g_i <= b_i for every asset,
    where [a_i, b_i] is the subgradient of the trading cost and the box at w_i: {kappa} above the current holding,
    {-kappa} below it, [-kappa, kappa] on it, extended to -infinity at zero and to +infinity at the cap."""
    g = cov @ w - gamma * mu
    a = np.where(w > w0 + eps, kappa, -kappa)
    b = np.where(w < w0 - eps, -kappa, kappa)
    a = np.where(w <= eps, -np.inf, a)
    b = np.where(w >= cap - eps, np.inf, b)
    gap = (g + a).max() - (g + b).min()  # an admissible nu exists when this is not positive
    return float(max(gap, 0.0) / np.abs(g).max())


def reference(cov, mu, gamma, cap) -> np.ndarray:
    """SciPy SLSQP on the smooth problem (no trading cost): the independent check."""
    n = len(cov)
    res = minimize(
        lambda w: 0.5 * w @ cov @ w - gamma * mu @ w,
        np.full(n, 1 / n),
        jac=lambda w: cov @ w - gamma * mu,
        method="SLSQP",
        bounds=[(0.0, cap)] * n,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1, "jac": lambda w: np.ones(n)}],
        options={"ftol": 1e-15, "maxiter": 2000},
    )
    return res.x
