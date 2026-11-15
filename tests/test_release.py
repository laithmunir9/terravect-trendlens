"""Public-mode and scientific-claim release gates. Credential values are synthetic."""
import json
from pathlib import Path

import pytest
import requests
import streamlit as st
from streamlit.testing.v1 import AppTest

from analysis import INFERENCE_STATUS, annualize_monthly, calculate_trend
from demos import DEMO_LOCATIONS, load_demo
from giovanni_snapshot import GIOVANNI_DEMO_SOURCE, load_giovanni_snapshot
from giovanni import EarthdataLoginRequired, earthdata_token, load_giovanni
from insights import explain_trend, investigation_brief
from release import AI_DISCLOSURE
from scripts.check_release import scan

APP = Path(__file__).resolve().parents[1] / 'app.py'


@pytest.fixture(autouse=True)
def clear_cache():
    st.cache_data.clear()
    yield
    st.cache_data.clear()


def test_public_mode_loads_real_demos_without_network_or_credentials(monkeypatch):
    monkeypatch.setenv('TRENDLENS_PUBLIC', '1')
    for key in ('EARTHDATA_TOKEN', 'EARTHDATA_USERNAME', 'EARTHDATA_PASSWORD', 'NETRC'):
        monkeypatch.delenv(key, raising=False)
    def forbidden(*args, **kwargs):
        raise AssertionError('Public demo must work without any external request')
    monkeypatch.setattr(requests, 'get', forbidden)
    at = AppTest.from_file(str(APP)).run()
    assert not at.exception and not at.error
    assert at.radio(key='source_mode').value == GIOVANNI_DEMO_SOURCE
    assert 'NASA Giovanni live (point)' not in at.radio(key='source_mode').options
    assert len(at.get('plotly_chart')) == 1
    assert any(m.label == 'Complete years analyzed' and m.value == '24' for m in at.metric)
    assert any('Incomplete years excluded: 2001' in w.value for w in at.warning)
    assert json.loads(at.json[0].value)['source'] == 'NASA Giovanni browser export'
    at.button(key='demo_compare').click().run()
    assert not at.exception and not at.error
    assert len(at.get('plotly_chart')) == 3
    assert any(INFERENCE_STATUS in c.value for c in at.caption)
    assert any(AI_DISCLOSURE in c.value for c in at.caption)


def test_public_mode_blocks_even_present_server_credentials(monkeypatch):
    monkeypatch.setenv('TRENDLENS_PUBLIC', '1')
    monkeypatch.setenv('EARTHDATA_TOKEN', 'SYNTHETIC-DO-NOT-USE')
    def forbidden(*args, **kwargs):
        raise AssertionError('Must block before consulting netrc or contacting NASA')
    monkeypatch.setattr(Path, 'is_file', forbidden)
    monkeypatch.setattr(requests, 'get', forbidden)
    with pytest.raises(EarthdataLoginRequired, match='disabled in public mode'):
        earthdata_token()
    with pytest.raises(EarthdataLoginRequired, match='disabled in public mode'):
        load_giovanni(24.4539, 54.3773, 2001, 2025)


def test_community_cloud_entrypoint_forces_public_mode(monkeypatch):
    monkeypatch.setenv('TRENDLENS_PUBLIC', '0')
    for key in ('EARTHDATA_TOKEN', 'EARTHDATA_USERNAME', 'EARTHDATA_PASSWORD', 'NETRC'):
        monkeypatch.delenv(key, raising=False)
    def forbidden(*args, **kwargs):
        raise AssertionError('Cloud startup must use saved public data without HTTP')
    monkeypatch.setattr(requests.sessions.Session, 'request', forbidden)
    at = AppTest.from_file(str(APP.parent / 'cloud' / 'streamlit_app.py')).run()
    assert not at.exception and not at.error
    assert at.radio(key='source_mode').value == GIOVANNI_DEMO_SOURCE
    assert 'NASA Giovanni live (point)' not in at.radio(key='source_mode').options
    assert any(m.label == 'Complete years analyzed' and m.value == '24' for m in at.metric)


def test_public_live_failure_does_not_silently_substitute_saved_data(monkeypatch):
    monkeypatch.setenv('TRENDLENS_PUBLIC', '1')
    def offline(*args, **kwargs):
        raise requests.ConnectionError()
    monkeypatch.setattr(requests, 'get', offline)
    at = AppTest.from_file(str(APP)).run()
    at.radio(key='source_mode').set_value('NASA POWER live').run()
    assert at.error and not at.exception
    assert not at.get('plotly_chart')
    [b for b in at.button if b.label == 'Open the saved NASA example'][0].click().run()
    assert not at.error and not at.exception
    assert at.radio(key='source_mode').value == GIOVANNI_DEMO_SOURCE


@pytest.mark.parametrize('name', DEMO_LOCATIONS)
def test_actual_demo_findings_never_establish_significance(name):
    dataset = load_demo(name, 2001, 2025)
    info = calculate_trend(annualize_monthly(dataset.monthly))
    assert info['autocorrelation_adjusted'] is False
    assert info['inference_status'] == INFERENCE_STATUS
    assert INFERENCE_STATUS in explain_trend(info)['evidence']
    assert INFERENCE_STATUS in investigation_brief(name, info, dataset.provenance)


def test_export_contains_disclosure_and_exact_original_snapshot(monkeypatch):
    monkeypatch.setenv('TRENDLENS_PUBLIC', '1')
    exports = {}
    def capture(label, data, **kwargs):
        exports[label] = data
        return False
    monkeypatch.setattr(st, 'download_button', capture)
    at = AppTest.from_file(str(APP)).run()
    assert not at.exception
    record = json.loads(exports['Download provenance and methods'])
    assert record['software']['ai_assistance'] == AI_DISCLOSURE
    assert record['software']['code_license'] == 'MIT'
    assert record['analysis']['statistics']['inference_status'] == INFERENCE_STATUS
    assert exports['Download original source response'] == load_giovanni_snapshot().original
    assert record['analysis']['years_used'] == list(range(2002, 2026))
    assert record['source_units'] == 'K'
    assert 'Native service metadata was not retained' in ' '.join(w.value for w in at.warning)
    assert 'Asia/Dubai' in exports['Download investigation brief']


def test_release_scan_reports_categories_without_secret_values():
    fake_key = 'sk-' + 'proj-' + 'x' * 48
    assert scan(fake_key) == ['openai-key']
    assert fake_key not in json.dumps(scan(fake_key))


def test_release_scan_accepts_source_hashes_and_public_request_urls():
    dataset = load_demo(DEMO_LOCATIONS[0], 2001, 2025)
    assert scan(json.dumps(dataset.provenance)) == []
