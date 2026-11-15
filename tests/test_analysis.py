"""Synthetic numerical fixtures only; these are not NASA observations."""
import numpy as np
import pandas as pd
import pytest
from scipy import stats

from analysis import align_annual, annual_coverage, annualize_monthly, calculate_trend


def monthly(start='2020-01-01', periods=12):
    return pd.DataFrame({'date': pd.date_range(start, periods=periods, freq='MS'),
                         'value': np.arange(periods, dtype=float)})


def annual():
    years = np.arange(2001, 2021)
    return pd.DataFrame({'year': years, 'value': 0.2 * (years - 2001) + 11})


def test_annualize_excludes_partial_years():
    assert annualize_monthly(monthly(periods=18))['year'].tolist() == [2020]


@pytest.mark.parametrize('year,days', [(2019, 365), (2020, 366)])
def test_day_weighting_including_leap_year(year, days):
    frame = monthly(f'{year}-01-01')
    expected = sum(frame.value * frame.date.dt.days_in_month) / days
    assert annualize_monthly(frame).value.iloc[0] == pytest.approx(expected)
    assert expected != pytest.approx(frame.value.mean())


@pytest.mark.parametrize('invalid', [None, np.nan, np.inf, -np.inf, 'bad'])
def test_missing_or_nonfinite_month_excludes_year(invalid):
    frame = monthly().astype({'value': object})
    frame.loc[3, 'value'] = invalid
    assert annualize_monthly(frame).empty


def test_duplicate_month_rejected_even_with_missing_value():
    frame = pd.concat([monthly(), monthly().iloc[[0]].assign(value=np.nan)])
    with pytest.raises(ValueError, match='same month'):
        annualize_monthly(frame)


def test_invalid_date_rejected():
    frame = monthly().astype({'date': object})
    frame.loc[0, 'date'] = 'invalid'
    with pytest.raises(ValueError, match='dates'):
        annualize_monthly(frame)


def test_unsorted_input_midmonth_and_numeric_strings():
    frame = monthly()
    frame.date = frame.date.map(lambda date: date.replace(day=15))
    frame.value = frame.value.astype(str)
    pd.testing.assert_frame_equal(annualize_monthly(frame.iloc[::-1]), annualize_monthly(monthly()))


def test_empty_data_and_all_missing_coverage():
    empty = pd.DataFrame(columns=['date', 'value'])
    assert annualize_monthly(empty).empty
    coverage = annual_coverage(empty, 2000, 2001)
    assert coverage.valid_months.tolist() == [0, 0]
    assert coverage.complete.tolist() == [False, False]


def test_coverage_missing_and_absent_years():
    frame = monthly().drop(index=1)
    coverage = annual_coverage(frame, 2019, 2021)
    assert coverage.valid_months.tolist() == [0, 11, 0]
    assert coverage.iloc[1].missing_months == '02'


def test_known_slope_and_decadal_interval():
    result = calculate_trend(annual())
    assert result['slope_per_decade'] == pytest.approx(2)
    assert result['n_years'] == 20
    assert result['fitted'].value.tolist() == pytest.approx(annual().value.tolist())


def test_uncertainty_against_independent_formula():
    frame = annual()
    frame.value += np.array([1, -1, 0, 2, -2] * 4)
    x, y = frame.year.to_numpy(), frame.value.to_numpy()
    centered = x - x.mean()
    slope = sum(centered * (y - y.mean())) / sum(centered ** 2)
    residual = y - (y.mean() + slope * centered)
    se = np.sqrt(sum(residual ** 2) / (len(x) - 2) / sum(centered ** 2))
    ci = stats.t.ppf(.975, len(x) - 2) * se
    result = calculate_trend(frame)
    assert result['lower_95_per_decade'] == pytest.approx((slope - ci) * 10)
    assert result['upper_95_per_decade'] == pytest.approx((slope + ci) * 10)
    assert result['p_value'] == pytest.approx(2 * stats.t.sf(abs(slope / se), len(x) - 2))
    assert 'not autocorrelation-adjusted' in result['inference_method']


def test_calendar_gaps_not_row_number_regression():
    frame = annual().drop(index=[2, 6, 7])
    result = calculate_trend(frame)
    assert result['slope_per_decade'] == pytest.approx(2)
    assert result['missing_years'] == [2003, 2007, 2008]


def test_constant_series_withholds_inference():
    result = calculate_trend(annual().assign(value=10))
    assert result['slope_per_decade'] == 0
    assert result['p_value'] is None
    assert result['r_squared'] is None
    assert result['lower_95_per_decade'] is None


def test_insufficient_years():
    with pytest.raises(ValueError, match='10 complete'):
        calculate_trend(annual().head(9))


@pytest.mark.parametrize('column,value', [('year', 2001), ('year', 2002.5), ('year', 'bad'),
                                         ('value', np.inf), ('value', np.nan)])
def test_invalid_annual_input(column, value):
    frame = annual().astype({column: object})
    frame.loc[1, column] = value
    with pytest.raises(ValueError):
        calculate_trend(frame)


def test_comparison_uses_identical_years_including_interior_gaps():
    first = annual().drop(index=[0, 3])
    second = annual().drop(index=[19, 7]).assign(value=lambda f: -f.value)
    left, right = align_annual(first, second)
    assert left.year.tolist() == right.year.tolist()
    assert left.year.tolist() == sorted(set(first.year) & set(second.year))
    assert calculate_trend(left)['slope_per_decade'] == pytest.approx(2)
    assert calculate_trend(right)['slope_per_decade'] == pytest.approx(-2)


def test_no_common_years():
    left, right = align_annual(annual(), annual().assign(year=lambda f: f.year + 50))
    assert left.empty and right.empty
