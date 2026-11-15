"""Plain-language interpretation of computed results; no inferred causality."""
from __future__ import annotations

from analysis import INFERENCE_STATUS
from release import AI_DISCLOSURE


def explain_trend(info: dict) -> dict[str, str]:
    slope = info['slope_per_decade']
    direction = 'increased' if slope > 0 else 'decreased' if slope < 0 else 'was flat'
    magnitude = (
        (f'Annual temperature {direction} at a fitted rate of {abs(slope):.3f} °C per decade.'
         if slope != 0 else 'The fitted annual temperature trend was flat.')
        + f" This uses {info['n_years']} complete years from {info['first_year']} to {info['last_year']}."
    )
    change = slope * (info['last_year'] - info['first_year']) / 10
    magnitude += (f' Across that interval, the fitted line changes by {change:+.2f} °C. '
                  'This is a model-based change, not the difference between two observed endpoints.')
    low, high = info['lower_95_per_decade'], info['upper_95_per_decade']
    if info['inference_warning']:
        evidence = info['inference_warning'] + ' Do not use this fit to claim statistical significance.'
    elif low is None or high is None or info['p_value'] is None:
        evidence = 'The slope uncertainty and statistical significance cannot be estimated for this series.'
    elif low <= 0 <= high:
        evidence = (f'The 95% OLS slope interval ({low:+.3f} to {high:+.3f} °C/decade) includes zero. '
                    'The data do not clearly distinguish a nonzero linear trend under OLS assumptions; '
                    'this does not prove that the environment is unchanged.')
    else:
        evidence = (f'The 95% OLS slope interval ({low:+.3f} to {high:+.3f} °C/decade) excludes zero. '
                    'This interval is conditional on independent-error OLS assumptions; '
                    'it does not establish a statistically significant environmental change.')
    evidence += ' ' + INFERENCE_STATUS
    return {
        'magnitude': magnitude,
        'evidence': evidence,
        'limits': 'Years can be correlated. The interval and p-value assume independent errors and do not '
                  'include dataset or model uncertainty. Results depend on the chosen period. '
                  'This analysis does not identify causes or predict future temperatures.',
    }


def investigation_brief(name: str, info: dict | None, provenance: dict) -> str:
    lines = [f'TrendLens investigation · {name}', '',
             f"Source: {provenance.get('source', 'User-supplied data')}",
             f"Selected years: {provenance.get('selected_years', 'See provenance JSON')}",
             f"Access: {provenance.get('access_mode', 'See source provenance')}",
             f"Retrieved: {provenance.get('retrieved_at_utc', provenance.get('retrieved_on', provenance.get('uploaded_at_utc', 'Not supplied')))}",
             f"Source SHA-256: {provenance.get('response_sha256', provenance.get('file_sha256', 'See provenance JSON'))}",
             f"Request: {provenance.get('request_url', 'See provenance JSON')}", '']
    if provenance.get('spatial_processing'):
        lines.append('Source spatial processing: ' + provenance['spatial_processing'])
    if provenance.get('timestamp_processing'):
        lines.append('Source timestamp processing: ' + provenance['timestamp_processing']['method'])
        lines.append('Provenance limit: ' + provenance['timestamp_processing']['certainty_limit'])
    if info:
        lines.extend(explain_trend(info).values())
        lines += ['', 'Years used: ' + ', '.join(map(str, info['years_used'])),
                  f"Exploratory two-sided OLS p-value (not autocorrelation-adjusted): {info['p_value']}"]
    else:
        lines.append('No trend estimate is available. At least 10 complete annual values are required.')
    lines += ['', 'Method: 12 valid monthly means per year, weighted by Gregorian calendar days. '
              'No gap filling. Comparison fits use the same complete years. '
              'No statistical test of the difference between slopes is performed.',
              'Spatial scope: model grid-cell estimates for point requests, not city-wide measurements. '
              'For uploads, spatial scope is user-supplied; inspect the provenance.',
              'Retain this brief together with the original source, data CSVs, and provenance JSON.',
              'Development disclosure: ' + AI_DISCLOSURE,
              'Original application code: MIT. NASA data and dependencies retain their own terms.']
    return '\n\n'.join(lines)
