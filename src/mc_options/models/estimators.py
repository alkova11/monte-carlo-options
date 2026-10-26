"""Independent-unit uncertainty; pilot cost charged against requested samples."""

from dataclasses import asdict, dataclass
from time import perf_counter

import numpy as np

from mc_options.config import validate_budget
from mc_options.models.black_scholes import black_scholes
from mc_options.models.controls import coefficient
from mc_options.models.payoffs import discounted_payoff
from mc_options.models.sampling import terminal

METHODS = ("ordinary", "antithetic", "control")
Z95 = 1.959963984540054


@dataclass
class Estimate:
    method: str
    requested_samples: int
    used_samples: int
    effective_samples: int
    pilot_samples: int
    seed: int
    price: float
    standard_error: float
    ci_low: float
    ci_high: float
    benchmark_price: float | None
    absolute_error: float | None
    runtime_seconds: float
    beta: float
    zero_payoff_frequency: float
    confidence_method: str
    warning: str

    def to_dict(self):
        return asdict(self)


@dataclass
class Simulation:
    estimate: Estimate
    units: np.ndarray
    payoffs: np.ndarray


def summarize(
    method,
    samples,
    used,
    pilot,
    seed,
    units,
    payoffs,
    reference,
    elapsed,
    beta=0.0,
    deterministic=False,
):
    summary_start = perf_counter()
    n = len(units)
    price = float(np.mean(units))
    se = float(np.std(units, ddof=1) / np.sqrt(n)) if n > 1 else 0.0
    warning = ""
    if not deterministic and (
        np.count_nonzero(payoffs) < 30
        or se == 0
        or (method == "control" and np.count_nonzero(payoffs == 0) < 30)
    ):
        warning = (
            "Rare/constant observed payoffs: normal CI can severely "
            "undercover; zero observed variance does not prove zero price."
        )
    result = Estimate(
        method,
        samples,
        used,
        n,
        pilot,
        seed,
        price,
        se,
        price - Z95 * se,
        price + Z95 * se,
        reference,
        abs(price - reference) if reference is not None else None,
        elapsed,
        beta,
        float(np.mean(payoffs == 0)),
        "exact deterministic"
        if deterministic
        else "normal CLT, independent units; conditional on pilot",
        warning,
    )
    result.runtime_seconds += perf_counter() - summary_start
    return Simulation(result, units, payoffs)


def simulate(o, samples=100_000, seed=42, method="ordinary") -> Simulation:
    validate_budget(samples, seed)
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}")
    start = perf_counter()
    reference = black_scholes(o)
    if o.maturity == 0 or o.volatility == 0:
        return summarize(
            method,
            samples,
            0,
            0,
            seed,
            np.array([reference]),
            np.array([reference]),
            reference,
            perf_counter() - start,
            deterministic=True,
        )
    pilot_rng, rng = [np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(2)]
    beta, pilot = 0.0, 0
    if method == "antithetic":
        z = rng.standard_normal(samples // 2)
        p1 = discounted_payoff(terminal(o, z), o)
        p2 = discounted_payoff(terminal(o, -z), o)
        raw = np.concatenate([p1, p2])
        units = (p1 + p2) / 2
        used = 2 * len(z)
    else:
        if method == "control":
            pilot = max(32, samples // 10)
            st = terminal(o, pilot_rng.standard_normal(pilot))
            beta = coefficient(discounted_payoff(st, o), np.exp(-o.rate * o.maturity) * st)
        st = terminal(o, rng.standard_normal(samples - pilot))
        raw = discounted_payoff(st, o)
        units = raw.copy()
        if method == "control":
            units -= beta * (
                np.exp(-o.rate * o.maturity) * st - o.spot * np.exp(-o.dividend_yield * o.maturity)
            )
        used = samples
    return summarize(
        method, samples, used, pilot, seed, units, raw, reference, perf_counter() - start, beta
    )
