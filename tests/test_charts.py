import numpy as np
import pandas as pd

from analysis import calculate_trend
from charts import build_chart, build_comparison_chart, comparison_data


def test_chart_preserves_selected_range_endpoints_and_gaps():
    annual = pd.DataFrame({'year': [2002, 2004], 'value': [10, 12]})
    fig = build_chart(annual, None, 'Synthetic chart check', 2001, 2025)
    assert tuple(fig.layout.xaxis.range) == (2000.5, 2025.5)
    assert fig.layout.xaxis.type == 'linear'
    assert fig.data[0].x[0] == 2001 and fig.data[0].x[-1] == 2025
    assert np.isnan(fig.data[0].y[2])
    assert fig.data[0].connectgaps is False
    assert 2001 in fig.layout.xaxis.tickvals and 2025 in fig.layout.xaxis.tickvals
    assert '°C' in fig.layout.yaxis.title.text


def test_fit_does_not_extrapolate_to_selected_boundaries():
    annual = pd.DataFrame({'year': range(2005, 2015), 'value': range(10)})
    fig = build_chart(annual, calculate_trend(annual), 'Synthetic', 2001, 2025)
    assert min(fig.data[1].x) == 2005 and max(fig.data[1].x) == 2014
    assert 'unadjusted' in fig.data[1].name


def test_empty_chart_and_single_selected_year():
    fig = build_chart(pd.DataFrame(columns=['year', 'value']), None, 'Empty', 2020, 2020)
    assert tuple(fig.layout.xaxis.range) == (2019.5, 2020.5)
    assert len(fig.data[0].x) == 1


def test_comparison_centers_only_common_years_and_preserves_gaps():
    left = pd.DataFrame({'year': [2001, 2002, 2004, 2005], 'value': [5, 900, 9, 800]})
    right = pd.DataFrame({'year': [2001, 2003, 2004], 'value': [20, 1000, 30]})
    data = comparison_data(left, right, 2001, 2004)
    assert data.year.tolist() == [2001, 2004]
    assert data.first_departure_c.tolist() == [-2, 2]
    assert data.second_departure_c.tolist() == [-5, 5]
    fig = build_comparison_chart(left, right, ('A', 'B'), 2001, 2005)
    assert np.isnan(fig.data[0].y[1]) and np.isnan(fig.data[1].y[2])
    assert all(trace.connectgaps is False for trace in fig.data)
    assert tuple(fig.layout.xaxis.range) == (2000.5, 2005.5)
    absolute = build_comparison_chart(left, right, ('A', 'B'), 2001, 2005, relative=False)
    assert absolute.data[0].y[0] == 5 and absolute.data[1].y[0] == 20


def test_centering_does_not_change_fitted_slope():
    annual = pd.DataFrame({'year': range(2001, 2026), 'value': np.arange(25) * .07 + 20})
    data = comparison_data(annual, annual, 2001, 2025)
    centered = data[['year', 'first_departure_c']].rename(columns={'first_departure_c': 'value'})
    assert np.isclose(calculate_trend(annual)['slope_per_decade'], calculate_trend(centered)['slope_per_decade'])


def test_empty_comparison_keeps_selected_range():
    empty = pd.DataFrame(columns=['year', 'value'])
    fig = build_comparison_chart(empty, empty, ('A', 'B'), 2001, 2025)
    assert len(fig.data) == 2 and len(fig.data[0].x) == 25
    assert np.isnan(fig.data[0].y).all()
