import numpy as np
import pandas as pd

from mc_options.config import Option
from mc_options.evaluation.benchmarks import aggregate
from mc_options.models.estimators import simulate


def test_repeated_run_coverage_and_scaling():
    rows = []
    for n in [1000, 4000]:
        for seed in range(200):
            e = simulate(Option(), n, seed, "ordinary").estimate
            rows.append(
                {
                    "case_id": "atm",
                    "method": "ordinary",
                    "sample_count": n,
                    "price": e.price,
                    "error": e.price - e.benchmark_price,
                    "standard_error": e.standard_error,
                    "covered": e.ci_low <= e.benchmark_price <= e.ci_high,
                    "runtime_seconds": e.runtime_seconds,
                }
            )
    summary = aggregate(pd.DataFrame(rows)).sort_values("sample_count")
    assert np.all((summary.coverage > 0.88) & (summary.coverage < 1.0))
    ratio = summary.rmse.iloc[0] / summary.rmse.iloc[1]
    assert 1.5 < ratio < 2.6
    assert np.all(summary.coverage_low < 0.95)
    assert np.all(summary.coverage_high > 0.95)
