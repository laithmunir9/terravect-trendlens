"""Verify bundled genuine NASA responses, independently of network availability."""
import calendar
import hashlib
import json

import pytest

import demos
from analysis import annualize_monthly


@pytest.mark.parametrize('name', demos.DEMO_LOCATIONS)
def test_saved_nasa_data_and_independent_weighting(name):
    dataset = demos.load_demo(name, 2001, 2025)
    assert dataset.provenance['source'] == 'NASA POWER'
    assert dataset.provenance['request_url'].startswith('https://power.larc.nasa.gov/')
    assert hashlib.sha256(dataset.original).hexdigest() == dataset.provenance['response_sha256']
    assert 'not a live retrieval' in dataset.provenance['access_mode']
    assert dataset.provenance['retrieved_at_utc']
    assert len(dataset.monthly) == 300 and not dataset.monthly.value.isna().any()
    raw = json.loads(dataset.original)['properties']['parameter']['T2M']
    assert dataset.provenance['source_units'] == 'C'
    annual = annualize_monthly(dataset.monthly)
    assert annual.year.tolist() == list(range(2001, 2026))
    for row in annual.itertuples():
        days = [calendar.monthrange(row.year, m)[1] for m in range(1, 13)]
        expected = sum(raw[f'{row.year}{m:02d}'] * days[m-1] for m in range(1, 13)) / sum(days)
        assert row.value == pytest.approx(expected, abs=1e-10)


def test_wrong_period_rejected():
    with pytest.raises(ValueError, match='exactly 2001'):
        demos.load_demo(demos.DEMO_LOCATIONS[0], 2010, 2025)


def test_corrupted_snapshot_rejected(tmp_path, monkeypatch):
    manifest = json.loads((demos.DEMO_DIR / 'manifest.json').read_text())
    (tmp_path / 'manifest.json').write_text(json.dumps(manifest))
    (tmp_path / 'abu_dhabi_source.json').write_bytes(b'corrupt')
    monkeypatch.setattr(demos, 'DEMO_DIR', tmp_path)
    with pytest.raises(ValueError, match='checksum mismatch'):
        demos.load_demo(demos.DEMO_LOCATIONS[0], 2001, 2025)


def test_missing_snapshot_is_actionable(tmp_path, monkeypatch):
    monkeypatch.setattr(demos, 'DEMO_DIR', tmp_path)
    with pytest.raises(ValueError, match='unavailable or incomplete'):
        demos.load_demo(demos.DEMO_LOCATIONS[0], 2001, 2025)
