# Changelog

## 0.2.0 — initial public release candidate

- European calls and puts under risk-neutral GBM, with dividends and analytical limits.
- Ordinary Monte Carlo, antithetic pair averages and an independent-pilot stock control.
- Discrete arithmetic Asian options with an analytical geometric-payoff control.
- Custom local web app, explicit runs, three interactive charts and downloadable artifacts.
- Saved study: 24 cases, three budgets, 100 seeds and three estimators (21,600 estimates).
- Empirical RMSE, interval coverage, variance reduction, runtime and convergence analysis.
- Locked Python/TypeScript dependencies, 54 Python checks and browser workflow validation.

The former Streamlit prototype was replaced by a custom interface. The earlier
narrative's 48-case/43,200-estimate count was corrected to match the actual 24-case,
21,600-estimate data; the underlying measurements were unchanged.
