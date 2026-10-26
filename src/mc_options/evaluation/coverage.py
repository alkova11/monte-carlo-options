import numpy as np

from mc_options.models.estimators import Z95


def wilson(successes, n):
    """Binomial Wilson interval for coverage proportion, including 0/n and n/n."""
    p = successes / n
    d = 1 + Z95**2 / n
    center = (p + Z95**2 / (2 * n)) / d
    half = Z95 * np.sqrt(p * (1 - p) / n + Z95**2 / (4 * n * n)) / d
    return float(center - half), float(center + half)
