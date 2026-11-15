"""Interpretation edge cases use synthetic statistics, not NASA conclusions."""
import pytest

from insights import explain_trend, investigation_brief


def result(**overrides):
    return dict(slope_per_decade=.2, lower_95_per_decade=.1, upper_95_per_decade=.3,
                n_years=20, first_year=2001, last_year=2020, years_used=list(range(2001, 2021)),
                p_value=.01, inference_warning=None) | overrides


@pytest.mark.parametrize('slope,word', [(.2, 'increased'), (-.2, 'decreased'), (0, 'was flat')])
def test_magnitude_direction_and_fitted_interval(slope, word):
    text = explain_trend(result(slope_per_decade=slope))['magnitude']
    assert word in text and f'{slope * 1.9:+.2f} °C' in text
    assert 'not the difference between two observed endpoints' in text


@pytest.mark.parametrize('low,high', [(-.1, .3), (0, .3), (-.3, 0)])
def test_interval_touching_zero_never_claims_nonzero_trend(low, high):
    text = explain_trend(result(lower_95_per_decade=low, upper_95_per_decade=high))['evidence']
    assert 'includes zero' in text and 'does not prove' in text


def test_nonzero_interval_qualifies_inference():
    text = explain_trend(result())['evidence']
    assert 'excludes zero' in text and 'independent-error OLS assumptions' in text
    assert 'Statistical significance is not established' in text
    assert 'does not establish a statistically significant environmental change' in text


@pytest.mark.parametrize('warning', ['Constant annual values; OLS inference is undefined.', 'Exact linear fit; zero residual uncertainty.'])
def test_degenerate_series_does_not_claim_significance(warning):
    text = explain_trend(result(inference_warning=warning))['evidence']
    assert warning in text and 'Do not use this fit to claim statistical significance' in text


def test_brief_contains_traceability_and_no_result_state():
    provenance = {'source': 'SYNTHETIC TEST', 'selected_years': [2001, 2020],
                  'response_sha256': 'fixture-hash', 'access_mode': 'test only'}
    brief = investigation_brief('Test', None, provenance)
    assert 'No trend estimate' in brief and 'fixture-hash' in brief and 'test only' in brief
    assert 'No statistical test of the difference' in brief
