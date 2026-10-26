# v0.2.0 — Monte Carlo Options Lab

An initial public release candidate for studying how accurately and efficiently
Monte Carlo estimators price options under a stated model.

## Included

- European calls/puts with exact risk-neutral terminal GBM sampling and a
dividend-adjusted Black–Scholes reference.
- Ordinary Monte Carlo, antithetic pair averages and an independent-pilot stock control.
- Arithmetic Asian extension with explicit dates and an analytical geometric control.
- Original local web interface with three interactive charts, comparisons, saved runs
and CSV/configuration/complete-run downloads.
- CLI workflows, locked dependencies, CI configuration, methodology and real saved evidence.

## Measured findings

The European study contains 24 cases × 3 budgets × 100 independent seeds × 3 methods:
21,600 estimates. Median empirical variance reduction at matched payoff budgets was
1.75× for antithetics and 3.22× for the stock control. The control pilot is included.
Some cases worsen; rare-payoff normal intervals can materially undercover.

See `docs/RESULTS.md` for coverage, uncertainty, timing and the numerical Asian reference.
These are model-conditional research findings, not return predictions.

## Local validation

54 Python tests passed, including numerical and HTTP integration checks. Ruff,
TypeScript checking/build and the browser workflow were checked locally. Remote GitHub
Actions status must be confirmed after the repository is published.

## Run

```bash
uv sync --locked --python 3.12
uv run --locked quant-options-app
```

The app runs at `http://127.0.0.1:8501`. No credentials or hosted services are required.
This source release does not host a public web app.
