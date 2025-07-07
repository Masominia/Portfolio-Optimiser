# Data

`raw/prices_300_stocks.csv.gz`: adjusted daily closing prices of 300 Nasdaq-listed stocks over 1,362 consecutive
trading days (about five and a half years), one row per day, one column per ticker. Calendar dates are replaced by
a day counter. Source: the Nasdaq panel of the `skfolio/skfolio-datasets` repository on GitHub, originally from
Yahoo Finance.

Selection (see `scripts/fetch_data.py`): complete history, no daily move above 60%, fewer than 5% unchanged closes,
then 300 tickers drawn at random with a fixed seed.

Returns are simple daily returns; covariances are annualised with 252 days.

Limits: stocks that were listed for the whole period only (survivorship bias); no transaction costs; the period
contains one market crash, which dominates the first evaluation window.
