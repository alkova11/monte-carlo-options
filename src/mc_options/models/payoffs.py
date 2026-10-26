import numpy as np


def discounted_payoff(values, option):
    sign = 1 if option.option_type == "call" else -1
    return np.exp(-option.rate * option.maturity) * np.maximum(sign * (values - option.strike), 0)
