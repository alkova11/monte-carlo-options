"""Dividend-adjusted Black–Scholes with deterministic limits."""

import numpy as np
from scipy.special import ndtr


def black_scholes(o) -> float:
    a = o.spot * np.exp(-o.dividend_yield * o.maturity)
    b = o.strike * np.exp(-o.rate * o.maturity)
    sign = 1 if o.option_type == "call" else -1
    if o.maturity == 0 or o.volatility == 0:
        return float(max(sign * (a - b), 0))
    v = o.volatility * np.sqrt(o.maturity)
    d1 = (np.log(o.spot) - np.log(o.strike) + (o.rate - o.dividend_yield) * o.maturity) / v + v / 2
    d2 = d1 - v
    return float(max(sign * (a * ndtr(sign * d1) - b * ndtr(sign * d2)), 0))
