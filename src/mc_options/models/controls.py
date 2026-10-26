import numpy as np


def coefficient(payoffs, control):
    """OLS slope with intercept, fitted on an independent pilot only."""
    x = control - control.mean()
    denom = np.dot(x, x)
    return float(np.dot(x, payoffs - payoffs.mean()) / denom) if denom > 0 else 0.0
