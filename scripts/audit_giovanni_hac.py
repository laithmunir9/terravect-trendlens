"""Offline feasibility audit, NOT a validated inference API or app dependency.

Only the reviewed 2002–2025 snapshot is loaded by main. Synthetic stationary
Gaussian AR(1) nulls probe calibration; they are not a fitted climate noise model.
Run from the repository root: .venv/bin/python scripts/audit_giovanni_hac.py
"""
from pathlib import Path
import json
import sys

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis import annualize_monthly
from giovanni_snapshot import load_giovanni_snapshot

YEARS = np.arange(2002, 2026)
LAGS = tuple(range(1, 7))
SEED = 20261115
REPLICATES = 20_000


def _candidate(years, values, lag):
    """Fixed-design OLS slope and Bartlett HAC SE, with n/(n-2) correction.

    Private audit helper; the last axis is time, earlier axes are simulations.
    Never compress missing calendar years. No p-values or decisions are returned.
    """
    if not np.array_equal(np.asarray(years), YEARS):
        raise ValueError('Audit requires ordered consecutive calendar years 2002–2025.')
    y = np.asarray(values, dtype=float)
    if y.ndim not in (1, 2) or y.shape[-1] != len(YEARS) or not np.isfinite(y).all():
        raise ValueError('Audit requires 24 finite annual values per series.')
    if isinstance(lag, bool) or not isinstance(lag, (int, np.integer)) or lag not in range(7):
        raise ValueError('Audit lag must be an integer from 0 to 6.')
    x = YEARS - YEARS.mean()
    slope = y @ x / (x @ x)
    residual = y - y.mean(axis=-1, keepdims=True) - slope[..., None] * x
    if np.any(np.sum(residual**2, axis=-1) <= np.finfo(float).eps * np.sum(y**2, axis=-1)):
        raise ValueError('Constant or numerically exact linear series cannot support this audit.')
    # Slope influence scores: algebraically the slope diagonal of the full
    # (X'X)^-1 X' diag(e) W diag(e) X (X'X)^-1 sandwich.
    score = residual * x / (x @ x)
    variance = np.sum(score**2, axis=-1)
    for distance in range(1, lag + 1):
        weight = 1 - distance / (lag + 1)
        variance += 2 * weight * np.sum(score[..., distance:] * score[..., :-distance], axis=-1)
    variance *= len(YEARS) / (len(YEARS) - 2)
    if np.any(variance <= 0) or not np.isfinite(variance).all():
        raise ValueError('Invalid HAC variance; inference withheld.')
    return slope, np.sqrt(variance)


def _null_calibration(replicates=REPLICATES, seed=SEED):
    """False-positive rates for a candidate two-sided t(22), nominal 5% test.

    Start AR(1) at its stationary distribution: no arbitrary burn-in. Innovations
    have unit variance; the trend test is invariant to their scale. Each rho uses
    fresh draws, with the same draws across lags. No rho is estimated from data.
    """
    rng = np.random.default_rng(seed)
    critical = stats.t.ppf(.975, len(YEARS) - 2)
    rows = []
    for rho in (0., .3, .6, .9):
        errors = rng.normal(size=(replicates, len(YEARS)))
        errors[:, 0] /= np.sqrt(1 - rho**2)
        for t in range(1, len(YEARS)):
            errors[:, t] += rho * errors[:, t - 1]
        rejections = []
        for lag in LAGS:
            slope, se = _candidate(YEARS, errors, lag)
            rejections.append(np.abs(slope / se) > critical)
        rates = np.mean(rejections, axis=1)
        rows.append({'rho': rho, 'false_positive_rate_by_lag': rates.tolist(),
                     'monte_carlo_se_by_lag': np.sqrt(rates * (1 - rates) / replicates).tolist(),
                     'reject_at_every_lag_rate': float(np.mean(np.all(rejections, axis=0)))})
    return rows


def main():
    snapshot = load_giovanni_snapshot()  # Existing checksum and provenance checks.
    annual = annualize_monthly(snapshot.monthly)  # Existing day weighting, unchanged.
    sensitivity = []
    for lag in (0, *LAGS):
        slope, se = _candidate(annual.year, annual.value, lag)
        sensitivity.append({'lag_years': lag, 'candidate_se_C_per_decade': float(se * 10)})
    print(json.dumps({
        'status': 'NOT VALIDATED: app significance assessment remains withheld',
        'snapshot_sha256': snapshot.provenance['file_sha256'],
        'years': annual.year.tolist(), 'slope_C_per_decade': float(slope * 10),
        'candidate': 'Bartlett HAC; n/(n-2) covariance correction; approximate t(22)',
        'observed_lag_sensitivity': sensitivity,
        'nominal_null_rejection_rate': .05, 'replicates_per_rho': REPLICATES,
        'seed': SEED, 'null_calibration': _null_calibration(),
    }, indent=2))


if __name__ == '__main__':
    main()
