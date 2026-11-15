"""Offline UI regression tests; all data in this module are synthetic."""
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests
import streamlit as st
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / 'app.py'


@pytest.fixture(autouse=True)
def clear_cache():
    st.cache_data.clear()
    yield
    st.cache_data.clear()


def fake_get(url, params, timeout):
    # Different missing years for each point exercise real UI alignment.
    first = params['latitude'] < 30
    missing = {params['start'], 2010} if first else {params['end'], 2012}
    series = {f'{year}{month:02d}': 10 + (year - 2000) * .1 + month / 100
              for year in range(params['start'], params['end'] + 1)
              for month in range(1, 13) if not (year in missing and month == 2)}
    payload = {'properties': {'parameter': {'T2M': series}},
               'header': {'fill_value': -999, 'sources': ['SYNTHETIC TEST ONLY']},
               'parameters': {'T2M': {'units': 'C'}}}
    response = requests.Response()
    response.status_code = 200
    response._content = json.dumps(payload).encode()
    response.url = 'https://example.invalid/synthetic-test'
    return response


def test_app_comparison_intersects_years_and_reports_coverage(monkeypatch):
    monkeypatch.setattr(requests, 'get', fake_get)
    at = AppTest.from_file(str(APP)).run()
    assert not at.exception and not at.error
    assert len(at.get('plotly_chart')) == 1
    at.checkbox[0].check().run()
    assert not at.exception and not at.error
    assert len(at.get('plotly_chart')) == 3  # Shared comparison plus two location detail charts.
    provenance = [json.loads(node.value) for node in at.json]
    assert len(provenance) == 2
    used = [node.value for node in at.markdown if node.value.startswith('Years used:')]
    assert len(used) == 2 and used[0] == used[1]
    assert '2010' not in used[0] and '2012' not in used[0]
    assert any('same' in node.value and 'complete calendar years' in node.value for node in at.info)
    assert any('not autocorrelation-adjusted' in node.value for node in at.caption)


def test_app_short_range_still_renders_annual_chart(monkeypatch):
    monkeypatch.setattr(requests, 'get', fake_get)
    at = AppTest.from_file(str(APP)).run()
    at.slider[0].set_range(2017, 2020).run()
    assert not at.exception and not at.error
    assert len(at.get('plotly_chart')) == 1
    assert not at.metric
    assert any('10 complete' in node.value for node in at.warning)


def test_app_network_failure_is_actionable(monkeypatch):
    def fail(*args, **kwargs):
        raise requests.Timeout()
    monkeypatch.setattr(requests, 'get', fail)
    at = AppTest.from_file(str(APP)).run()
    assert not at.exception
    assert 'timed out' in at.error[0].value
    assert at.button[0].label == 'Retry NASA POWER'


def test_app_upload_empty_state_does_not_claim_dataset(monkeypatch):
    monkeypatch.setattr(requests, 'get', fake_get)
    at = AppTest.from_file(str(APP)).run()
    at.radio[0].set_value('NASA Giovanni CSV upload').run()
    assert not at.exception and not at.error
    assert not at.metric
    assert any('No Giovanni dataset is bundled or claimed as used' in node.value for node in at.info)


def test_app_synthetic_upload_workflow(monkeypatch):
    monkeypatch.setattr(requests, 'get', fake_get)
    last = datetime.now(timezone.utc).year - 1
    content = 'Title: SYNTHETIC SOFTWARE TEST ONLY\nUnits: K\nTime,Temperature (K)\n'
    content += '\n'.join(f'{y}{m:02d},{280 + .1*(y-2000) + m/100}' for y in range(2001, last + 1) for m in range(1, 13))
    upload = io.BytesIO(content.encode())
    upload.name = 'synthetic-software-test.csv'
    monkeypatch.setattr(st, 'file_uploader', lambda *a, **k: upload)
    at = AppTest.from_file(str(APP)).run()
    at.radio[0].set_value('NASA Giovanni CSV upload').run()
    assert not at.exception and not at.error
    for node in at.text_input:
        if node.label == 'Dataset product and version':
            node.set_value('SYNTHETIC TEST')
        if node.label == 'Region or coordinates':
            node.set_value('SYNTHETIC REGION')
    [node for node in at.checkbox if node.label.startswith('I verified')][0].check()
    at.run()
    assert not at.exception and not at.error
    assert len(at.get('plotly_chart')) == 1
    provenance = json.loads(at.json[0].value)
    assert provenance['source_units'] == 'K'
    assert provenance['transformation'] == 'Kelvin minus 273.15'
    assert any('not been independently authenticated' in node.value for node in at.warning)


def test_giovanni_requires_explicit_retrieval_and_handles_missing_login(monkeypatch):
    import giovanni
    monkeypatch.setattr(requests, 'get', fake_get)
    calls = []
    def blocked(*args):
        calls.append(args)
        raise giovanni.EarthdataLoginRequired('Earthdata Login is required. Sign in in your own terminal.')
    monkeypatch.setattr(giovanni, 'load_giovanni', blocked)
    at = AppTest.from_file(str(APP)).run()
    at.radio[0].set_value('NASA Giovanni live (point)').run()
    assert not at.exception and not at.error
    assert not calls and not at.get('plotly_chart')
    [b for b in at.button if b.label == 'Retrieve Giovanni point series'][0].click().run()
    assert len(calls) == 1 and not at.exception
    assert any('Earthdata Login' in w.value for w in at.warning)
    assert not at.get('plotly_chart')
    at.radio[0].set_value('NASA POWER live').run()
    assert not at.exception and not at.error
    assert len(at.get('plotly_chart')) == 1


