import numpy as np


def terminal(o, z):
    return o.spot * np.exp(
        (o.rate - o.dividend_yield - 0.5 * o.volatility**2) * o.maturity
        + o.volatility * np.sqrt(o.maturity) * z
    )


def paths(o, rng, count=30, steps=100):
    if not 1 <= count <= 200 or not 1 <= steps <= 1000:
        raise ValueError("visual paths limited to 200 paths and 1000 steps")
    times = np.linspace(0, o.maturity, steps + 1)
    dt = np.diff(times)
    increments = (o.rate - o.dividend_yield - 0.5 * o.volatility**2) * dt + o.volatility * np.sqrt(
        dt
    ) * rng.standard_normal((count, steps))
    values = o.spot * np.exp(np.cumsum(increments, axis=1))
    return times, np.column_stack([np.full(count, o.spot), values])
