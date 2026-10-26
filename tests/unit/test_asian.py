from dataclasses import replace

import numpy as np
import pytest

from mc_options.config import Option
from mc_options.models.asian import average_payoffs, geometric_price, simulate_asian
from mc_options.models.black_scholes import black_scholes


@pytest.mark.parametrize("kind", ["call", "put"])
def test_one_observation_reduces_to_european(kind):
    o = Option(option_type=kind)
    assert geometric_price(o, [o.maturity]) == pytest.approx(black_scholes(o), abs=1e-12)
    s = simulate_asian(o, [1.0], 10000, 42, "control")
    assert s.estimate.price == pytest.approx(black_scholes(o), abs=1e-12)
    assert s.estimate.beta == pytest.approx(1.0)


def test_geometric_moments_and_control():
    o = Option()
    dates = np.arange(1, 13) / 12
    a, g = average_payoffs(o, dates, 100000, np.random.default_rng(123))
    assert abs(g.mean() - geometric_price(o, dates)) < 5 * g.std(ddof=1) / np.sqrt(len(g))
    assert np.all(a >= g - 1e-12)
    for kind in ["call", "put"]:
        o = replace(o, option_type=kind)
        plain = simulate_asian(o, dates, 20000, 42, "ordinary")
        control = simulate_asian(o, dates, 20000, 43, "control")
        assert abs(plain.estimate.price - control.estimate.price) < 5 * np.hypot(
            plain.estimate.standard_error, control.estimate.standard_error
        )
        assert control.estimate.standard_error < plain.estimate.standard_error / 5
        assert control.estimate.benchmark_price is None
        np.testing.assert_array_equal(
            control.units, simulate_asian(o, dates, 20000, 43, "control").units
        )


def test_asian_deterministic_and_dates():
    o = Option(volatility=0)
    dates = [0, 0.5, 1]
    expected = np.exp(-o.rate) * max(
        np.mean(o.spot * np.exp((o.rate - o.dividend_yield) * np.array(dates))) - o.strike, 0
    )
    assert simulate_asian(o, dates, 100, 0).estimate.price == pytest.approx(expected)
    for dates in [[], [0.5, 0.5], [-1], [1.1], [float("nan")]]:
        with pytest.raises(ValueError):
            simulate_asian(o, dates, 100, 0)
