"""Source parsing with explicit units, missing values, and retained provenance."""
from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests

from analysis import normalize_monthly

POWER_URL = 'https://power.larc.nasa.gov/api/temporal/monthly/point'


@dataclass
class MonthlyDataset:
    monthly: pd.DataFrame
    provenance: dict
    warnings: list[str] = field(default_factory=list)
    original: bytes = b''


@dataclass
class GiovanniTable:
    frame: pd.DataFrame
    metadata: str
    header_line: int
    original: bytes


def temperature_unit(text: str) -> str:
    unit = re.sub(r'[\s_°\-]', '', str(text).lower())
    if unit in {'c', 'degc', 'celsius', 'degreec', 'degreesc', 'degreecelsius', 'degreescelsius'}:
        return 'C'
    if unit in {'k', 'degk', 'kelvin', 'degreekelvin', 'degreeskelvin'}:
        return 'K'
    raise ValueError(f'Unsupported or unknown temperature units: {text!r}. Only absolute temperature in Celsius or Kelvin is supported.')


def _values_to_celsius(values, unit: str, fills: list[float]) -> pd.Series:
    numbers = pd.to_numeric(pd.Series(values), errors='coerce').astype(float)
    numbers = numbers.mask(~np.isfinite(numbers) | numbers.isin(fills))
    if temperature_unit(unit) == 'K':
        numbers = numbers - 273.15
    if (numbers.dropna() < -273.15).any():
        raise ValueError('Temperature below absolute zero. Check units and declare the source missing-value sentinel.')
    return numbers


def parse_power_payload(payload: dict, start: int, end: int) -> MonthlyDataset:
    if not 1981 <= start <= end <= 2200:
        raise ValueError('POWER years must be ordered and start in 1981 or later.')
    if not isinstance(payload, dict):
        raise ValueError('NASA POWER returned a non-object JSON response.')
    try:
        values = payload['properties']['parameter']['T2M']
        header = payload['header']
        variable = payload['parameters']['T2M']
        unit = temperature_unit(variable['units'])
        fill = float(header['fill_value'])
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError('NASA POWER response is missing T2M data, units, or fill-value metadata.') from exc
    if not isinstance(values, dict) or not values:
        raise ValueError('NASA POWER response contains no T2M series.')
    if not np.isfinite(fill):
        raise ValueError('NASA POWER fill-value metadata is invalid.')
    rows, summaries, invalid_keys, outside = [], 0, 0, 0
    for key, value in values.items():
        key = str(key)
        if not re.fullmatch(r'\d{6}', key):
            invalid_keys += 1
            continue
        year, month = int(key[:4]), int(key[4:])
        if month == 13:
            summaries += 1
            continue
        if not 1 <= month <= 12:
            invalid_keys += 1
            continue
        if not start <= year <= end:
            outside += 1
            continue
        rows.append({'date': pd.Timestamp(year, month, 1), 'value': value})
    if not rows:
        raise ValueError('NASA POWER response contains no monthly values in the requested range.')
    monthly = pd.DataFrame(rows)
    monthly['value'] = _values_to_celsius(monthly['value'], unit, [fill])
    monthly = normalize_monthly(monthly).set_index('date').reindex(
        pd.date_range(f'{start}-01-01', f'{end}-12-01', freq='MS', name='date')).reset_index()
    warnings = []
    missing = int(monthly['value'].isna().sum())
    if missing:
        warnings.append(f'{missing} requested months are absent, missing, or non-numeric; affected years are excluded.')
    if invalid_keys:
        warnings.append(f'Ignored {invalid_keys} invalid time keys in the POWER response.')
    if outside:
        warnings.append(f'Ignored {outside} months outside the selected years.')
    messages = payload.get('messages', [])
    if messages:
        warnings.append(f'NASA POWER messages: {messages}')
    return MonthlyDataset(monthly, {
        'source': 'NASA POWER', 'parameter': 'T2M', 'source_units': unit,
        'analysis_units': 'C', 'selected_years': [start, end], 'header': header,
        'parameter_metadata': variable, 'geometry': payload.get('geometry'),
        'api_messages': messages, 'ignored_annual_summaries': summaries,
        'missing_months': missing,
    }, warnings)


