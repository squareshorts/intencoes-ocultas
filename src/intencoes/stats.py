"""Paired-bootstrap statistics for invasion analyses with common random numbers.

Every cell (mutant x, resident y) is played on the same game seeds as its
baseline cell (y, y). The per-seed paired difference
    d_s = n * (1[focal wins | x, y] - 1[focal wins | y, y])
is resampled *by seed*, jointly across all cells, so the correlation that the
shared seeds induce between cells is kept in the uncertainty.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def paired_differences(winners: dict, n_players: int, focal_seat: int = 0):
    """winners[(x, y)] -> int array of winning seats per seed (-1 = draw).

    Returns {(x, y): per-seed paired difference vs (y, y)}.
    """
    out = {}
    for (x, y), w in winners.items():
        base = winners[(y, y)]
        out[(x, y)] = n_players * ((w == focal_seat).astype(float) - (base == focal_seat).astype(float))
    return out


def invasion_table(winners: dict, n_players: int, n_boot: int = 2000, seed: int = 0, focal_seat: int = 0):
    """Mean relative invasion fitness with 95% paired-bootstrap CIs, plus the selection gradient.

    The gradient is the least-squares slope (through the origin) of the relative fitness
    on (x - y), pooled over cells; its CI comes from the same joint seed resampling.
    """
    diffs = paired_differences(winners, n_players, focal_seat)
    keys = sorted(diffs)
    D = np.stack([diffs[k] for k in keys])  # cells x seeds
    dx = np.array([x - y for x, y in keys])
    n_seeds = D.shape[1]
    rng = np.random.default_rng(seed)
    boot_means = np.empty((n_boot, len(keys)))
    for b in range(n_boot):
        idx = rng.integers(0, n_seeds, n_seeds)
        boot_means[b] = D[:, idx].mean(axis=1)
    means = D.mean(axis=1)
    slope = lambda m: (dx @ m) / (dx @ dx) if dx @ dx > 0 else np.nan  # noqa: E731
    boot_slopes = np.array([slope(m) for m in boot_means])
    table = pd.DataFrame({
        "mutant": [k[0] for k in keys], "resident": [k[1] for k in keys],
        "rel_fitness": means,
        "ci_low": np.percentile(boot_means, 2.5, axis=0),
        "ci_high": np.percentile(boot_means, 97.5, axis=0),
    })
    gradient = {"gradient": slope(means),
                "ci_low": float(np.percentile(boot_slopes, 2.5)),
                "ci_high": float(np.percentile(boot_slopes, 97.5)),
                "seeds": n_seeds}
    return table, gradient
