# SplitFolio report

Problem: minimise 1/2 w'Cw - gamma mu'w + kappa |w - w0|_1 with sum(w) = 1 and 0 <= w <= cap. Covariance from 500 days of returns (shrunk 20% to its diagonal, annualised), cap 5% (or 2/n when larger). Tolerance 1e-9 on both residuals.

## 1. Accuracy and speed

| assets | problem | iterations | milliseconds | optimality violation | budget error | weights at a bound | weights left untouched | SLSQP milliseconds | largest weight difference to SLSQP | objective minus SLSQP objective |
|---|---|---|---|---|---|---|---|---|---|---|
| 30 | minimum variance | 69 | 0.067 | 7.97e-08 | 3.94e-10 | 14 | 0 | 5.947 | 3.87e-08 | -8.36e-12 |
| 30 | mean-variance | 121 | 0.095 | 9.45e-10 | 6.41e-10 | 26 | 0 | 4.839 | 3.77e-08 | -2.22e-11 |
| 30 | minimum variance with trading cost | 76 | 0.068 | 7.85e-08 | 2.13e-10 | 12 | 4 | n/a | n/a | n/a |
| 60 | minimum variance | 115 | 0.422 | 2.73e-09 | 9.53e-10 | 41 | 0 | 22.186 | 7.84e-08 | 1.13e-11 |
| 60 | mean-variance | 207 | 0.683 | 8.44e-10 | 1.54e-08 | 57 | 0 | 12.927 | 1.37e-08 | -6.46e-10 |
| 60 | minimum variance with trading cost | 235 | 0.760 | 8.72e-08 | 4.00e-10 | 28 | 15 | n/a | n/a | n/a |
| 100 | minimum variance | 114 | 0.814 | 7.80e-09 | 1.64e-09 | 76 | 0 | 93.093 | 1.74e-07 | 1.49e-11 |
| 100 | mean-variance | 491 | 5.068 | 3.77e-09 | 6.97e-08 | 97 | 0 | 49.934 | 3.93e-08 | -4.06e-09 |
| 100 | minimum variance with trading cost | 245 | 1.662 | 9.52e-08 | 4.07e-10 | 40 | 32 | n/a | n/a | n/a |
| 200 | minimum variance | 231 | 6.839 | 1.10e-07 | 1.10e-09 | 160 | 0 | n/a | n/a | n/a |
| 200 | mean-variance | 1,174 | 32.375 | 0.000 | 1.46e-07 | 199 | 0 | n/a | n/a | n/a |
| 200 | minimum variance with trading cost | 134 | 4.009 | 1.06e-08 | 7.79e-09 | 93 | 79 | n/a | n/a | n/a |
| 300 | minimum variance | 246 | 17.730 | 1.19e-07 | 2.41e-09 | 254 | 0 | n/a | n/a | n/a |
| 300 | mean-variance | 1,492 | 88.436 | 1.28e-08 | 2.50e-07 | 295 | 0 | n/a | n/a | n/a |
| 300 | minimum variance with trading cost | 196 | 14.676 | 7.97e-08 | 5.73e-08 | 159 | 115 | n/a | n/a | n/a |

## 2. Rolling minimum-variance portfolio (300 stocks, 41 rebalances, every 21 days)

Equal-weight portfolio over the same period: realised volatility 28.2%.

| trading-cost coefficient | realised volatility % | turnover per rebalance % | first rebalance turnover % | stocks traded per rebalance | annual turnover % | mean solver milliseconds | mean iterations |
|---|---|---|---|---|---|---|---|
| 0.00 | 21.09 | 10.47 | 84.72 | 43.02 | 125.60 | 19.89 | 281.49 |
| 5.00e-04 | 21.32 | 7.32 | 76.40 | 28.90 | 87.88 | 24.21 | 342.24 |
| 2.00e-03 | 21.49 | 4.73 | 52.84 | 19.30 | 56.81 | 31.62 | 473.10 |
| 5.00e-03 | 21.71 | 3.27 | 26.24 | 15.78 | 39.19 | 36.75 | 556.80 |
| 0.02 | 24.99 | 1.45 | 0.33 | 7.15 | 17.43 | 59.14 | 1,010.68 |

## Validation

9 PASS, 0 WARN, 0 FAIL. See `validation.md`.
