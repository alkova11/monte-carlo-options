from dataclasses import asdict
from itertools import product

import numpy as np
import pandas as pd

from mc_options.config import Option, validate_budget
from mc_options.evaluation.coverage import wilson
from mc_options.models.estimators import METHODS, simulate
from mc_options.reporting.artifacts import Run


def aggregate(frame):
    rows = []
    for (case, method, count), g in frame.groupby(["case_id", "method", "sample_count"]):
        errors = g.error.to_numpy()
        squared = errors**2
        mse = squared.mean()
        # Delta-method uncertainty for RMSE; useful only with enough replicates.
        rmse_se = squared.std(ddof=1) / np.sqrt(len(g)) / (2 * np.sqrt(mse)) if mse > 0 else 0.0
        low, high = wilson(int(g.covered.sum()), len(g))
        rows.append(
            {
                "case_id": case,
                "method": method,
                "sample_count": count,
                "replicates": len(g),
                "rmse": np.sqrt(mse),
                "rmse_se": rmse_se,
                "bias": errors.mean(),
                "empirical_variance": g.price.var(ddof=1),
                "mean_reported_variance": np.mean(g.standard_error**2),
                "coverage": g.covered.mean(),
                "coverage_low": low,
                "coverage_high": high,
                "mean_runtime_seconds": g.runtime_seconds.mean(),
                "runtime_sd_seconds": g.runtime_seconds.std(ddof=1),
                "median_runtime_seconds": g.runtime_seconds.median(),
            }
        )
    out = pd.DataFrame(rows)
    plain = out[out.method == "ordinary"].set_index(["case_id", "sample_count"])
    out["variance_reduction"] = [
        plain.loc[(r.case_id, r.sample_count), "empirical_variance"] / r.empirical_variance
        if r.empirical_variance > 0
        else np.nan
        for r in out.itertuples()
    ]
    return out


def benchmark(config, output="reports/experiments"):
    reps = config.get("replicates", 100)
    if isinstance(reps, bool) or not isinstance(reps, int) or not 20 <= reps <= 1000:
        raise ValueError("replicates must be an integer in [20,1000]")
    seed = config.get("seed", 20261025)
    cases = config["cases"]
    counts = config["sample_counts"]
    for count in counts:
        validate_budget(count, seed)
    if not cases or len(cases) * reps * sum(counts) * 3 > 500_000_000:
        raise ValueError("benchmark exceeds 500 million payoff budget")
    options = [Option(**c["option"]) for c in cases]
    if len({c["case_id"] for c in cases}) != len(cases):
        raise ValueError("case IDs must be unique")
    run = Run(config, output)
    try:
        run.json("configuration.json", config)
        run.table(
            "pricing_cases",
            pd.DataFrame(
                [
                    {"case_id": c["case_id"], **asdict(o)}
                    for c, o in zip(cases, options, strict=True)
                ]
            ),
        )
        for method in METHODS:
            simulate(Option(), 2000, 0, method)  # untimed warmup
        jobs = list(product(range(len(cases)), counts, range(reps)))
        streams = np.random.SeedSequence(seed).spawn(len(jobs) * 3)
        rows = []
        index = 0
        order_rng = np.random.default_rng(np.random.SeedSequence(seed, spawn_key=(999,)))
        for ci, n, rep in jobs:
            for method in order_rng.permutation(METHODS):
                method = str(method)
                child_seed = int(
                    streams[index].generate_state(1, dtype=np.uint64)[0] % np.uint64(2**63)
                )
                index += 1
                e = simulate(options[ci], n, child_seed, method).estimate
                rows.append(
                    {
                        "run_id": run.manifest["run_id"],
                        "case_id": cases[ci]["case_id"],
                        "replicate": rep,
                        "sample_count": n,
                        **e.to_dict(),
                        "error": e.price - e.benchmark_price,
                        "covered": e.ci_low <= e.benchmark_price <= e.ci_high,
                    }
                )
        frame = pd.DataFrame(rows)
        summary = aggregate(frame)
        run.table("benchmark_replicates", frame)
        run.table("summary", summary)
        from mc_options.evaluation.convergence import convergence_rates

        run.table("convergence_rates", convergence_rates(frame))
        from mc_options.reporting.charts import research_charts

        for name, fig in research_charts(summary).items():
            run.figure(name, fig)
        run.finish()
    except Exception as exc:
        run.finish(exc)
        raise
    return run.folder
