# Monte Carlo Options Lab

Interactive European and Asian option pricing with reproducible Python simulations, variance reduction, confidence intervals and downloadable results.

Built a quantitative research lab comparing ordinary Monte Carlo, antithetic pairs and an independent-pilot control variate against dividend-adjusted Black–Scholes prices. A saved study of 21,600 estimates across 24 synthetic cases found median empirical variance reductions of 1.75× for antithetics and 3.22× for the stock control. The project also examines confidence-interval undercoverage in rare-payoff cases and extends pricing to arithmetic Asian options with a geometric control.

The custom web app lets visitors change assumptions, inspect simulated paths and convergence, compare estimators, and download reproducible run artifacts. Public calculations run in a browser worker using the original Python estimators.

Technology: Python, NumPy, SciPy, pandas, Plotly, TypeScript and Pyodide. License: MIT.

Repository: https://github.com/alkova11/monte-carlo-options

Model prices are conditional on risk-neutral GBM assumptions; they are not forecasts of market returns.

Live app: https://mcopricingsim.adeptrhea24.chatgpt.site
