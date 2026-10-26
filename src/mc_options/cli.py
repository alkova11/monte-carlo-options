import argparse
from dataclasses import asdict

import numpy as np

from mc_options.config import Option, read_config
from mc_options.evaluation.benchmarks import benchmark
from mc_options.evaluation.convergence import convergence
from mc_options.models.estimators import METHODS, simulate
from mc_options.models.sampling import paths
from mc_options.reporting.artifacts import save_pricing
from mc_options.reporting.charts import convergence_chart, path_chart, payoff_chart


def price(config, output="reports/experiments"):
    o = Option(**config.get("option", {}))
    samples = config.get("samples", 100_000)
    seed = config.get("seed", 42)
    method = config.get("method", "control")
    if method not in METHODS:
        raise ValueError("unknown method")
    sims = {m: simulate(o, samples, seed, m) for m in METHODS}
    curves = {m: convergence(s) for m, s in sims.items()}
    times, values = paths(o, np.random.default_rng(np.random.SeedSequence(seed, spawn_key=(99,))))
    figures = {
        "paths": path_chart(times, values),
        "payoffs": payoff_chart(sims[method].payoffs),
        "convergence": convergence_chart(
            curves[method], sims[method].estimate.benchmark_price, method
        ),
    }
    full = {**config, "option": asdict(o), "samples": samples, "seed": seed, "method": method}
    folder = save_pricing(full, sims, curves, figures, output, visual_paths=(times, values))
    return folder


def main():
    parser = argparse.ArgumentParser(description="Monte Carlo option pricing lab")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ["price", "benchmark", "asian"]:
        p = sub.add_parser(name)
        p.add_argument("--config", required=True)
        p.add_argument("--output", default="reports/experiments")
    sub.add_parser("demo")
    args = parser.parse_args()
    try:
        if args.command == "demo":
            folder = price({"option": asdict(Option()), "samples": 100_000, "seed": 42})
        elif args.command == "benchmark":
            folder = benchmark(read_config(args.config), args.output)
        elif args.command == "asian":
            from mc_options.models.asian import asian_experiment

            folder = asian_experiment(read_config(args.config), args.output)
        else:
            folder = price(read_config(args.config), args.output)
    except (ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(folder)


if __name__ == "__main__":
    main()
