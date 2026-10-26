# LinkedIn launch post — draft

I built a Monte Carlo options-pricing lab to answer a practical question:

How much noise can you remove without increasing the sample budget?

The project compares ordinary Monte Carlo, antithetic pairs and a stock control
variate against dividend-adjusted Black–Scholes prices.

Across 24 synthetic pricing cases, three budgets and 100 independent seeds per cell
— 21,600 estimates — the median empirical variance reduction was:

• Antithetic pairs: 1.75×
• Independent-pilot stock control: 3.22×

The important detail: the control's pilot samples are included in the budget, and
antithetic uncertainty is calculated across independent pair averages.

The most useful finding wasn't just a lower standard error. Rare payoffs exposed how
an apparently precise normal confidence interval can miss uncertainty from events
that were never sampled. Benefits varied by case; some variance ratios were below 1.

I also added arithmetic-average Asian options with explicit observation dates and a
geometric payoff control, plus a custom live web interface for exploring paths, payoff
distributions, convergence and saved research comparisons.

The repository includes reproducible experiments, measured results, 57 passing Python
tests, locked dependencies and a methodology report explaining the modelling choices.

Repository: https://github.com/alkova11/monte-carlo-options

Live app: https://monte-carlo-options-lab-alkova11.adeptrhea24.chatgpt.site

These are conditional risk-neutral model prices, not forecasts of market returns.

#QuantitativeFinance #Python #MonteCarlo #OptionsPricing

---

## Attachments and featured-project copy

Recommended launch image: `reports/figures/linkedin-launch.png`.
Optional second image: `reports/figures/github-preview.png` (actual app screenshot).

Alt text: A Monte Carlo options-pricing research project comparing three estimators
across 24 synthetic cases and 21,600 estimates. Median empirical variance reductions
are 1.75× for antithetics and 3.22× for an independent-pilot stock control. A dark custom
interface shows simulated price paths, payoff distributions and price convergence.

Suggested Featured title: Monte Carlo Options Lab — Pricing & Variance Reduction

Suggested Featured description: Reproducible Python study of option-pricing error,
uncertainty and cost. Ordinary, antithetic and control-variate estimators; European
Black–Scholes benchmarks; arithmetic Asian extension; live browser-based web interface.

Publication status: draft only. Links are included; review the draft before posting. No LinkedIn post or account change has been made.
