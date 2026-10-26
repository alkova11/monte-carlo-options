# Measured results

All numbers below come from the saved completed runs. No single-run timing is used to
claim a universal estimator ranking. Reproduce with the commands in README.md.

## European example
S0=K=100,r=.05,q=.02,sigma=.2,T=1,call,N=100000,seed=42.
Analytical Black–Scholes price: 9.227005508.

| method | price | standard_error | absolute_error | effective_samples | pilot_samples |
|---|---|---|---|---|---|
| ordinary | 9.28704 | 0.0437591 | 0.060033 | 100000 | 0 |
| antithetic | 9.21958 | 0.0324691 | 0.00742079 | 50000 | 0 |
| control | 9.23146 | 0.0188927 | 0.00445041 | 90000 | 10000 |

The budget includes the pilot. This single seed illustrates the interface, not a
statistical verdict. Independent replications provide the main evidence below.

## Repeated-seed study
24 cases × 3 budgets × 100 independent seeds × 3 estimators
= 21,600 estimates.
The 24 cases cross calls/puts, strikes 80/100/120, sigma .15/.4, T .25/2, with
S0=100,r=.05,q=.02. Each cell has 100 independent observations. The overview below
weights all case/budget cells equally; it is not an average over market frequencies.

| method | median_variance_reduction | mean_coverage | worst_coverage |
|---|---|---|---|
| antithetic | 1.75358 | 0.943056 | 0.6 |
| control | 3.21689 | 0.935833 | 0.56 |
| ordinary | 1 | 0.939028 | 0.55 |

Variance reduction compares empirical estimate variances at the same payoff budget.
Medians summarise heterogeneous cases: gains are not universal. Extremely large
ratios in nearly linear cases are unstable and should not be generalised. Rare-payoff
coverage materially below .95 demonstrates the limitations of a normal CI.
The mean coverage is also below nominal, especially for controls in this grid.

For the preselected ATM call with sigma=.15,T=2,N=16000:

| method | rmse | rmse_se | coverage | coverage_low | coverage_high | mean_runtime_seconds | runtime_sd_seconds | variance_reduction |
|---|---|---|---|---|---|---|---|---|
| antithetic | 0.0819216 | 0.00486602 | 0.98 | 0.929988 | 0.994498 | 0.000341448 | 4.83947e-06 | 2.61668 |
| control | 0.0418296 | 0.00250531 | 0.99 | 0.945514 | 0.998233 | 0.000438815 | 5.9866e-06 | 10.0382 |
| ordinary | 0.132698 | 0.00949786 | 0.91 | 0.837738 | 0.951927 | 0.000390037 | 5.46426e-06 | 1 |

RMSE uncertainties use a delta-method approximation. Coverage uncertainties use Wilson
intervals. At 100 repeats, an observed coverage such as .91 or .99 does not establish
a permanently miscalibrated method; consult the interval and repeated studies.
Timings include pilots and summaries. Randomised method order reduces order effects,
but CPU load, allocation and platform variation remain. This experiment demonstrates
accuracy/cost tradeoffs, not that one method is always faster.

## Convergence
Log-log RMSE slopes use three budgets (1000,4000,16000); -.5 is the usual CLT rate.

| method | median_slope |
|---|---|
| antithetic | -0.5105 |
| control | -0.511041 |
| ordinary | -0.508472 |

Per-case bootstrap percentile intervals (500 within-budget resamples, seed 917) are
saved in convergence_rates.parquet. These estimates support approximate inverse-root
scaling in this design; they do not prove a universal asymptotic rate. One running
convergence trace cannot supply independent repeated-run evidence.

## Asian extension
Monthly observations i/12, i=1..12; equal weights, no observation at zero. Same model
parameters as the European example. 50 independent seeds per method at budget 20000.
Independent numerical reference (500000 total budget, geometric control):
5.519788167, SE 0.000327406, approximate 95% CI
[5.519146464, 5.520429870]. This is NOT an analytical
arithmetic-average price. Analytical geometric control price:
5.327705787.

| method | replicates | mean_price | empirical_sd | rmse_to_noisy_reference | reference_se | mean_runtime_seconds |
|---|---|---|---|---|---|---|
| control | 50 | 5.52009 | 0.0017891 | 0.00179602 | 0.000327406 | 0.00317982 |
| ordinary | 50 | 5.52736 | 0.0606949 | 0.0605606 | 0.000327406 | 0.00305709 |

The geometric control substantially reduces empirical spread in this example.
RMSE against the shared numerical reference includes reference noise and can inherit
shared implementation error. We therefore also validate analytical geometric moments,
AM>=GM for call payoffs, deterministic averages, puts and the single-date European limit.

## Environment and provenance
Python 3.12.15; macOS-26.6.2-arm64-arm-64bit; 10 logical CPUs;
processor arm. Dependencies: {"numpy": "2.5.4", "pandas": "3.1.0", "plotly": "7.1.0", "pyarrow": "26.0.0", "scipy": "1.18.1", "streamlit": "1.66.1"}.
Wall-clock timing, warmups excluded, no CPU affinity. Runs executed locally; hardware
load was uncontrolled. Git was unavailable due to the host Xcode licence prompt:
commit and dirty state are null, not invented. Each original manifest stores its source
hash and lock hash, seed/configuration and artifact checksums. Source snapshots identify
the code at each run; later documentation/UI adjustments may change the current hash.

Portable evidence: [publication index](../reports/published/publication_index.json).
Original run IDs: b68726db-6b93-484f-a6b5-f7ffce9ff9ca, cdb03fd4-5c50-4cb2-a9e0-2a6168b2204d, 158e2dff-6404-46bb-b98a-f90a16440d0e.
Complete generated HTML/NPZ/CSV files remain in the ignored original run folders.
The focused [RMSE chart](../reports/figures/rmse.html) and
[error/time chart](../reports/figures/error_time.html) embed Plotly for offline inspection.

## Limits and next research
Constant-volatility GBM is a teaching/research model. No prices are calibrated to a
live market, and no conclusion predicts realised returns. The finite synthetic grid,
100 repeats, single host, normal intervals, fixed pilot fraction and shared Asian
implementation limit generality. Rare-event/importance sampling, alternative pilot
allocations, independent Asian implementations and Greeks are sensible future work.
See METHODOLOGY.md for derivations, assumptions and the development failure that
exposed rare-event undercoverage.
