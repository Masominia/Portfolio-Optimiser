import numpy as np
import pytest

from splitfolio import engine

needs_engine = pytest.mark.skipif(not engine.available(), reason="Rust solver not built (make build)")


def _problem(n=25, seed=0):
    rng = np.random.default_rng(seed)
    f = rng.normal(size=(300, 3))
    r = 0.01 * (f @ rng.normal(size=(3, n)) + 1.5 * rng.normal(size=(300, n)))
    return 252 * np.cov(r.T), 252 * r.mean(0)


@needs_engine
def test_two_assets_closed_form():
    cov = np.array([[0.04, 0.01], [0.01, 0.09]])
    w = engine.solve(cov)["weights"]
    exact = (0.09 - 0.01) / (0.04 + 0.09 - 0.02)  # minimum-variance weight of the first asset
    assert w == pytest.approx([exact, 1 - exact], abs=1e-7)


@needs_engine
def test_matches_slsqp_with_binding_constraints():
    cov, mu = _problem()
    for gamma in (0.0, 0.5):
        s = engine.solve(cov, mu, gamma, cap=0.15)
        w, ref = s["weights"], engine.reference(cov, mu, gamma, 0.15)
        assert np.abs(w - ref).max() < 1e-5 and abs(w.sum() - 1) < 1e-7
        assert w.min() >= 0 and w.max() <= 0.15 + 1e-12 and ((w < 1e-9) | (w > 0.15 - 1e-9)).any()
        assert engine.kkt_violation(w, cov, mu, gamma, 0.0, np.full(25, 1 / 25), 0.15) < 1e-5


@needs_engine
def test_trading_cost_keeps_positions():
    cov, mu = _problem(40, 1)
    w0 = np.full(40, 1 / 40)
    free = engine.solve(cov, w0=w0, cap=0.2)["weights"]
    small = engine.solve(cov, kappa=0.002, w0=w0, cap=0.2)["weights"]
    huge = engine.solve(cov, kappa=10.0, w0=w0, cap=0.2)["weights"]
    assert np.abs(small - w0).sum() < np.abs(free - w0).sum() and (np.abs(small - w0) < 1e-12).sum() > 0
    assert np.allclose(huge, w0, atol=1e-9)  # trading is never worth it
    assert engine.kkt_violation(small, cov, mu, 0.0, 0.002, w0, 0.2) < 1e-5
    assert engine.objective(small, cov, mu, 0, 0.002, w0) <= engine.objective(free, cov, mu, 0, 0.002, w0) + 1e-12


def test_optimality_measure_rejects_a_wrong_answer():
    cov, mu = _problem(10, 2)
    w = np.full(10, 0.1)
    assert engine.kkt_violation(w, cov, mu, 0.0, 0.0, w, 1.0) > 1e-2


def test_data():
    r = engine.load_returns()
    assert r.shape == (1361, 300) and np.isfinite(r).all()


@needs_engine
def test_fast_pipeline(tmp_path):
    from splitfolio.pipeline import run

    out = run(out=tmp_path, fast=True)
    assert (tmp_path / "report.md").exists() and (tmp_path / "figures" / "overview.png").exists()
    assert all(c["status"] != "FAIL" for c in out["checks"])
