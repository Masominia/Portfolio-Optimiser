# Validation checks

| area | check | status | detail |
|---|---|---|---|
| Accuracy | optimality conditions satisfied on every problem | PASS | largest violation 1.2e-07 of the gradient size, 15 problems |
| Accuracy | weights agree with SciPy SLSQP | PASS | largest difference 1.7e-07 |
| Accuracy | objective never worse than SLSQP by more than 1e-9 | PASS | worst case +1.5e-11 |
| Accuracy | budget constraint met | PASS | largest error 2.5e-07 |
| Speed | faster than SLSQP at the largest common size | PASS | at least 10x at 100 assets |
| Sparsity | the trading cost leaves positions exactly untouched | PASS | 4 of 30, 15 of 60, 32 of 100, 79 of 200, 115 of 300 |
| Backtest | minimum variance has lower realised volatility than equal weights | PASS | 21.1% against 28.2% |
| Backtest | turnover falls monotonically with the trading cost | PASS | 10.5%, 7.3%, 4.7%, 3.3%, 1.5% |
| Backtest | turnover cut by more than half for less than one point of volatility | PASS | turnover 10.5% to 4.7%, volatility 21.09% to 21.49% |