def load_power(lat: float, lon: float, start: int, end: int) -> MonthlyDataset:
    if not np.isfinite([lat, lon]).all() or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError('Latitude or longitude is outside its valid range.')
    if not 1981 <= start <= end <= 2200:
        raise ValueError('POWER years must be ordered and start in 1981 or later.')
    params = dict(parameters='T2M', community='RE', latitude=lat, longitude=lon,
                  start=start, end=end, format='JSON')
    try:
        response = requests.get(POWER_URL, params=params, timeout=(10, 60))
        response.raise_for_status()
    except requests.Timeout as exc:
        raise ValueError('NASA POWER timed out. Retry later or choose a shorter period.') from exc
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else 'unknown'
        raise ValueError(f'NASA POWER returned HTTP {status}. Check the selected years or retry later.') from exc
    except requests.RequestException as exc:
        raise ValueError('Cannot connect to NASA POWER. Check your connection and retry.') from exc
    try:
        payload = response.json()
    except ValueError as exc:
        raise ValueError('NASA POWER returned invalid JSON instead of a data response. Retry later.') from exc
    dataset = parse_power_payload(payload, start, end)
    dataset.original = response.content
    dataset.provenance.update({
        'request_url': response.url, 'request_parameters': params,
        'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
        'response_sha256': hashlib.sha256(response.content).hexdigest(),
    })
    return dataset


def _header_name(value: str) -> str:
    return re.sub(r'[^a-z0-9]', '', value.lower())


def _is_date_header(value: str) -> bool:
    return _header_name(value) in {'time', 'date', 'datetime', 'timeutc', 'dateutc', 'yearmonth', 'yyyymm', 'yyyyMMdd'.lower()}


def read_giovanni_csv(content: bytes, header_line: int | None = None) -> GiovanniTable:
    """Read comma-separated exports with BOM, comments, and metadata preambles.

    An explicit 1-based header line handles unfamiliar column names. Metadata
    and the original bytes are retained; file origin is not authenticated.
    """
    if not content or len(content) > 10_000_000:
        raise ValueError('Upload a non-empty CSV no larger than 10 MB.')
    try:
        text = content.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ValueError('CSV must use UTF-8 encoding. Re-export or save it as UTF-8.') from exc
    lines = text.splitlines()
    selected = None
    if header_line is not None:
        if not 1 <= header_line <= len(lines):
            raise ValueError('Header line is outside the CSV file.')
        selected = header_line - 1
    else:
        for i, line in enumerate(lines):
            try:
                cells = next(csv.reader([line.lstrip().lstrip('#').strip()]))
            except csv.Error:
                continue
            names = [_header_name(c) for c in cells]
            if len(cells) >= 2 and (any(_is_date_header(c) for c in cells) or {'year', 'month'} <= set(names)):
                selected = i
                break
    if selected is None:
        raise ValueError('Could not locate a time-series header. Set its line number in Import options.')
    table_lines = [lines[selected].lstrip().lstrip('#').strip()]
    metadata_lines = lines[:selected]
    for line in lines[selected + 1:]:
        if line.lstrip().startswith('#'):
            metadata_lines.append(line)
        elif line.strip():
            table_lines.append(line)
    try:
        records = list(csv.reader(io.StringIO('\n'.join(table_lines)), strict=True))
    except csv.Error as exc:
        raise ValueError(f'Malformed CSV quoting: {exc}') from exc
    columns = [c.strip() for c in records[0]]
    if len(columns) < 2 or any(not c for c in columns) or len(set(columns)) != len(columns):
        raise ValueError('CSV needs at least two distinct, non-empty column names.')
    if any(len(row) != len(columns) for row in records[1:]):
        raise ValueError('CSV data rows have inconsistent column counts. Check delimiters or trailing metadata.')
    frame = pd.DataFrame(records[1:], columns=columns)
    if frame.empty:
        raise ValueError('CSV contains a header but no data rows.')
    return GiovanniTable(frame, '\n'.join(metadata_lines), selected + 1, content)


def infer_giovanni_unit(table: GiovanniTable, value_column: str) -> str | None:
    """Prefer selected-column units; reject unsupported or contradictory labels."""
    labels = re.findall(r'\(([^()]*)\)|\[([^\[\]]*)\]', value_column)
    units = [a or b for a, b in labels]
    # Only use global units for a single measurement column: multivariate exports
    # may contain variables with different units.
    measurement_columns = [c for c in table.frame if not _is_date_header(c) and _header_name(c) not in {'year', 'month'}]
    if len(measurement_columns) == 1:
        units += re.findall(r'(?im)^\s*#?\s*units?\s*[:,=]\s*([^\r\n]+)', table.metadata)
    if not units:
        return None
    canonical = {temperature_unit(u.strip().strip('"')) for u in units}
    if len(canonical) != 1:
        raise ValueError('Conflicting units in the CSV header and metadata. Resolve them before importing.')
    return canonical.pop()


