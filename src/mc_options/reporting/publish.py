"""Create portable research evidence and a report from completed, hashed run folders."""

import argparse
import json
import shutil
from pathlib import Path

import pandas as pd

from mc_options.reporting.artifacts import ROOT, sha
from mc_options.reporting.charts import research_charts


def table(frame, columns):
    rows = ["| " + " | ".join(columns) + " |", "|" + "|".join(["---"] * len(columns)) + "|"]
    for _, row in frame.iterrows():
        rows.append(
            "| "
            + " | ".join(
                f"{row[c]:.6g}" if isinstance(row[c], float) else str(row[c]) for c in columns
            )
            + " |"
        )
    return "\n".join(rows)


def publish(pricing, benchmark, asian):
    destination = ROOT / "reports/published"
    destination.mkdir(exist_ok=True)
    index = {}
    inputs = {"european": pricing, "benchmark": benchmark, "asian": asian}
    for label, folder in inputs.items():
        folder = Path(folder).resolve()
        if not folder.is_relative_to(ROOT):
            raise ValueError("run folders must be inside this project")
        manifest = json.loads((folder / "manifest.json").read_text())
        if manifest["status"] != "succeeded":
            raise ValueError("cannot publish a failed/incomplete run")
        for a in manifest["artifacts"]:
            original = ROOT / a["file_uri"]
            if not original.is_relative_to(ROOT) or sha(original.read_bytes()) != a["sha256"]:
                raise ValueError("artifact checksum mismatch")
        selected = [p for p in folder.iterdir() if p.suffix in {".json", ".parquet"}]
        target = destination / label
        target.mkdir(exist_ok=True)
        for p in selected:
            shutil.copy2(p, target / p.name)
        index[label] = {
            "run_id": manifest["run_id"],
            "original_folder": str(folder.relative_to(ROOT)),
            "copies": [
                {"path": str((target / p.name).relative_to(ROOT)), "sha256": sha(p.read_bytes())}
                for p in selected
            ],
        }
    (destination / "publication_index.json").write_text(json.dumps(index, indent=2))
    summary = pd.read_parquet(Path(benchmark) / "summary.parquet")
    rates = pd.read_parquet(Path(benchmark) / "convergence_rates.parquet")
    estimates = pd.read_parquet(Path(pricing) / "estimates.parquet")
    asian_summary = pd.read_parquet(Path(asian) / "summary.parquet")
    reference = json.loads((Path(asian) / "reference.json").read_text())
    overview = summary.groupby("method", as_index=False).agg(
        median_variance_reduction=("variance_reduction", "median"),
        mean_coverage=("coverage", "mean"),
        worst_coverage=("coverage", "min"),
    )
    rate_summary = rates.groupby("method", as_index=False).agg(median_slope=("slope", "median"))
    example = summary[(summary.case_id == "call_K100_v0.15_T2.0") & (summary.sample_count == 16000)]
    focused = summary[summary.case_id == "call_K100_v0.15_T2.0"]
    for name, fig in research_charts(focused).items():
        fig.update_layout(showlegend=True)
        fig.write_html(ROOT / f"reports/figures/{name}.html", include_plotlyjs=True)
    env = json.loads((Path(benchmark) / "manifest.json").read_text())["environment"]
    european_table = table(
        estimates,
        [
            "method",
            "price",
            "standard_error",
            "absolute_error",
            "effective_samples",
            "pilot_samples",
        ],
    )
    example_table = table(
        example,
        [
            "method",
            "rmse",
            "rmse_se",
            "coverage",
            "coverage_low",
            "coverage_high",
            "mean_runtime_seconds",
            "runtime_sd_seconds",
            "variance_reduction",
        ],
    )
    asian_table = table(
        asian_summary,
        [
            "method",
            "replicates",
            "mean_price",
            "empirical_sd",
            "rmse_to_noisy_reference",
            "reference_se",
            "mean_runtime_seconds",
        ],
    )
    case_count = summary.case_id.nunique()
    estimate_count = len(pd.read_parquet(Path(benchmark) / "benchmark_replicates.parquet"))
    report = f"""# Measured results

All numbers below come from the saved completed runs. No single-run timing is used to
claim a universal estimator ranking. Reproduce with the commands in README.md.

## European example
S0=K=100,r=.05,q=.02,sigma=.2,T=1,call,N=100000,seed=42.
Analytical Black–Scholes price: {estimates.benchmark_price.iloc[0]:.9f}.

{european_table}

The budget includes the pilot. This single seed illustrates the interface, not a
statistical verdict. Independent replications provide the main evidence below.

## Repeated-seed study
{case_count} cases × 3 budgets × 100 independent seeds × 3 estimators
= {estimate_count:,} estimates.
The {case_count} cases cross calls/puts, strikes 80/100/120, sigma .15/.4, T .25/2, with
S0=100,r=.05,q=.02. Each cell has 100 independent observations. The overview below
weights all case/budget cells equally; it is not an average over market frequencies.

{table(overview, ["method", "median_variance_reduction", "mean_coverage", "worst_coverage"])}

Variance reduction compares empirical estimate variances at the same payoff budget.
Medians summarise heterogeneous cases: gains are not universal. Extremely large
ratios in nearly linear cases are unstable and should not be generalised. Rare-payoff
coverage materially below .95 demonstrates the limitations of a normal CI.
The mean coverage is also below nominal, especially for controls in this grid.

For the preselected ATM call with sigma=.15,T=2,N=16000:

{example_table}

RMSE uncertainties use a delta-method approximation. Coverage uncertainties use Wilson
intervals. At 100 repeats, an observed coverage such as .91 or .99 does not establish
a permanently miscalibrated method; consult the interval and repeated studies.
Timings include pilots and summaries. Randomised method order reduces order effects,
but CPU load, allocation and platform variation remain. This experiment demonstrates
accuracy/cost tradeoffs, not that one method is always faster.

## Convergence
Log-log RMSE slopes use three budgets (1000,4000,16000); -.5 is the usual CLT rate.

{table(rate_summary, ["method", "median_slope"])}

Per-case bootstrap percentile intervals (500 within-budget resamples, seed 917) are
saved in convergence_rates.parquet. These estimates support approximate inverse-root
scaling in this design; they do not prove a universal asymptotic rate. One running
convergence trace cannot supply independent repeated-run evidence.

## Asian extension
Monthly observations i/12, i=1..12; equal weights, no observation at zero. Same model
parameters as the European example. 50 independent seeds per method at budget 20000.
Independent numerical reference (500000 total budget, geometric control):
{reference["price"]:.9f}, SE {reference["standard_error"]:.9f}, approximate 95% CI
[{reference["ci_low"]:.9f}, {reference["ci_high"]:.9f}]. This is NOT an analytical
arithmetic-average price. Analytical geometric control price:
{reference["geometric_analytical_price"]:.9f}.

{asian_table}

The geometric control substantially reduces empirical spread in this example.
RMSE against the shared numerical reference includes reference noise and can inherit
shared implementation error. We therefore also validate analytical geometric moments,
AM>=GM for call payoffs, deterministic averages, puts and the single-date European limit.

## Environment and provenance
Python {env["python"]}; {env["platform"]}; {env["logical_cpus"]} logical CPUs;
processor {env["processor"]}. Dependencies: {json.dumps(env["dependencies"], sort_keys=True)}.
Wall-clock timing, warmups excluded, no CPU affinity. Runs executed locally; hardware
load was uncontrolled. Git was unavailable due to the host Xcode licence prompt:
commit and dirty state are null, not invented. Each original manifest stores its source
hash and lock hash, seed/configuration and artifact checksums. Source snapshots identify
the code at each run; later documentation/UI adjustments may change the current hash.

Portable evidence: [publication index](../reports/published/publication_index.json).
Original run IDs: {", ".join(index[k]["run_id"] for k in inputs)}.
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
"""
    (ROOT / "docs/RESULTS.md").write_text(report)
    print(destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for flag in ["pricing", "benchmark", "asian"]:
        parser.add_argument(f"--{flag}", required=True)
    args = parser.parse_args()
    publish(args.pricing, args.benchmark, args.asian)
