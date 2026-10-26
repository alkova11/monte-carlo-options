# Model, estimators and experimental design

## Question and units
How do variance-reduction estimators change option-pricing error, uncertainty and
cost at a fixed payoff-evaluation budget? All experiments use synthetic inputs.
Currency is unspecified: spot, strike, payoffs and prices use the same currency unit.
T and observation dates are year fractions supplied directly; no calendar/day-count
conversion is implied. r and q are continuously compounded annual rates, and sigma
is annualised volatility (return standard deviation per square-root year).

These are risk-neutral model prices, not forecasts of future returns. Assumptions:
constant parameters, lognormal underlying, continuous dividends, frictionless trading,
no jumps, no volatility smile, no counterparty/default costs and European exercise.

## Risk-neutral dynamics and reference
Under the pricing measure, dS=(r-q)S dt + sigma S dW. Applying Ito's lemma to log S
gives drift r-q-sigma²/2, hence

    S_T = S0 exp((r-q-sigma²/2)T + sigma sqrt(T) Z), Z ~ N(0,1).
    Y_call = exp(-rT) max(S_T-K,0)
    Y_put  = exp(-rT) max(K-S_T,0)

The drift is r-q because discounted gains including dividends are a martingale under
the pricing measure. It is not an assumed expected physical market return.
For T>0 and sigma>0:

    d1 = [log(S0/K)+(r-q+sigma²/2)T]/(sigma sqrt(T))
    d2 = d1-sigma sqrt(T)
    C = S0 exp(-qT) Phi(d1)-K exp(-rT) Phi(d2)
    P = K exp(-rT) Phi(-d2)-S0 exp(-qT) Phi(-d1)

The code evaluates each tail directly with scipy.special.ndtr, avoiding 1-Phi(x)
cancellation. At expiry it returns intrinsic value; with zero volatility it discounts
the deterministic forward payoff. Analytical parity is
C-P=S0 exp(-qT)-K exp(-rT). Numerical reference fixtures use S0=K=100,r=.05,q=0,
sigma=.2,T=1: call 10.450583572185565, put 5.573526022256971.

## Independent sampling units and fair budgets
The input N is a *maximum payoff-evaluation budget*, not necessarily a count of
independent observations. Three methods run separately; choosing the displayed method
does not alter the comparison. The pricing engine directly samples terminal prices.
A separate stream generates just 30 paths with 100 exact-increment steps for display.

| Method | Independent unit U | Independent units | Cost charged |
|---|---|---:|---:|
| Ordinary | discounted payoff Y(Z) | N | N payoffs |
| Antithetic | [Y(Z)+Y(-Z)]/2 | floor(N/2) | 2 floor(N/2) payoffs |
| Stock control | Y-beta(X-E[X]) | N-m | N payoffs including m pilot |

Odd antithetic budgets leave one evaluation unused. For controls m=max(32,floor(N/10));
X=exp(-rT)S_T, E[X]=S0 exp(-qT). Fit beta=sum((X-Xbar)(Y-Ybar))/sum((X-Xbar)²)
with an intercept on an independent pilot. A degenerate pilot sets beta=0.
Conditional on any fitted beta, the production mean is unbiased because the control
expectation is known and the pilot is independent. Consequently production residual
variance supplies the conditional SE; pilot cost affects how many production draws
remain, not an extra fitted-coefficient term in the mean SE. This independence would
not hold if the same draws were used to fit and estimate without further analysis.

For independent units U_1,...,U_n, price=mean(U), SE=sd(U,ddof=1)/sqrt(n),
CI=mean(U) +/- 1.95996398454 SE. For antithetics sd is across pair averages,
never across the correlated individual legs. Deterministic cases bypass sampling,
report zero draws used, one exact value and SE=0. No interval is clipped to price bounds.
Runtime uses perf_counter and includes sampling, pilot fitting, payoff evaluation,
benchmark calculation and summary statistics, excluding charting, disk IO and imports.
Fixed payoff budgets do not imply equal runtime or equal numbers of normal draws.

## Confidence limitations
The normal CLT interval is asymptotic, not exact for skewed payoffs. Early running
means and rare-event payoffs can have severe undercoverage; zero observed variance is
not proof of zero option value. The UI warns for fewer than 30 nonzero payoffs or
zero sample SE. For controls it also warns when fewer than 30 zero payoffs were
observed, because an apparently linear deep-in-the-money payoff may conceal a rare
kink. These are diagnostics, not certified coverage thresholds. Negative controlled
estimates/interval endpoints can occur and are not silently clipped.

During development, K=80,sigma=.1,T=.25 produced a tiny positive put value but no
observed positive payoffs. The stock-controlled call also looked virtually constant.
An initial generic five-SE assertion correctly failed: the observed variance missed
the rare event. We moved the ordinary statistical agreement fixture to a nonrare case,
kept dedicated rare-payoff warning checks, and retained difficult cases in research.
We did not widen all tolerances until the issue disappeared.

The convergence plot reuses nested samples and a fixed pilot. Consecutive points are
dependent, and its pointwise intervals are not a simultaneous band. Chart hover and estimator switching are client-side and never request fresh samples.
Form submission alone triggers simulation. The browser loads an existing saved run on
refresh and restores its inputs. Results and downloads use that saved run; edited
inputs are marked as stale until an explicit new submission.

