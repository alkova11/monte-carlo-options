import numpy as np

from mc_options.models.estimators import Z95


def convergence_data(simulation, points=80):
    x = simulation.units
    if len(x) == 1:
        return {
            "effective_samples": np.array([1]),
            "sample_count": np.array([0]),
            "price": x,
            "standard_error": np.array([0.0]),
            "ci_low": x,
            "ci_high": x,
        }
    n = np.unique(np.geomspace(min(30, len(x)), len(x), points).astype(int))
    center = x[0]
    shifted = x - center
    total = np.cumsum(shifted)[n - 1]
    squares = np.cumsum(shifted**2)[n - 1]
    mean = center + total / n
    se = np.sqrt(np.maximum((squares - total**2 / n) / (n - 1), 0) / n)
    e = simulation.estimate
    cost = n * (2 if e.method == "antithetic" else 1) + e.pilot_samples
    return {
        "effective_samples": n,
        "sample_count": cost,
        "price": mean,
        "standard_error": se,
        "ci_low": mean - Z95 * se,
        "ci_high": mean + Z95 * se,
    }


def convergence(simulation, points=80):
    import pandas as pd

    return pd.DataFrame(convergence_data(simulation, points))


def convergence_rates(frame, bootstrap_seed=917, resamples=500):
    """Bootstrap independent replicates within each budget; fit log RMSE vs log N."""
    import pandas as pd

    rng = np.random.default_rng(bootstrap_seed)
    rows = []
    for (case, method), g in frame.groupby(["case_id", "method"]):
        groups = list(g.groupby("sample_count", sort=True))
        if len(groups) < 2:
            continue
        x = np.log([n for n, _ in groups])
        centered = x - x.mean()
        log_rmse = []
        boot_log_rmse = []
        for _, h in groups:
            errors = h.error.to_numpy()
            mse = np.mean(errors**2)
            log_rmse.append(np.log(max(np.sqrt(mse), np.finfo(float).tiny)))
            indices = rng.integers(0, len(errors), (resamples, len(errors)))
            rmses = np.sqrt(np.mean(errors[indices] ** 2, axis=1))
            boot_log_rmse.append(np.log(np.maximum(rmses, np.finfo(float).tiny)))
        slope = np.dot(centered, log_rmse) / np.dot(centered, centered)
        boot = centered @ np.array(boot_log_rmse) / np.dot(centered, centered)
        lo, hi = np.quantile(boot, [0.025, 0.975])
        rows.append(
            {
                "case_id": case,
                "method": method,
                "slope": slope,
                "bootstrap_low": lo,
                "bootstrap_high": hi,
                "bootstrap_resamples": resamples,
                "bootstrap_seed": bootstrap_seed,
            }
        )
    return pd.DataFrame(rows)
