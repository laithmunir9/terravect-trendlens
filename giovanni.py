"""NASA's documented Giovanni in the Cloud point time-series API.

Only the catalogue-listed MERRA-2 monthly T2M product is supported. No spatial
averaging, hourly-to-monthly resampling, or substitution with POWER is performed.
"""
from __future__ import annotations

import csv
import hashlib
import io
import os
from pathlib import Path
import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests

from analysis import normalize_monthly
from data_sources import MonthlyDataset, _values_to_celsius, parse_month, temperature_unit
from release import public_mode

CATALOGUE_URL = 'https://api.giovanni.earthdata.nasa.gov/configured-variables'
TIMESERIES_URL = 'https://api.giovanni.earthdata.nasa.gov/timeseries'
VARIABLE = 'M2IMNXASM_5_12_4_T2M'
PRODUCT = 'M2IMNXASM'
VERSION = '5.12.4'
PRODUCT_URL = 'https://www.earthdata.nasa.gov/data/catalog/ges-disc-m2imnxasm-5.12.4'
DOI = '10.5067/5ESKGQTZG7FO'
TUTORIAL_URL = 'https://github.com/nasa/gesdisc-tutorials/blob/main/notebooks/How_to_Access_GiC_Time_Series_Service.ipynb'
LOGIN_INSTRUCTIONS = 'Run .venv/bin/python scripts/earthdata_login.py in your own terminal to sign in interactively, then use the app it starts. Do not paste credentials or tokens into chat.'


class EarthdataLoginRequired(ValueError):
    """No usable Earthdata authentication, with no sensitive details attached."""


def earthdata_token() -> str:
    """No interactive prompts in the Streamlit process; never cache the token."""
    if public_mode():
        raise EarthdataLoginRequired('Authenticated Giovanni access is disabled in public mode. Use public POWER or saved NASA data.')
    token = os.environ.get('EARTHDATA_TOKEN', '').strip()
    if token:
        if '\n' in token or '\r' in token:
            raise EarthdataLoginRequired('Invalid Earthdata token format. ' + LOGIN_INSTRUCTIONS)
        return token
    has_environment = bool(os.environ.get('EARTHDATA_USERNAME') and os.environ.get('EARTHDATA_PASSWORD'))
    netrc_path = Path(os.environ.get('NETRC', str(Path.home() / '.netrc')))
    if not has_environment and not netrc_path.is_file():
        raise EarthdataLoginRequired('Earthdata Login is required. ' + LOGIN_INSTRUCTIONS)
    try:
        import earthaccess
        auth = earthaccess.login(strategy='environment' if has_environment else 'netrc', persist=False)
        if not auth.authenticated:
            raise RuntimeError('Unauthenticated')
        return earthaccess.get_edl_token()['access_token']
    except Exception:
        # Never propagate authentication exception messages or request objects.
        raise EarthdataLoginRequired('Earthdata Login failed. ' + LOGIN_INSTRUCTIONS) from None


def _get(url: str, *, params=None, token: str | None = None):
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    try:
        response = requests.get(url, params=params, headers=headers,
                                timeout=(10, 90), allow_redirects=False)
    except requests.Timeout:
        raise ValueError('NASA Giovanni timed out. Retry or select a shorter year range.') from None
    except requests.RequestException:
        raise ValueError('Cannot connect to NASA Giovanni. Check the connection and retry.') from None
    status = response.status_code
    if status >= 400:
        # Inspect only to classify; never display an arbitrary server error body.
        quota = 'quota' in response.text.lower() or 'credit' in response.text.lower()
        if quota:
            raise ValueError(f'NASA Giovanni quota/credit limit reached (HTTP {status}). Contact GES DISC or retry after quota renewal; POWER remains available.')
        if status in (401, 403):
            raise EarthdataLoginRequired(f'NASA Giovanni denied access (HTTP {status}). ' + LOGIN_INSTRUCTIONS)
        if status == 429:
            raise ValueError('NASA Giovanni rate limit reached (HTTP 429). Retry later.')
        raise ValueError(f'NASA Giovanni request failed (HTTP {status}). No substitute data were used.')
    if status != 200:
        raise ValueError(f'Unexpected NASA Giovanni response (HTTP {status}); redirects are not followed with credentials.')
    return response


