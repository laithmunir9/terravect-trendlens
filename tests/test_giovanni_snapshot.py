"""Real browser exports, timezone regression, independent arithmetic and offline UI."""
import calendar
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

import giovanni_snapshot as snapshot
from analysis import annualize_monthly, calculate_trend, INFERENCE_STATUS


def test_real_exports_month_mapping_coverage_and_independent_weighting():
    data = snapshot.load_giovanni_snapshot()
    assert hashlib.sha256(data.original).hexdigest() == data.provenance['file_sha256']
    assert data.provenance['source_units'] == 'K'
    assert data.provenance['requested_bbox_west_south_east_north'] == [54.25, 24.25, 54.5, 24.75]
    assert len(data.monthly) == 300 and data.monthly.value.notna().sum() == 299
    assert pd.isna(data.monthly.iloc[0].value)  # January 2001 never filled.
    # Browser timestamp Jan 31 20:00 UTC is Feb 1 midnight in acquisition timezone.
    first = data.monthly.iloc[1]
    assert first.date == pd.Timestamp('2001-02-01')
    assert first.value == pytest.approx(292.9977 - 273.15)
    assert data.monthly.iloc[-1].date == pd.Timestamp('2025-12-01')
    raw = pd.read_csv(snapshot.SNAPSHOT_DIR / 'giovanni_abu_dhabi_2001_2025.csv')
    raw_month = pd.to_datetime(raw.x, utc=True).dt.tz_convert('Asia/Dubai')
    annual = annualize_monthly(data.monthly)
    assert annual.year.tolist() == list(range(2002, 2026))
    for row in annual.itertuples():
        entries = raw.loc[raw_month.dt.year == row.year, 'y'].to_list()
        days = [calendar.monthrange(row.year, m)[1] for m in range(1, 13)]
        expected = sum((kelvin - 273.15) * day for kelvin, day in zip(entries, days, strict=True)) / sum(days)
        assert row.value == pytest.approx(expected, abs=1e-10)
    assert calculate_trend(annual)['inference_status'] == INFERENCE_STATUS


def test_independent_2020_export_matches_all_eleven_months():
    data = snapshot.load_giovanni_snapshot()
    assert data.provenance['validation']['overlap_months'] == 11
    assert data.provenance['validation']['overlap_values_equal']
    raw = pd.read_csv(snapshot.SNAPSHOT_DIR / 'giovanni_abu_dhabi_2020.csv')
    assert len(raw) == 11
    feb = data.monthly[data.monthly.date == '2020-02-01'].value.iloc[0]
    assert feb == pytest.approx(293.80566 - 273.15)


def test_changed_bytes_are_rejected(tmp_path, monkeypatch):
    manifest = json.loads((snapshot.SNAPSHOT_DIR / 'giovanni_manifest.json').read_text())
    (tmp_path / 'giovanni_manifest.json').write_text(json.dumps(manifest))
    (tmp_path / manifest['records']['long']['file']).write_bytes(b'x,y\ncorrupt,1')
    monkeypatch.setattr(snapshot, 'SNAPSHOT_DIR', tmp_path)
    with pytest.raises(ValueError, match='checksum'):
        snapshot.load_giovanni_snapshot()


def test_timezone_rule_is_not_silently_applied_to_other_exports(tmp_path, monkeypatch):
    # Deliberately synthetic data with an updated hash: catches shape, not integrity.
    body = b'x,y\n2020-02-01T00:00:00.000Z,293.8\n'
    (tmp_path / 'synthetic.csv').write_bytes(body)
    monkeypatch.setattr(snapshot, 'SNAPSHOT_DIR', tmp_path)
    with pytest.raises(ValueError, match='timezone'):
        snapshot._read_export({'file': 'synthetic.csv', 'sha256': hashlib.sha256(body).hexdigest(), 'rows': 1})


def test_changed_overlap_is_rejected(tmp_path, monkeypatch):
    import shutil
    for name in ('giovanni_manifest.json', 'giovanni_abu_dhabi_2001_2025.csv', 'giovanni_abu_dhabi_2020.csv'):
        shutil.copyfile(snapshot.SNAPSHOT_DIR / name, tmp_path / name)
    manifest = json.loads((tmp_path / 'giovanni_manifest.json').read_text())
    p = tmp_path / manifest['records']['check']['file']
    p.write_bytes(p.read_bytes().replace(b'293.80566', b'294.80566'))
    manifest['records']['check']['sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
    (tmp_path / 'giovanni_manifest.json').write_text(json.dumps(manifest))
    monkeypatch.setattr(snapshot, 'SNAPSHOT_DIR', tmp_path)
    with pytest.raises(ValueError, match='disagree'):
        snapshot.load_giovanni_snapshot()


def test_other_time_window_rejected():
    with pytest.raises(ValueError, match='fixed'):
        snapshot.load_giovanni_snapshot(2020, 2020)
