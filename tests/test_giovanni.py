"""Synthetic API/CSV fixtures only; not downloaded NASA observations."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import requests

import giovanni
from analysis import annualize_monthly


def point_csv(*, unit='K', rows=None, extra=''):
    if rows is None:
        rows = '\n'.join(f'2020-{m:02d}-01T00:00:00Z,{273.15+m}' for m in range(1, 13))
    return (f'title,SYNTHETIC SOFTWARE TEST ONLY\nparam_name,2-meter air temperature\n'
            f'param_short_name,T2M\nunit,{unit}\nlat,24.5\nlon,54.375\n'
            f'{extra},\nTimestamp,T2M\n{rows}\n').encode()


def parse(content):
    return giovanni.parse_point_csv(content, 24.4539, 54.3773, 2020, 2020)


def response(body=b'', status=200):
    r = requests.Response()
    r.status_code = status
    r._content = body
    return r


def test_monthly_kelvin_conversion_and_provenance():
    raw = point_csv()
    data = parse(raw)
    assert data.monthly.value.tolist() == pytest.approx(range(1, 13))
    assert data.monthly.date.iloc[-1] == pd.Timestamp('2020-12-01')
    assert len(annualize_monthly(data.monthly)) == 1
    assert data.original == raw
    assert data.provenance['product'] == 'M2IMNXASM'
    assert data.provenance['version'] == '5.12.4'
    assert data.provenance['variable'] == giovanni.VARIABLE
    assert data.provenance['doi'] == '10.5067/5ESKGQTZG7FO'
    assert data.provenance['returned_grid_coordinates']['latitude'] == 24.5
    assert data.provenance['requested_coordinates']['latitude'] == 24.4539
    assert data.provenance['source_timestamps'][0] == '2020-01-01T00:00:00Z'
    assert data.provenance['service'] == 'point time series'
    assert len(data.provenance['response_sha256']) == 64


def test_preserve_missing_months_and_mask_before_kelvin_conversion():
    data = parse(point_csv(rows='2020-01-01,1e15\n2020-02-01,-9999\n2020-03-01,NaN\n2020-04-01,inf\n2020-05-01,280',
                           extra='_FillValue,-9999\n'))
    assert data.monthly.value.isna().sum() == 11
    assert data.monthly.value.iloc[4] == pytest.approx(6.85)
    assert annualize_monthly(data.monthly).empty
    assert data.provenance['missing_months'] == 11


def test_celsius_no_double_conversion():
    data = parse(point_csv(unit='degrees Celsius', rows='2020-01-01,20'))
    assert data.monthly.value.iloc[0] == 20
    assert data.provenance['unit_conversion'] == 'Celsius unchanged'


def test_float32_merra_fill_is_not_treated_as_temperature():
    data = parse(point_csv(rows=f'2020-01-01,{float(np.float32(1e15))}\n2020-02-01,280'))
    assert np.isnan(data.monthly.value.iloc[0])
    assert data.monthly.value.iloc[1] == pytest.approx(6.85)


def test_preamble_size_bom_comments_and_quoted_metadata():
    content = point_csv(extra='citation,"NASA, synthetic fixture"\nunused,anything\n')
    data = parse(b'\xef\xbb\xbf' + content.replace(b'unit,K', b'# unit,K'))
    assert data.provenance['response_metadata']['citation'] == 'NASA, synthetic fixture'


@pytest.mark.parametrize('content', [b'', b'<html>Login</html>', b'{"code": "401"}',
                                    b'title,empty\n', b'Timestamp,T2M\n2020-01-01,273.15'])
def test_empty_error_or_missing_metadata_rejected(content):
    with pytest.raises(ValueError):
        parse(content)


@pytest.mark.parametrize('old,new', [(b'unit,K', b'unit,mm/day'),
                                    (b'lat,24.5', b'lat,50'),
                                    (b'lon,54.375', b'lon,NaN'),
                                    (b'param_short_name,T2M', b'param_short_name,T10M')])
def test_conflicting_response_metadata_rejected(old, new):
    with pytest.raises(ValueError):
        parse(point_csv().replace(old, new))


@pytest.mark.parametrize('rows', ['2020-01-01,273\n2020-01-02,274',
                                 '2020-01-01,273\n2020-01-01,274',
                                 '2020-01-01,273\nbad,274',
                                 '2019-01-01,273', '2020-01-01,NaN',
                                 '2020-01-01,1e15', '2020-01-01,-9999'])
def test_frequency_date_and_all_missing_fail_closed(rows):
    with pytest.raises(ValueError):
        parse(point_csv(rows=rows))


def test_exact_documented_query_coordinate_order():
    params = giovanni.request_parameters(24.4539, 54.3773, 2001, 2025)
    assert params['location'] == '[24.4539,54.3773]'
    assert params['time'] == '2001-01-01T00:00:00/2025-12-31T23:59:59'
    assert params['data'] == giovanni.VARIABLE


@pytest.mark.parametrize('lat,lon,start,end', [(91, 0, 2020, 2020), (0, 181, 2020, 2020),
                                              (np.nan, 0, 2020, 2020), (0, 0, 1979, 2020),
                                              (0, 0, 2021, 2020), (0, 0, 2020, 3000)])
def test_invalid_requests(lat, lon, start, end):
    with pytest.raises(ValueError):
        giovanni.request_parameters(lat, lon, start, end)


def test_missing_auth_never_prompts(monkeypatch, tmp_path):
    for key in ('EARTHDATA_TOKEN', 'EARTHDATA_USERNAME', 'EARTHDATA_PASSWORD'):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv('NETRC', str(tmp_path / 'not-created'))
    with pytest.raises(giovanni.EarthdataLoginRequired, match='terminal'):
        giovanni.earthdata_token()


def test_token_environment_not_logged(monkeypatch, capsys):
    monkeypatch.setenv('EARTHDATA_TOKEN', 'SYNTHETIC-SECRET-FOR-TEST')
    assert giovanni.earthdata_token() == 'SYNTHETIC-SECRET-FOR-TEST'
    assert capsys.readouterr().out == ''


def test_auth_library_failure_message_does_not_leak(monkeypatch):
    import earthaccess
    monkeypatch.delenv('EARTHDATA_TOKEN', raising=False)
    monkeypatch.setenv('EARTHDATA_USERNAME', 'SYNTHETIC-USER')
    monkeypatch.setenv('EARTHDATA_PASSWORD', 'SYNTHETIC-SECRET')
    def fail(**kwargs):
        assert kwargs == {'strategy': 'environment', 'persist': False}
        raise RuntimeError('SYNTHETIC-SECRET')
    monkeypatch.setattr(earthaccess, 'login', fail)
    with pytest.raises(giovanni.EarthdataLoginRequired) as caught:
        giovanni.earthdata_token()
    assert 'SYNTHETIC-SECRET' not in str(caught.value)
    assert caught.value.__suppress_context__


@pytest.mark.parametrize('status,body,message', [(401, b'private', 'denied access'),
                                                (403, b'Bad or missing token', 'denied access'),
                                                (403, b'Quota exceeded', 'quota/credit'),
                                                (429, b'rate limited', 'rate limit'),
                                                (500, b'private error', 'HTTP 500'),
                                                (302, b'', 'redirects')])
def test_http_failures_are_safe(monkeypatch, status, body, message):
    monkeypatch.setattr(requests, 'get', lambda *a, **k: response(body, status))
    with pytest.raises(ValueError, match=message) as caught:
        giovanni._get(giovanni.TIMESERIES_URL, token='SYNTHETIC-SECRET')
    assert 'SYNTHETIC-SECRET' not in str(caught.value)
    assert 'private' not in str(caught.value)


@pytest.mark.parametrize('error,message', [(requests.Timeout('SYNTHETIC-SECRET'), 'timed out'),
                                         (requests.ConnectionError('SYNTHETIC-SECRET'), 'Cannot connect')])
def test_network_exceptions_sanitized(monkeypatch, error, message):
    def fail(*a, **k):
        raise error
    monkeypatch.setattr(requests, 'get', fail)
    with pytest.raises(ValueError, match=message) as caught:
        giovanni._get(giovanni.TIMESERIES_URL, token='SYNTHETIC-SECRET')
    assert 'SYNTHETIC-SECRET' not in str(caught.value)


def test_load_checks_catalogue_and_retains_only_public_provenance(monkeypatch):
    monkeypatch.setenv('EARTHDATA_TOKEN', 'SYNTHETIC-SECRET')
    calls = []
    def get(url, **kwargs):
        calls.append((url, kwargs))
        assert kwargs['allow_redirects'] is False
        assert kwargs['timeout'] == (10, 90)
        if url == giovanni.CATALOGUE_URL:
            assert kwargs['headers'] == {}
            return response(json.dumps({'configured_variables': [giovanni.VARIABLE]}).encode())
        assert kwargs['headers'] == {'Authorization': 'Bearer SYNTHETIC-SECRET'}
        return response(point_csv())
    monkeypatch.setattr(requests, 'get', get)
    result = giovanni.load_giovanni(24.4539, 54.3773, 2020, 2020)
    assert len(calls) == 2
    assert 'SYNTHETIC-SECRET' not in json.dumps(result.provenance)
    assert 'SYNTHETIC-SECRET' not in result.original.decode()
    assert result.provenance['request_url'].startswith(giovanni.TIMESERIES_URL)
    assert result.provenance['catalogue_check']['variable_count'] == 1


def test_unavailable_variable_does_not_fallback(monkeypatch):
    monkeypatch.setenv('EARTHDATA_TOKEN', 'SYNTHETIC-SECRET')
    monkeypatch.setattr(giovanni, 'configured_variables', lambda: (['OTHER_VARIABLE'], {}))
    monkeypatch.setattr(giovanni, '_get', lambda *a, **k: pytest.fail('Must not request another source'))
    with pytest.raises(ValueError, match='not in the current'):
        giovanni.load_giovanni(24.4539, 54.3773, 2020, 2020)


@pytest.mark.parametrize('body', [b'not json', b'{}', b'[]', b'{"configured_variables":"bad"}',
                                 b'{"configured_variables":[1]}'])
def test_malformed_catalogue(monkeypatch, body):
    monkeypatch.setattr(requests, 'get', lambda *a, **k: response(body))
    with pytest.raises(ValueError, match='invalid'):
        giovanni.configured_variables()