def configured_variables() -> tuple[list[str], dict]:
    response = _get(CATALOGUE_URL)
    try:
        variables = response.json()['configured_variables']
    except (ValueError, KeyError, TypeError):
        raise ValueError('NASA Giovanni returned an invalid configured-variables catalogue.') from None
    if not isinstance(variables, list) or not all(isinstance(v, str) for v in variables):
        raise ValueError('NASA Giovanni returned an invalid variable list.')
    return variables, {'url': CATALOGUE_URL, 'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
                       'sha256': hashlib.sha256(response.content).hexdigest(), 'variable_count': len(variables)}


def request_parameters(lat: float, lon: float, start: int, end: int) -> dict:
    if not np.isfinite([lat, lon]).all() or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError('Latitude or longitude is outside its valid range.')
    latest_complete = datetime.now(timezone.utc).year - 1
    if not isinstance(start, int) or not isinstance(end, int) or not 1980 <= start <= end <= latest_complete:
        raise ValueError('Select ordered, complete calendar years from 1980 onward.')
    return {'data': VARIABLE, 'location': f'[{lat},{lon}]',
            'time': f'{start}-01-01T00:00:00/{end}-12-31T23:59:59'}


def parse_point_csv(content: bytes, lat: float, lon: float, start: int, end: int) -> MonthlyDataset:
    """Parse metadata key/value rows followed by a two-column time series.

    NASA's tutorial uses a fixed 13-row preamble. We locate the table instead,
    retaining the original bytes, timestamps and every metadata field. Only
    monthly rows are accepted; multiple samples per month fail validation.
    """
    params = request_parameters(lat, lon, start, end)
    if not content or len(content) > 10_000_000:
        raise ValueError('Giovanni returned an empty or unexpectedly large point response.')
    try:
        rows = list(csv.reader(io.StringIO(content.decode('utf-8-sig')), strict=True))
    except (UnicodeDecodeError, csv.Error):
        raise ValueError('Giovanni returned malformed CSV instead of a point series.') from None
    metadata, measurements, timestamps = {}, [], []
    in_table = False
    for row in rows:
        if not row or not any(cell.strip() for cell in row):
            continue
        if len(row) != 2:
            raise ValueError('Giovanni point CSV must have exactly two columns.')
        key, value = (cell.strip() for cell in row)
        clean_key = key.lstrip('#').strip()
        if not in_table:
            if clean_key.lower() in {'time', 'timestamp', 'date', 'datetime'}:
                in_table = True
                continue
            if not pd.isna(parse_month(key)):
                in_table = True  # Accept headerless data after a metadata separator.
            else:
                if clean_key in metadata:
                    raise ValueError('Giovanni CSV contains duplicate metadata fields.')
                metadata[clean_key] = value
                continue
        date = parse_month(key)
        if pd.isna(date):
            raise ValueError('Giovanni CSV contains an invalid timestamp or trailing non-data row.')
        timestamps.append(key)
        measurements.append({'date': date, 'value': value})
    if not measurements:
        raise ValueError('Giovanni returned no point measurements. Check product availability and the selected period.')
    attrs = {k.lower(): v for k, v in metadata.items()}
    try:
        unit_label = attrs['unit'] if 'unit' in attrs else attrs['units']
        unit = temperature_unit(unit_label)
        grid_lat, grid_lon = float(attrs['lat']), float(attrs['lon'])
        parameter_name = attrs['param_name']
    except (KeyError, TypeError, ValueError):
        raise ValueError('Giovanni response lacks valid temperature units, parameter name or grid coordinates.') from None
    if not parameter_name or not np.isfinite([grid_lat, grid_lon]).all() or not (-90 <= grid_lat <= 90 and -180 <= grid_lon <= 180):
        raise ValueError('Giovanni returned invalid parameter or grid metadata.')
    # Guard against a wrong point response; native grid spacing is 0.5° x 0.625°.
    lon_distance = abs((grid_lon - lon + 180) % 360 - 180)
    if abs(grid_lat - lat) > 0.5 or lon_distance > 0.625:
        raise ValueError('Returned Giovanni grid coordinates do not match the requested point.')
    for field in ('data', 'variable', 'variable_id'):
        if field in attrs and attrs[field] not in {VARIABLE, 'T2M'}:
            raise ValueError('Giovanni returned a different variable than requested.')
    if 'param_short_name' in attrs and attrs['param_short_name'] not in {VARIABLE, 'T2M'}:
        raise ValueError('Giovanni returned a different parameter than requested.')
    # MERRA-2 documents 1e15 as the undefined value. A service declaration may
    # additionally supply a different numeric fill value; both are retained.
    fills = [1e15, float(np.float32(1e15))]
    for key in ('_fillvalue', 'fill_value', 'missing_value', 'missing value'):
        if key in attrs:
            try:
                declared = [float(v) for v in re.split(r'[,;\s]+', attrs[key].strip())]
                if not np.isfinite(declared).all():
                    raise ValueError
                fills.extend(declared)
            except ValueError:
                raise ValueError('Giovanni returned an invalid missing-value declaration.') from None
    raw = pd.DataFrame(measurements)
    raw['value'] = _values_to_celsius(raw['value'], unit, fills)
    monthly = normalize_monthly(raw)
    if not monthly['date'].dt.year.between(start, end).all():
        raise ValueError('Giovanni returned dates outside the requested years; no trend was calculated.')
    monthly = monthly.set_index('date').reindex(pd.date_range(
        f'{start}-01-01', f'{end}-12-01', freq='MS', name='date')).reset_index()
    missing = int(monthly['value'].isna().sum())
    if monthly['value'].notna().sum() == 0:
        raise ValueError('Giovanni returned no valid temperature measurements in the requested period.')
    warnings = ['Point grid-cell series, not an area average. This directly identifies the M2IMNXASM product; numerical agreement with POWER is not assumed.']
    if missing:
        warnings.append(f'{missing} requested months are absent or invalid; affected years are excluded without interpolation.')
    return MonthlyDataset(monthly, {
        'source': 'NASA Giovanni in the Cloud', 'service': 'point time series',
        'product': PRODUCT, 'version': VERSION, 'product_url': PRODUCT_URL, 'doi': DOI,
        'variable': VARIABLE, 'parameter': 'T2M', 'parameter_name': parameter_name,
        'source_units': unit_label, 'analysis_units': 'C',
        'requested_coordinates': {'latitude': lat, 'longitude': lon},
        'returned_grid_coordinates': {'latitude': grid_lat, 'longitude': grid_lon},
        'native_grid_spacing_degrees': {'latitude': 0.5, 'longitude': 0.625},
        'selected_years': [start, end], 'source_timestamps': timestamps,
        'response_metadata': metadata, 'request_parameters': params,
        'endpoint': TIMESERIES_URL, 'tutorial_url': TUTORIAL_URL,
        'missing_value_sentinels': sorted(set(fills)), 'missing_months': missing,
        'missing_value_policy': 'Mask response-declared sentinels and the documented MERRA-2 default 1e15 (including float32 representation) before conversion.',
        'temporal_processing': 'Native monthly means of instantaneous assimilated fields; no submonthly resampling. Calendar labels normalized to month start.',
        'spatial_processing': 'Giovanni point extraction; no spatial averaging or client interpolation.',
        'unit_conversion': 'Kelvin minus 273.15' if unit == 'K' else 'Celsius unchanged',
        'response_sha256': hashlib.sha256(content).hexdigest(),
    }, warnings, content)


def load_giovanni(lat: float, lon: float, start: int, end: int) -> MonthlyDataset:
    params = request_parameters(lat, lon, start, end)
    token = earthdata_token()
    variables, catalogue_provenance = configured_variables()
    if VARIABLE not in variables:
        raise ValueError(f'{VARIABLE} is not in the current Giovanni catalogue. No alternate product was silently substituted; use POWER or the documented GES DISC subsetting workflow.')
    response = _get(TIMESERIES_URL, params=params, token=token)
    dataset = parse_point_csv(response.content, lat, lon, start, end)
    # Construct the provenance URL from public parameters only, never from a
    # server redirect, request headers, cookies, or the authentication object.
    dataset.provenance.update({
        'request_url': requests.Request('GET', TIMESERIES_URL, params=params).prepare().url,
        'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
        'catalogue_check': catalogue_provenance,
    })
    return dataset