## Repeated-seed research design
The European grid crosses calls/puts, strikes 80/100/120 at spot 100, volatilities
15%/40%, maturities .25/2 years, with r=5%,q=2%: 24 cases. Budgets 1,000/4,000/16,000
and 100 independent seeds per cell produce 21,600 estimates. No market calibration or
train/test split applies to this synthetic numerical investigation. This grid is not
an exhaustive assessment of tails or a volatility surface.

SeedSequence spawns independent experiment streams, then separate pilot/production
streams. Methods use independent streams in the repeated-run study; the UI uses the
same seed across methods for reproducible comparisons, so its estimates are not
independent cross-method experiments. Method timing order is shuffled reproducibly
within each replicate; one warmup per estimator is excluded. No affinity or hardware
isolation is enforced, so report distributions and avoid universal speed claims.

RMSE=sqrt(mean((estimate-reference)²)); bias and empirical estimate variance are
reported separately. Variance reduction is empirical Var(ordinary)/Var(method) within
the same case/budget, including pilot costs. Ratios below one indicate worse variance.
RMSE SE uses the delta method from the variance of squared errors; it is only an
approximation with 100 repeats and may be poor in rare cases. Coverage is the fraction
of intervals containing Black–Scholes, with a binomial Wilson interval. A successful
95% method should miss about 5% of the time; no test requires every CI to contain truth.

For each case and estimator, fit log(RMSE) against log(N). A slope near -.5 supports
inverse-square-root convergence. Bootstrap independent repeats separately at each
budget 500 times (seed 917) to form percentile intervals for that slope. Only three
budgets are used, so the bootstrap assesses repeat variation within this design,
not proof of an asymptotic convergence rate. Very rare payoffs can defeat this summary.

## Arithmetic Asian extension
Observation dates t_1<...<t_m in [0,T] are explicit, equal-weight dates. Include S0
only if date zero is explicitly provided; include maturity only if explicitly listed.
Payment occurs at T even if the last observation is earlier. Arithmetic A=mean(S_ti),
geometric G=exp(mean(log S_ti)). Draw exact independent GBM increments over date gaps,
streaming dates to use O(N) memory. There is no Euler time-stepping bias at these dates;
changing observation dates changes the contract, rather than refining an approximation
to an automatically assumed continuous average.

The logarithm of G is normal with

    mu = log S0 + (r-q-sigma²/2) mean(t_i)
    v  = sigma²/m² sum_i sum_j min(t_i,t_j).
    d2 = (mu-log K)/sqrt(v), d1=d2+sqrt(v).
    geometric call = exp(-rT)[exp(mu+v/2)Phi(d1)-K Phi(d2)].

The put uses the corresponding negative-tail formula. The discounted geometric payoff
is a highly correlated control with this analytic expectation; beta uses a separate
pilot under the same budget rule. At v=0 evaluate the deterministic payoff directly.
The one-observation-at-T case reduces to European Black–Scholes and the control removes
all simulation error, an especially strong implementation check.

The arithmetic price has no analytical formula implemented here. Its saved reference
is an independent 500,000-path geometric-control Monte Carlo estimate, including its
own standard error and seed. Fifty independent 20,000-budget replications per method
compare empirical spread and RMSE against that noisy reference. Differences use
sqrt(SE_estimate²+SE_reference²). Reference noise contributes to RMSE and is shared
across comparisons; these are not exact absolute errors or analytical coverage results.
The reference uses the same implementation, so agreement alone cannot rule out shared
bugs. One-date limits, deterministic cases, geometric moment checks and AM>=GM for
calls provide additional validation. No Asian antithetic estimator or Greeks are claimed.

## Limits and reproducibility
Budget: 100–2,000,000 per run; up to 200 visual paths/1,000 steps; dates 1–365;
Asian 50 million observation evaluations per simulation; benchmark aggregate caps
prevent accidental excessive workloads. Finite positive spot/strike, nonnegative
volatility/T, bounded rates and combined second-moment limits are validated. These
bounds prevent overflow and runaway memory but do not guarantee useful tail sampling.

Each run saves UTC timestamps, UUID, canonical configuration hash, seed, dependency
lock hash, source-tree hash, Git commit/dirty state when available, environment,
checksummed artifacts and status. Synthetic runs have empty dataset lists. Price runs
save raw independent units/payoffs and visual paths as NPZ; tables use Parquet and CSV;
interactive HTML embeds Plotly for offline viewing. Research tables retain every seed.
Bitwise output reproduction targets the locked software/platform; runtime and file UUIDs
naturally change. Cross-platform numerical differences may exist.

## Sources and implementation attribution
Implementation is original project code using standard formulas; no third-party source
code was copied. API signatures were checked against primary documentation:

- [NumPy Generator.standard_normal](https://numpy.org/doc/stable/reference/random/generated/numpy.random.Generator.standard_normal.html)
- [SciPy ndtr](https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.ndtr.html)
- [Plotly.js react and rendering API](https://plotly.com/javascript/plotlyjs-function-reference/)
- [uv lock and sync](https://docs.astral.sh/uv/concepts/projects/sync/)
- [QuantLib Asian example](https://github.com/lballabio/QuantLib/blob/master/Examples/AsianOption/AsianOption.cpp)
  distinguishes discrete geometric analytic engines from arithmetic Monte Carlo controls.
- [QuantLib workshop presentation](https://www.quantlib.org/slides/qlws14/lewerenz.pdf)
  provides context on analytical geometric and numerical arithmetic-average engines.

Docs were consulted 25 October 2026. Dependencies retain their upstream licences; choose
a repository licence before publication. No market dataset redistribution is involved.
