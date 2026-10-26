from dataclasses import replace

import numpy as np
import pytest

from mc_options.config import Option
from mc_options.evaluation.convergence import convergence
from mc_options.models.black_scholes import black_scholes
from mc_options.models.controls import coefficient
from mc_options.models.estimators import METHODS, simulate
from mc_options.models.payoffs import discounted_payoff
from mc_options.models.sampling import terminal


def test_reference_and_parity():
    o = Option(dividend_yield=0)
    assert black_scholes(o) == pytest.approx(10.450583572185565, abs=1e-12)
    assert black_scholes(replace(o, option_type="put")) == pytest.approx(
        5.573526022256971, abs=1e-12
    )
    for q in [0, 0.02, 0.1]:
        for r in [-0.02, 0.05]:
            for t in [0, 0.25, 3]:
                c = replace(o, dividend_yield=q, rate=r, maturity=t)
                p = replace(c, option_type="put")
                parity = c.spot * np.exp(-q * t) - c.strike * np.exp(-r * t)
                assert black_scholes(c) - black_scholes(p) == pytest.approx(parity, abs=1e-12)
                assert max(parity, 0) - 1e-12 <= black_scholes(c) <= c.spot * np.exp(-q * t)


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize(
    "strike,vol,t,q", [(80, 0.25, 0.5, 0), (100, 0.2, 1, 0.02), (120, 0.5, 2, 0.04)]
)
def test_statistical_agreement(method, kind, strike, vol, t, q):
    e = simulate(
        Option(strike=strike, volatility=vol, maturity=t, dividend_yield=q, option_type=kind),
        50_000,
        123,
        method,
    ).estimate
    assert e.absolute_error <= 5 * e.standard_error + 1e-10


@pytest.mark.parametrize("method", METHODS)
def test_limits_seed_and_uncertainty(method):
    for o in [Option(maturity=0, strike=90), Option(volatility=0)]:
        e = simulate(o, 1000, 1, method).estimate
        assert e.price == black_scholes(o)
        assert e.standard_error == 0
        assert e.used_samples == 0
    a = simulate(Option(), 1001, 8, method)
    b = simulate(Option(), 1001, 8, method)
    np.testing.assert_array_equal(a.units, b.units)
    assert a.estimate.standard_error == pytest.approx(
        np.std(a.units, ddof=1) / np.sqrt(len(a.units))
    )
    last = convergence(a).iloc[-1]
    assert last.price == pytest.approx(a.estimate.price)
    assert last.standard_error == pytest.approx(a.estimate.standard_error)
    assert a.estimate.used_samples <= 1001


def test_antithetic_pair_formula():
    o = Option()
    sim = simulate(o, 1000, 42, "antithetic")
    rng = np.random.default_rng(np.random.SeedSequence(42).spawn(2)[1])
    z = rng.standard_normal(500)
    pairs = (discounted_payoff(terminal(o, z), o) + discounted_payoff(terminal(o, -z), o)) / 2
    np.testing.assert_array_equal(sim.units, pairs)
    assert sim.estimate.effective_samples == 500


def test_control_independent_pilot_formula():
    o = Option()
    sim = simulate(o, 1000, 42, "control")
    pilot, main = [np.random.default_rng(s) for s in np.random.SeedSequence(42).spawn(2)]
    xp = np.exp(-o.rate) * terminal(o, pilot.standard_normal(100))
    yp = discounted_payoff(xp / np.exp(-o.rate), o)
    beta = coefficient(yp, xp)
    st = terminal(o, main.standard_normal(900))
    adjusted = discounted_payoff(st, o) - beta * (
        np.exp(-o.rate) * st - o.spot * np.exp(-o.dividend_yield)
    )
    np.testing.assert_allclose(sim.units, adjusted, atol=1e-12)
    assert sim.estimate.beta == pytest.approx(beta)
    assert sim.estimate.pilot_samples == 100
    assert sim.estimate.effective_samples == 900


def test_mc_parity_using_shared_draws():
    o = Option()
    st = terminal(o, np.random.default_rng(10).standard_normal(30_000))
    differences = discounted_payoff(st, o) - discounted_payoff(st, replace(o, option_type="put"))
    expected = o.spot * np.exp(-o.dividend_yield) - o.strike * np.exp(-o.rate)
    assert abs(differences.mean() - expected) < 5 * differences.std(ddof=1) / np.sqrt(len(st))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"spot": 0},
        {"strike": -1},
        {"rate": float("nan")},
        {"volatility": -1},
        {"maturity": -1},
        {"option_type": "x"},
        {"spot": True},
        {"volatility": 3, "maturity": 50},
    ],
)
def test_invalid_option(kwargs):
    with pytest.raises(ValueError):
        Option(**kwargs)


@pytest.mark.parametrize("n,seed", [(99, 0), (2_000_001, 0), (100, -1), (True, 1), (100, 1.5)])
def test_invalid_budget(n, seed):
    with pytest.raises(ValueError):
        simulate(Option(), n, seed)


def test_rare_payoff_warning():
    e = simulate(Option(strike=1000, volatility=0.01), 1000, 1).estimate
    assert e.warning
