# Methodology

## 1. Problem

    minimise    1/2 w' C w - gamma mu' w + kappa |w - w0|_1
    subject to  sum(w) = 1,   0 <= w_i <= cap

Risk, expected return, a proportional trading cost against the current holdings w0, full investment, no short
positions and a cap per name. The quadratic part is smooth; the cost and the bounds are not. Generic solvers
handle the kinks through extra variables and constraints.

## 2. Splitting

Write the weights twice, x and z, and require x = z. Give the smooth part to x and the non-smooth part to z. The
alternating direction method of multipliers then repeats three steps:

1. x-step. Minimise the quadratic plus a penalty rho/2 |x - z + u|^2 under the budget constraint. This is a linear
   system with the matrix C + rho I, which never changes: it is factorised once (Cholesky) and each iteration costs
   two triangular solves. The budget is imposed exactly by a rank-one correction.
2. z-step. Minimise the trading cost and the box constraints plus the same penalty. The problem separates into one
   scalar problem per asset with a closed form: shrink x + u towards the current holding by kappa / rho (soft
   threshold), then clip to [0, cap].
3. Dual step. u accumulates the disagreement x - z.

The soft threshold is what produces exact zeros in the trade list: a position whose marginal benefit of trading is
below the cost is left exactly where it is, not approximately.

Stop when the primal residual max|x - z| and the dual residual rho max|z - z_previous| are both below 1e-9. The
step parameter rho is set to the average variance, the natural scale of the quadratic term. The solver returns z,
which satisfies the bounds exactly.

## 3. Verification

- Optimality conditions. A point is optimal when one multiplier nu makes C w - gamma mu - nu lie in the
  subdifferential of the cost and the box at every asset. The largest violation over 15 problems is 1.2e-7 of the
  gradient size. This check uses no other solver.
- SciPy SLSQP on the smooth problems up to 100 assets: weights within 1.7e-7, objective never worse by more than
  1.5e-11.
- Closed form for two assets; a prohibitive trading cost returns the starting portfolio.

## 4. Findings

- 300 assets, long-only, capped: about 18 ms (minimum variance, 246 iterations), 15 to 25 ms with trading costs, 90 ms for
  the mean-variance problem, which needs more iterations (1,492). At 100 assets it is 10 to 100 times faster than
  SLSQP, depending on the problem; timings vary from run to run.
- With the trading cost, 115 of 300 positions are left exactly untouched in a single solve.
- Rolling minimum-variance portfolio, 300 stocks, 41 monthly rebalances: realised volatility 21.1% against 28.2%
  for equal weights. Raising the trading-cost coefficient to 0.002 cuts turnover from 10.5% to 4.7% per rebalance
  and the number of names traded from 43 to 19, for 0.4 points of volatility. At 0.02 the portfolio barely trades
  and stays close to where it started (volatility 25.0%).

## 5. Limits

- First-order method: iteration counts grow with the conditioning of the problem (1,492 for the mean-variance case
  against 246 for minimum variance), and accuracy beyond 1e-9 is slow. Interior-point or active-set solvers reach
  machine precision in fewer, costlier steps.
- rho is fixed. Adaptive rho and over-relaxation, as in production splitting solvers, would cut the iterations.
- Dense Cholesky: fine for hundreds of assets, cubic beyond. A factor-model covariance would make the x-step linear
  in the number of assets.
- The backtest has no return forecast, no transaction-cost accounting in the returns, and uses surviving stocks. It
  shows the turnover and risk trade-off of the optimiser, not an investable performance.
- Only the constraints listed above. Sector or factor exposure limits need a further splitting block.

## References

- Boyd, Parikh, Chu, Peleato, Eckstein, Distributed optimization and statistical learning via the alternating
  direction method of multipliers, Foundations and Trends in Machine Learning.
- Stellato, Banjac, Goulart, Bemporad, Boyd, OSQP: an operator splitting solver for quadratic programs,
  Mathematical Programming Computation.
- Parikh, Boyd, Proximal algorithms, Foundations and Trends in Optimization.
- Markowitz, Portfolio selection, Journal of Finance.
