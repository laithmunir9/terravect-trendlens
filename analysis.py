"""Annual temperature aggregation and exploratory, unadjusted OLS statistics."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

INFERENCE_STATUS = ('Exploratory OLS only. Statistical significance is not established: '
                    'year-to-year dependence has not been validated or corrected.')


def normalize_monthly(monthly: pd.DataFrame) -> pd.DataFrame:
    """Validate monthly frequency; never silently choose duplicate months.

    Source-specific fill values must be decoded by the source parser first.
    Non-numeric and non-finite measurements count as missing, never as zero.
    """
    if not {'date', 'value'} <= set(monthly.columns):
        raise ValueError('Monthly data need date and value columns.')
    df = monthly[['date', 'value']].copy()
    dates = pd.to_datetime(df['date'], errors='coerce', utc=True, format='mixed')
    if dates.isna().any():
        raise ValueError('Monthly data contain invalid or missing dates.')
    df['date'] = dates.dt.tz_convert(None).dt.to_period('M').dt.to_timestamp()
    if df['date'].duplicated().any():
        raise ValueError('Multiple rows occur in the same month. Supply monthly means; duplicate months are not averaged or discarded.')
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df.loc[~np.isfinite(df['value']), 'value'] = np.nan
    return df.sort_values('date').reset_index(drop=True)


def annual_coverage(monthly: pd.DataFrame, start: int, end: int) -> pd.DataFrame:
    """Report every selected year, including years with no records at all."""
    if start > end:
        raise ValueError('Start year must not exceed end year.')
    df = normalize_monthly(monthly).set_index('date')
    expected = pd.date_range(f'{start}-01-01', f'{end}-12-01', freq='MS')
    df = df.reindex(expected)
    rows = []
    for year, group in df.groupby(df.index.year):
        valid = group['value'].notna()
        rows.append({'year': int(year), 'valid_months': int(valid.sum()),
                     'missing_months': ', '.join(group.index[~valid].strftime('%m')),
                     'complete': bool(valid.all())})
    return pd.DataFrame(rows)


def annualize_monthly(monthly: pd.DataFrame) -> pd.DataFrame:
    """Day-weighted means of exactly 12 finite monthly means per calendar year.

    Appropriate for monthly mean temperatures, not monthly totals. No imputation
    or extrapolation is performed; leap days are included.
    """
    df = normalize_monthly(monthly)
    rows = []
    for year, group in df.groupby(df['date'].dt.year):
        if len(group) == 12 and group['value'].notna().all():
            rows.append({'year': int(year), 'value': float(np.average(
                group['value'], weights=group['date'].dt.days_in_month))})
    return pd.DataFrame(rows, columns=['year', 'value'])


def _validate_annual(annual: pd.DataFrame) -> pd.DataFrame:
    if not {'year', 'value'} <= set(annual.columns):
        raise ValueError('Annual data need year and value columns.')
    df = annual[['year', 'value']].apply(pd.to_numeric, errors='coerce')
    if not np.isfinite(df.to_numpy(dtype=float)).all():
        raise ValueError('Annual years and values must be finite numbers.')
    if (df['year'] % 1 != 0).any() or not df['year'].between(1, 9999).all():
        raise ValueError('Annual years must be valid integer calendar years.')
    if df['year'].duplicated().any():
        raise ValueError('Annual data contain duplicate years.')
    df['year'] = df['year'].astype(int)
    return df.sort_values('year').reset_index(drop=True)


def align_annual(first: pd.DataFrame, second: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Both fits use the exact same complete years, including interior gaps."""
    first, second = _validate_annual(first), _validate_annual(second)
    common = sorted(set(first['year']) & set(second['year']))
    return (first.set_index('year').reindex(common).reset_index(),
            second.set_index('year').reindex(common).reset_index())


def calculate_trend(annual: pd.DataFrame) -> dict:
    """Two-sided OLS t-test and 95% slope CI; NOT autocorrelation-adjusted.

    Ten years is a guardrail, not evidence of sufficient statistical power.
    Calendar years preserve gaps in the fit. Constant series withhold inference.
    """
    df = _validate_annual(annual)
    if len(df) < 10:
        raise ValueError('At least 10 complete annual values are needed for a trend estimate.')
    x, y = df['year'].to_numpy(dtype=float), df['value'].to_numpy(dtype=float)
    constant = np.ptp(y) == 0
    result = stats.linregress(x, y)
    slope_ci = stats.t.ppf(0.975, df=len(x) - 2) * result.stderr
    return {
        'slope_per_decade': float(result.slope * 10),
        'lower_95_per_decade': None if constant else float((result.slope - slope_ci) * 10),
        'upper_95_per_decade': None if constant else float((result.slope + slope_ci) * 10),
        'p_value': None if constant else float(result.pvalue),
        'r_squared': None if constant else float(result.rvalue**2),
        'n_years': len(df), 'first_year': int(x.min()), 'last_year': int(x.max()),
        'years_used': df['year'].tolist(),
        'missing_years': sorted(set(range(int(x.min()), int(x.max()) + 1)) - set(df['year'])),
        'inference_method': 'Ordinary OLS; not autocorrelation-adjusted',
        'inference_status': INFERENCE_STATUS,
        'autocorrelation_adjusted': False,
        'inference_warning': 'Constant annual values; OLS inference is undefined.' if constant else (
            'Exact linear fit; zero residual uncertainty does not describe measurement or model uncertainty.'
            if result.stderr == 0 else None),
        'fitted': pd.DataFrame({'year': x.astype(int), 'value': result.intercept + result.slope * x}),
    }
