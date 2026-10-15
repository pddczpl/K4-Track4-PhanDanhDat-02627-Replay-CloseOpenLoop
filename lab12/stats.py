"""Small statistics helpers."""
import numpy as np


def wilson(k, n, z=1.96):
    """Wilson score interval for a proportion k/n (95 % by default). Returns (low, high)."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1.0 + (z ** 2) / n
    center = (p + (z ** 2) / (2.0 * n)) / d
    half_width = (z * np.sqrt((p * (1.0 - p) / n) + ((z ** 2) / (4.0 * (n ** 2))))) / d
    lo = float(max(0.0, min(1.0, center - half_width)))
    hi = float(max(0.0, min(1.0, center + half_width)))
    return (lo, hi)



def rate(flags):
    """{'k','n','rate','ci95'} for a boolean array."""
    flags = np.asarray(flags, bool)
    k, n = int(flags.sum()), int(flags.size)
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": k / n if n else float("nan"), "ci95": [lo, hi]}


def wasserstein1(a, b, n=200):
    """1-D Wasserstein distance between two samples (mean absolute difference of the quantile functions)."""
    q = np.linspace(0.005, 0.995, n)
    return float(np.mean(np.abs(np.quantile(a, q) - np.quantile(b, q))))
