"""Load the reviewed Giovanni browser exports; never infer dates for arbitrary CSVs."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd

from data_sources import MonthlyDataset

SNAPSHOT_DIR = Path(__file__).resolve().parent / 'data' / 'demos'
GIOVANNI_DEMO_SOURCE = 'NASA Giovanni saved demo'


def _read_export(record: dict) -> pd.DataFrame:
    original = (SNAPSHOT_DIR / record['file']).read_bytes()
    if hashlib.sha256(original).hexdigest() != record['sha256']:
        raise ValueError('Saved Giovanni export checksum mismatch. Restore the reviewed original.')
    frame = pd.read_csv(io.BytesIO(original))
    if list(frame.columns) != ['x', 'y'] or len(frame) != record['rows']:
        raise ValueError('Saved Giovanni export columns or row count changed.')
    dates = pd.to_datetime(frame.x, utc=True, errors='raise')
    # These specific exports came from a browser in Asia/Dubai. NASA's frontend
    # parsed timezone-less service dates locally before serializing them to UTC.
    # See the source/format evidence and limits in giovanni_manifest.json.
    local = dates.dt.tz_convert('Asia/Dubai').dt.tz_localize(None)
    if not ((local.dt.day == 1) & (local == local.dt.normalize())).all():
        raise ValueError('Saved Giovanni timestamps no longer match the reviewed timezone conversion.')
    if local.duplicated().any() or not local.is_monotonic_increasing:
        raise ValueError('Saved Giovanni months must be ordered and unique.')
    values = pd.to_numeric(frame.y, errors='raise')
    if not np.isfinite(values).all() or not values.between(150, 350).all():
        raise ValueError('Saved Giovanni values are missing or outside the reviewed temperature range.')
    return pd.DataFrame({'date': local, 'value': values - 273.15})


def load_giovanni_snapshot(start: int = 2001, end: int = 2025) -> MonthlyDataset:
    if (start, end) != (2001, 2025):
        raise ValueError('Saved Giovanni investigation covers the fixed 2001–2025 request.')
    try:
        manifest = json.loads((SNAPSHOT_DIR / 'giovanni_manifest.json').read_text())
        long_record, check_record = manifest['records']['long'], manifest['records']['check']
        long, check = _read_export(long_record), _read_export(check_record)
        expected = pd.date_range('2001-02-01', '2025-12-01', freq='MS')
        if long.date.tolist() != expected.tolist():
            raise ValueError('Saved Giovanni coverage differs from the reviewed February 2001–December 2025 record.')
        overlap = long[long.date.dt.year == 2020].set_index('date').loc[check.date]
        if check.date.tolist() != pd.date_range('2020-02-01', '2020-12-01', freq='MS').tolist():
            raise ValueError('Saved Giovanni check export coverage changed.')
        if not np.array_equal(overlap.value.to_numpy(), check.value.to_numpy()):
            raise ValueError('Independent Giovanni exports disagree for overlapping months.')
        monthly = long.set_index('date').reindex(pd.date_range(
            '2001-01-01', '2025-12-01', freq='MS', name='date')).reset_index()
        provenance = dict(manifest,
            access_mode='Saved NASA browser export; not a live retrieval',
            snapshot_manifest='data/demos/giovanni_manifest.json',
            file_sha256=long_record['sha256'],
            missing_months=1,
            transformation='Restore browser calendar labels in Asia/Dubai; Kelvin minus 273.15; no values filled.',
            validation={'valid_months': len(long), 'overlap_months': len(check),
                        'overlap_values_equal': True, 'complete_years': list(range(2002, 2026))})
        return MonthlyDataset(monthly, provenance, [
            'Giovanni browser export: monthly labels restored using the acquisition timezone (Asia/Dubai). '
            'Native service metadata was not retained; see provenance for the evidence and limitations.'
        ], (SNAPSHOT_DIR / long_record['file']).read_bytes())
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError('Saved Giovanni evidence is unavailable or incomplete. Restore the snapshot and manifest.') from exc
