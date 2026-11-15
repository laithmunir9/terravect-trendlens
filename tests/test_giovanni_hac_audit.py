"""Audit arithmetic and failure evidence; no production significance claims."""
import numpy as np
import pytest

from analysis import INFERENCE_STATUS, annualize_monthly, calculate_trend
from giovanni_snapshot import load_giovanni_snapshot
from scripts.audit_giovanni_hac import YEARS, _candidate, _null_calibration


@pytest.mark.parametrize('lag', range(7))
def test_against_full_matrix_sandwich(lag):
    # Independent full-matrix formulation, including intercept and Bartlett W.
    y = np.random.default_rng(43).normal(size=24) + .04 * (YEARS - 2002)
    design = np.column_stack([np.ones(24), YEARS - YEARS.mean()])
    inverse = np.linalg.inv(design.T @ design)
    beta = inverse @ design.T @ y
    residual = y - design @ beta
    distances = np.abs(YEARS[:, None] - YEARS[None, :])
    weights = np.maximum(0, 1 - distances / (lag + 1))
    omega = residual[:, None] * weights * residual[None, :]
    covariance = (24 / 22) * inverse @ design.T @ omega @ design @ inverse
    slope, se = _candidate(YEARS, y, lag)
    assert slope == pytest.approx(beta[1], abs=1e-14)
    assert se == pytest.approx(np.sqrt(covariance[1, 1]), rel=1e-12)


@pytest.mark.parametrize('years', [YEARS[:-1], YEARS[::-1], YEARS + 1,
                                  np.delete(YEARS, 10), np.r_[YEARS[:-1], 2024]])
def test_rejects_other_windows_gaps_order_and_duplicates(years):
    with pytest.raises(ValueError, match='calendar years'):
        _candidate(years, np.arange(len(years)), 2)


@pytest.mark.parametrize('values', [np.ones(24), np.arange(24), np.full(24, np.nan),
                                   np.full(24, np.inf), np.ones(23)])
def test_withholds_degenerate_or_invalid_data(values):
    with pytest.raises(ValueError):
        _candidate(YEARS, values, 2)


@pytest.mark.parametrize('lag', [-1, 7, 1.5, True])
def test_invalid_lags(lag):
    with pytest.raises(ValueError, match='lag'):
        _candidate(YEARS, np.random.default_rng(1).normal(size=24), lag)


def test_snapshot_slope_unchanged_and_inference_still_withheld():
    annual = annualize_monthly(load_giovanni_snapshot().monthly)
    original = calculate_trend(annual)
    slope, se = _candidate(annual.year, annual.value, 2)
    assert slope * 10 == pytest.approx(original['slope_per_decade'], abs=1e-12)
    assert slope * 10 == pytest.approx(.35584302739107976)
    assert se * 10 == pytest.approx(.0847757536327741)
    assert original['inference_status'] == INFERENCE_STATUS
    assert original['autocorrelation_adjusted'] is False


def test_batch_and_unit_conversion():
    y = np.random.default_rng(7).normal(size=24)
    slope, se = _candidate(YEARS, y, 3)
    slopes, ses = _candidate(YEARS, np.stack([y, 10 * y + 273.15]), 3)
    assert slopes == pytest.approx([slope, 10 * slope])
    assert ses == pytest.approx([se, 10 * se])


def test_candidate_fails_small_sample_null_calibration():
    # Broad deterministic regression guard, not a claim to validate all noise models.
    rows = _null_calibration()
    moderate = rows[1]
    assert moderate['rho'] == .3
    assert min(moderate['false_positive_rate_by_lag']) > .12
    assert moderate['reject_at_every_lag_rate'] > .12
    assert max(moderate['monte_carlo_se_by_lag']) < .004