def parse_month(value: str) -> pd.Timestamp:
    """Unambiguous year-first dates only; never interpret numeric Unix timestamps."""
    text = str(value).strip()
    if re.fullmatch(r'\d{6}', text):
        return pd.to_datetime(text, format='%Y%m', errors='coerce')
    if re.fullmatch(r'\d{8}', text):
        return pd.to_datetime(text, format='%Y%m%d', errors='coerce')
    if not re.fullmatch(r'\d{4}[-/]\d{1,2}(?:[-/]\d{1,2})?(?:[T ].*)?', text):
        return pd.NaT
    parsed = pd.to_datetime(text, errors='coerce')
    # Monthly timestamps are calendar labels. Converting midnight +03:00 to
    # UTC would incorrectly assign a first-of-month value to the previous month.
    return parsed.tz_localize(None) if not pd.isna(parsed) else pd.NaT


def import_giovanni(table: GiovanniTable, date_column: str, value_column: str,
                    unit: str, start: int, end: int, *, month_column: str | None = None,
                    missing_values: str = '', metadata: dict | None = None,
                    filename: str = '') -> MonthlyDataset:
    if start > end:
        raise ValueError('Start year must not exceed end year.')
    columns = [date_column, value_column] + ([month_column] if month_column else [])
    if len(set(columns)) != len(columns) or any(c not in table.frame for c in columns):
        raise ValueError('Choose distinct existing time and measurement columns.')
    unit = temperature_unit(unit)
    inferred = infer_giovanni_unit(table, value_column)
    if inferred is not None and inferred != unit:
        raise ValueError('Selected units conflict with the units declared by the CSV.')
    frame = table.frame
    if month_column:
        years = pd.to_numeric(frame[date_column], errors='coerce')
        months = pd.to_numeric(frame[month_column], errors='coerce')
        if (years.isna().any() or months.isna().any() or
                (years % 1 != 0).any() or (months % 1 != 0).any()):
            raise ValueError('Year and month columns must contain integers.')
        dates = pd.to_datetime(dict(year=years, month=months, day=1), errors='coerce', utc=True)
    else:
        dates = pd.to_datetime(frame[date_column].map(parse_month), errors='coerce', utc=True)
    if dates.isna().any():
        raise ValueError(f'{int(dates.isna().sum())} rows have invalid dates. Use YYYY-MM, YYYYMM, or ISO dates; annual summaries are not monthly data.')
    declared = re.findall(
        r'(?im)^\s*#?\s*(?:_?fill[ _]?value|missing[ _]?value)(?:s)?\s*[:,=]\s*([^\r\n]+)', table.metadata)
    fill_tokens = re.split(r'[,;\s]+', ' '.join(declared + [missing_values]).strip())
    try:
        fills = [float(token.strip('\"\'')) for token in fill_tokens if token]
    except ValueError as exc:
        raise ValueError('Missing-value declarations must be numeric, separated by commas or spaces.') from exc
    if not np.isfinite(fills).all():
        raise ValueError('Missing-value sentinels must be finite numbers; NaN is already treated as missing.')
    values = _values_to_celsius(frame[value_column], unit, fills)
    monthly = normalize_monthly(pd.DataFrame({'date': dates, 'value': values}))
    outside = int((~monthly['date'].dt.year.between(start, end)).sum())
    monthly = monthly[monthly['date'].dt.year.between(start, end)]
    if monthly.empty:
        raise ValueError('CSV contains no months in the selected year range.')
    monthly = monthly.set_index('date').reindex(pd.date_range(
        f'{start}-01-01', f'{end}-12-01', freq='MS', name='date')).reset_index()
    missing = int(monthly['value'].isna().sum())
    warnings = ['Uploaded CSV origin is user-supplied and has not been independently authenticated.']
    if missing:
        warnings.append(f'{missing} selected months are absent, missing, or non-numeric; affected years are excluded.')
    if outside:
        warnings.append(f'{outside} rows outside the selected year range were excluded.')
    return MonthlyDataset(monthly, {
        'source': 'User-uploaded CSV (Giovanni workflow)', 'filename': filename,
        'uploaded_at_utc': datetime.now(timezone.utc).isoformat(),
        'file_sha256': hashlib.sha256(table.original).hexdigest(),
        'original_metadata': table.metadata, 'header_line': table.header_line,
        'date_column': date_column, 'month_column': month_column, 'value_column': value_column,
        'source_units': unit, 'analysis_units': 'C', 'missing_value_sentinels': fills,
        'selected_years': [start, end], 'missing_months': missing,
        'user_supplied_metadata': metadata or {},
        'transformation': 'Kelvin minus 273.15' if unit == 'K' else 'Celsius unchanged',
    }, warnings, table.original)
