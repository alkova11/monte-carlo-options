# Modelling and implementation decisions

| Decision | Reason |
| --- | --- |
| Exact European terminal sampling | Intermediate time steps are unnecessary for terminal-only payoffs. |
| Total payoff-evaluation budget | Counts both antithetic legs and independent control-pilot draws. |
| Antithetic uncertainty from pair averages | Individual legs are correlated; pairs are the independent units. |
| Separate pilot: max(32, N//10) | Keeps fitted coefficients independent of production observations. |
| Approximate normal intervals | Transparent baseline, with explicit rare-event limits and repeated-run coverage. |
| Explicit Asian observation dates | Defines the discrete contract; date zero is included only when supplied. |
| Geometric Asian payoff control | Has an analytical expectation; arithmetic reference remains numerical. |
| File artifacts, no database | Synthetic research runs need reproducible files rather than a hosted service. |
| Custom local HTML/CSS/TypeScript UI | Owner requested an original interface in place of the Streamlit prototype. |
| Loopback-only Python HTTP API | Keeps the initial application a local research tool. |
| Plotly bundle served locally | Charts work without a CDN after dependencies are installed. |
| Store null unavailable Git metadata | Source/lock hashes provide honest provenance without fabricated commits. |

The saved grid crosses 2 option types × 3 strikes × 2 volatilities × 2 maturities:
24 cases. Three budgets, 100 independent seeds and three methods produce 21,600
estimates. The previous narrative count was corrected; saved measurements were preserved.

No market-return prediction, live-market calibration, brokerage workflow or public
multi-user deployment is part of this release. Licensing and publication are owner decisions.


## Public browser runtime

Use Pyodide in a module worker to reuse existing Python estimators on static hosting. Cap public runs at 200,000 per estimator and store the latest five runs per visitor locally. Native research artifacts remain the source of benchmark claims. Record browser runtime versions and source hashes because they can differ from the native lock. Compare parameter values in a stable key order to avoid false stale-result messages.
