//! Constrained mean-variance portfolios by the alternating direction method of multipliers (ADMM).
//!
//!     minimise    1/2 w' C w - gamma mu' w + kappa |w - w0|_1
//!     subject to  sum(w) = 1,   0 <= w_i <= cap
//!
//! The problem is split in two copies of the weights, x and z, forced to agree:
//!   x-step: a smooth quadratic with the budget constraint, one pair of triangular solves with a Cholesky factor
//!           computed once;
//!   z-step: the non-smooth part (trading cost and box), which separates by asset and has a closed form:
//!           shrink towards the current weight, then clip;
//!   dual step: accumulate the disagreement.
//!
//! Usage: splitfolio-engine <problem file>
//! File:  n gamma kappa cap rho tolerance max_iterations, then mu[n], w0[n], C (n x n, row by row)

use std::env;
use std::fs;
use std::process;
use std::time::Instant;

fn fail(msg: &str) -> ! {
    eprintln!("splitfolio-engine: {msg}");
    process::exit(1)
}

/// In-place Cholesky factorisation (lower triangle) of a symmetric positive definite matrix.
fn cholesky(a: &mut [f64], n: usize) {
    for j in 0..n {
        let mut d = a[j * n + j];
        for k in 0..j {
            d -= a[j * n + k] * a[j * n + k];
        }
        if d <= 0.0 {
            fail("matrix is not positive definite");
        }
        let d = d.sqrt();
        a[j * n + j] = d;
        for i in j + 1..n {
            let mut s = a[i * n + j];
            for k in 0..j {
                s -= a[i * n + k] * a[j * n + k];
            }
            a[i * n + j] = s / d;
        }
    }
}

/// Solve L L' x = b in place.
fn solve(l: &[f64], n: usize, b: &mut [f64]) {
    for i in 0..n {
        let mut s = b[i];
        let row = &l[i * n..i * n + i];
        for (k, lv) in row.iter().enumerate() {
            s -= lv * b[k];
        }
        b[i] = s / l[i * n + i];
    }
    for i in (0..n).rev() {
        let mut s = b[i];
        for k in i + 1..n {
            s -= l[k * n + i] * b[k];
        }
        b[i] = s / l[i * n + i];
    }
}

fn main() {
    let path = env::args().nth(1).unwrap_or_else(|| fail("usage: splitfolio-engine <problem file>"));
    let text = fs::read_to_string(&path).unwrap_or_else(|_| fail("cannot read the problem file"));
    let mut tok = text.split_ascii_whitespace();
    let mut num = || -> f64 { tok.next().and_then(|t| t.parse().ok()).unwrap_or_else(|| fail("problem file is truncated or malformed")) };
    let n = num() as usize;
    let (gamma, kappa, cap, rho, tol) = (num(), num(), num(), num(), num());
    let max_iter = num() as usize;
    let mu: Vec<f64> = (0..n).map(|_| num()).collect();
    let w0: Vec<f64> = (0..n).map(|_| num()).collect();
    let cov: Vec<f64> = (0..n * n).map(|_| num()).collect();
    if n == 0 || cap * (n as f64) < 1.0 || rho <= 0.0 {
        fail("need n > 0, cap * n >= 1 and rho > 0");
    }

    let t0 = Instant::now();
    let mut l = cov.clone();
    for i in 0..n {
        l[i * n + i] += rho;
    }
    cholesky(&mut l, n);
    let mut ones = vec![1.0; n];
    solve(&l, n, &mut ones); // (C + rho I)^-1 1
    let ones_sum: f64 = ones.iter().sum();

    let mut x = vec![1.0 / n as f64; n];
    let mut z = x.clone();
    let mut u = vec![0.0; n];
    let mut rhs = vec![0.0; n];
    let (mut iterations, mut primal, mut dual) = (0usize, f64::INFINITY, f64::INFINITY);
    let shrink = kappa / rho;
    while iterations < max_iter {
        iterations += 1;
        // x-step: (C + rho I) x = gamma mu + rho (z - u) + nu 1, with nu fixed by the budget
        for i in 0..n {
            rhs[i] = gamma * mu[i] + rho * (z[i] - u[i]);
        }
        solve(&l, n, &mut rhs);
        let nu = (1.0 - rhs.iter().sum::<f64>()) / ones_sum;
        for i in 0..n {
            x[i] = rhs[i] + nu * ones[i];
        }
        // z-step: soft threshold around the current holdings, then clip to the box
        let mut dz = 0.0f64;
        primal = 0.0;
        for i in 0..n {
            let v = x[i] + u[i] - w0[i];
            let t = if v > shrink { v - shrink } else if v < -shrink { v + shrink } else { 0.0 };
            let znew = (w0[i] + t).clamp(0.0, cap);
            dz = dz.max((znew - z[i]).abs());
            z[i] = znew;
            let r = x[i] - z[i];
            u[i] += r;
            primal = primal.max(r.abs());
        }
        dual = rho * dz;
        if primal < tol && dual < tol {
            break;
        }
    }
    let seconds = t0.elapsed().as_secs_f64();

    // report the feasible copy z, rescaled only by the (tiny) budget residual
    let total: f64 = z.iter().sum();
    let mut objective = 0.0;
    for i in 0..n {
        let mut cw = 0.0;
        for j in 0..n {
            cw += cov[i * n + j] * z[j];
        }
        objective += 0.5 * z[i] * cw - gamma * mu[i] * z[i] + kappa * (z[i] - w0[i]).abs();
    }
    println!("iterations {iterations}\nprimal_residual {primal:.3e}\ndual_residual {dual:.3e}\nbudget_error {:.3e}", (total - 1.0).abs());
    println!("objective {objective:.15e}\nseconds {seconds:.6}");
    println!("weights {}", z.iter().map(|v| format!("{v:.15e}")).collect::<Vec<_>>().join(" "));
}
