"""Validated model parameters; currency units match spot and strike."""

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Option:
    spot: float = 100.0
    strike: float = 100.0
    rate: float = 0.05
    dividend_yield: float = 0.02
    volatility: float = 0.2
    maturity: float = 1.0
    option_type: str = "call"

    def __post_init__(self):
        for key, value in asdict(self).items():
            if key != "option_type" and (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError(f"{key} must be a finite number")
        if self.option_type not in {"call", "put"}:
            raise ValueError("option_type must be call or put")
        if not (0 < self.spot <= 1e9 and 0 < self.strike <= 1e9):
            raise ValueError("spot and strike must be in (0, 1e9]")
        if not (0 <= self.volatility <= 3 and 0 <= self.maturity <= 50):
            raise ValueError("volatility must be in [0,3], maturity in [0,50] years")
        if abs(self.rate) > 1 or abs(self.dividend_yield) > 1:
            raise ValueError("rates and dividend yields must be in [-1,1]")
        if (2 * abs(self.rate - self.dividend_yield) + self.volatility**2) * self.maturity > 150:
            raise ValueError("combined parameters exceed numerical moment limit")


def validate_budget(samples, seed):
    if isinstance(samples, bool) or not isinstance(samples, int) or not 100 <= samples <= 2_000_000:
        raise ValueError("samples must be an integer in [100, 2000000]")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**63:
        raise ValueError("seed must be an integer in [0, 2**63)")


def read_config(path):
    return json.loads(Path(path).read_text())
