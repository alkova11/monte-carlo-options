"""Discrete equally weighted arithmetic Asian; geometric Asian analytic control."""

from dataclasses import asdict
from time import perf_counter

import numpy as np
from scipy.special import ndtr

from mc_options.config import Option, validate_budget
from mc_options.models.controls import coefficient
from mc_options.models.estimators import summarize
from mc_options.models.payoffs import discounted_payoff


def validate_dates(o, dates):
    a = np.asarray(dates, dtype=float)
    if a.ndim != 1 or not 1 <= len(a) <= 365 or not np.all(np.isfinite(a)):
        raise ValueError("provide 1–365 finite observation dates")
    if a[0] < 0 or a[-1] > o.maturity or np.any(np.diff(a) <= 0):
        raise ValueError("dates must be strictly increasing in [0,T]")
    return a


def geometric_price(o, dates):
    t = validate_dates(o, dates)
    mu = np.log(o.spot) + (o.rate - o.dividend_yield - 0.5 * o.volatility**2) * t.mean()
    var = o.volatility**2 * np.minimum.outer(t, t).mean()
    sign = 1 if o.option_type == "call" else -1
    if var == 0:
        return float(discounted_payoff(np.exp(mu), o))
    d2 = (mu - np.log(o.strike)) / np.sqrt(var)
    d1 = d2 + np.sqrt(var)
    return float(
        np.exp(-o.rate * o.maturity)
        * sign
        * (np.exp(mu + var / 2) * ndtr(sign * d1) - o.strike * ndtr(sign * d2))
    )


def average_payoffs(o, dates, n, rng):
    """Stream observation dates: O(n) memory, exact GBM increments."""
    log_s = np.full(n, np.log(o.spot))
    arithmetic = np.zeros(n)
    geometric_log = np.zeros(n)
    previous = 0.0
    for date in dates:
        dt = date - previous
        log_s += (o.rate - o.dividend_yield - 0.5 * o.volatility**2) * dt + o.volatility * np.sqrt(
            dt
        ) * rng.standard_normal(n)
        arithmetic += np.exp(log_s)
        geometric_log += log_s
        previous = date
    return discounted_payoff(arithmetic / len(dates), o), discounted_payoff(
        np.exp(geometric_log / len(dates)), o
    )


def simulate_asian(o, dates, samples=100_000, seed=42, method="control"):
    validate_budget(samples, seed)
    dates = validate_dates(o, dates)
    if samples * len(dates) > 50_000_000:
        raise ValueError("Asian run limited to 50 million observation evaluations")
    if method not in {"ordinary", "control"}:
        raise ValueError("Asian supports ordinary or geometric control")
    start = perf_counter()
    if o.volatility == 0 or dates[-1] == 0:
        avg = np.mean(o.spot * np.exp((o.rate - o.dividend_yield) * dates))
        exact = float(discounted_payoff(avg, o))
        return summarize(
            method,
            samples,
            0,
            0,
            seed,
            np.array([exact]),
            np.array([exact]),
            None,
            perf_counter() - start,
            deterministic=True,
        )
    pilot_rng, rng = [np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(2)]
    pilot = max(32, samples // 10) if method == "control" else 0
    beta = 0.0
    if pilot:
        yp, xp = average_payoffs(o, dates, pilot, pilot_rng)
        beta = coefficient(yp, xp)
    raw, x = average_payoffs(o, dates, samples - pilot, rng)
    units = raw - beta * (x - geometric_price(o, dates)) if pilot else raw.copy()
    return summarize(
        method, samples, samples, pilot, seed, units, raw, None, perf_counter() - start, beta
    )


def asian_experiment(config, output="reports/experiments"):
    import pandas as pd

    from mc_options.reporting.artifacts import Run

    o = Option(**config["option"])
    dates = validate_dates(o, config["observation_dates"])
    samples = config.get("samples", 20_000)
    reps = config.get("replicates", 50)
    ref_n = config.get("reference_samples", 500_000)
    seed = config.get("seed", 1234)
    validate_budget(samples, seed)
    validate_budget(ref_n, seed)
    if (
        not isinstance(reps, int)
        or not 20 <= reps <= 500
        or (2 * reps * samples + ref_n) * len(dates) > 150_000_000
    ):
        raise ValueError("Asian experiment limited to 20–500 repeats and 150 million observations")
    run = Run(config, output)
    try:
        children = np.random.SeedSequence(seed).spawn(2 * reps + 1)
        seeds = [int(s.generate_state(1, dtype=np.uint64)[0] % np.uint64(2**63)) for s in children]
        reference = simulate_asian(o, dates, ref_n, seeds[0], "control").estimate
        rows = []
        for rep in range(reps):
            for j, m in enumerate(["ordinary", "control"]):
                e = simulate_asian(o, dates, samples, seeds[1 + 2 * rep + j], m).estimate
                rows.append(
                    {
                        "run_id": run.manifest["run_id"],
                        "replicate": rep,
                        **e.to_dict(),
                        "difference_from_numerical_reference": e.price - reference.price,
                        "combined_standard_error": float(
                            np.hypot(e.standard_error, reference.standard_error)
                        ),
                    }
                )
        frame = pd.DataFrame(rows)
        run.json("configuration.json", config)
        run.table(
            "pricing_cases",
            pd.DataFrame([{"case_id": "asian", **asdict(o), "observation_dates": list(dates)}]),
        )
        run.json(
            "reference.json",
            {
                "kind": (
                    "independent numerical geometric-control estimate; NOT analytical "
                    "arithmetic price"
                ),
                "geometric_analytical_price": geometric_price(o, dates),
                **reference.to_dict(),
            },
        )
        run.table("asian_replicates", frame)
        summaries = []
        for m, g in frame.groupby("method"):
            summaries.append(
                {
                    "method": m,
                    "replicates": reps,
                    "mean_price": g.price.mean(),
                    "empirical_sd": g.price.std(ddof=1),
                    "rmse_to_noisy_reference": np.sqrt(
                        np.mean(g.difference_from_numerical_reference**2)
                    ),
                    "reference_se": reference.standard_error,
                    "mean_runtime_seconds": g.runtime_seconds.mean(),
                }
            )
        run.table("summary", pd.DataFrame(summaries))
        run.finish()
    except Exception as exc:
        run.finish(exc)
        raise
    return run.folder