def test_giovanni_success_retains_session_data_and_invalidates_selection(monkeypatch):
    import giovanni
    from data_sources import MonthlyDataset
    import pandas as pd
    monkeypatch.setattr(requests, 'get', fake_get)
    calls = []
    def synthetic(*args):
        calls.append(args)
        dates = pd.date_range(f'{args[2]}-01-01', f'{args[3]}-12-01', freq='MS')
        return MonthlyDataset(pd.DataFrame({'date': dates, 'value': range(len(dates))}),
                              {'source': 'NASA Giovanni in the Cloud', 'fixture': 'SYNTHETIC TEST ONLY'},
                              original=b'This is a synthetic fixture, not NASA data.')
    monkeypatch.setattr(giovanni, 'load_giovanni', synthetic)
    at = AppTest.from_file(str(APP)).run()
    at.radio[0].set_value('NASA Giovanni live (point)').run()
    [b for b in at.button if b.label == 'Retrieve Giovanni point series'][0].click().run()
    assert not at.exception and not at.error
    assert len(at.get('plotly_chart')) == 1 and len(calls) == 1
    at.run()
    assert len(calls) == 1  # A rerun/download must not cause another API request.
    at.slider[0].set_range(2010, 2020).run()
    assert not at.get('plotly_chart')  # Never show stale data for different settings.
    assert len(calls) == 1


def test_giovanni_failure_clears_previous_result(monkeypatch):
    import giovanni
    from data_sources import MonthlyDataset
    import pandas as pd
    monkeypatch.setattr(requests, 'get', fake_get)
    calls = []
    def retrieve(*args):
        calls.append(args)
        if len(calls) > 1:
            raise ValueError('NASA Giovanni quota/credit limit reached (HTTP 403).')
        return MonthlyDataset(pd.DataFrame({'date': pd.date_range('2020-01-01', periods=12, freq='MS'), 'value': range(12)}),
                              {'source': 'NASA Giovanni in the Cloud', 'fixture': 'SYNTHETIC TEST ONLY'})
    monkeypatch.setattr(giovanni, 'load_giovanni', retrieve)
    at = AppTest.from_file(str(APP)).run()
    at.radio[0].set_value('NASA Giovanni live (point)').run()
    [b for b in at.button if b.label == 'Retrieve Giovanni point series'][0].click().run()
    assert len(at.get('plotly_chart')) == 1
    [b for b in at.button if b.label == 'Retrieve Giovanni point series'][0].click().run()
    assert not at.exception
    assert 'quota' in at.error[0].value
    assert not at.get('plotly_chart')


def test_saved_examples_work_offline_and_set_reproducible_selection(monkeypatch):
    def offline(*args, **kwargs):
        raise requests.ConnectionError()
    monkeypatch.setattr(requests, 'get', offline)
    at = AppTest.from_file(str(APP)).run()
    assert at.error  # A failed live request is never silently replaced.
    at.button(key='demo_compare').click().run()
    assert not at.exception and not at.error
    assert at.radio(key='source_mode').value == 'NASA POWER saved demo'
    assert at.slider(key='year_range').value == (2001, 2025)
    assert at.slider(key='year_range').disabled
    assert at.checkbox(key='compare').value
    assert len(at.get('plotly_chart')) == 3
    assert all('not a live retrieval' in json.loads(node.value)['access_mode'] for node in at.json)
    assert any('same 25 complete calendar years' in node.value for node in at.info)
    at.button(key='demo_single').click().run()
    assert not at.exception and not at.error
    assert at.radio(key='source_mode').value == 'NASA Giovanni saved demo'
    assert len(at.get('plotly_chart')) == 1
    assert any(m.label == 'Complete years analyzed' and m.value == '24' for m in at.metric)
    at.radio(key='source_mode').set_value('NASA POWER saved demo').run()
    [b for b in at.button if b.label == 'Use live NASA data'][0].click().run()
    assert at.error and not at.exception  # Going live requests NASA, not the snapshot.
    assert not at.slider(key='year_range').disabled


def test_custom_coordinates_are_sent_to_source(monkeypatch):
    calls = []
    def capture(url, params, timeout):
        calls.append(params.copy())
        return fake_get(url, params, timeout)
    monkeypatch.setattr(requests, 'get', capture)
    at = AppTest.from_file(str(APP)).run()
    at.selectbox(key='first_location').select('Custom coordinates').run()
    at.number_input(key='first_location_lat').set_value(-33.86)
    at.number_input(key='first_location_lon').set_value(151.21)
    at.run()
    assert not at.exception and not at.error
    assert calls[-1]['latitude'] == -33.86 and calls[-1]['longitude'] == 151.21
    at.button(key='demo_compare').click().run()
    assert not at.exception and not at.error
    assert at.selectbox(key='first_location').value == 'Abu Dhabi, UAE'


def test_demo_source_normalizes_previous_location_and_time(monkeypatch):
    monkeypatch.setattr(requests, 'get', fake_get)
    at = AppTest.from_file(str(APP)).run()
    at.selectbox(key='first_location').select('Phoenix, USA').run()
    at.slider(key='year_range').set_range(2010, 2020).run()
    at.radio(key='source_mode').set_value('NASA POWER saved demo').run()
    assert not at.exception and not at.error
    assert at.selectbox(key='first_location').value == 'Abu Dhabi, UAE'
    assert at.slider(key='year_range').value == (2001, 2025)
