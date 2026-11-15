"""Fabricated parser fixtures for software testing, NOT genuine NASA datasets."""
import json

import numpy as np
import pandas as pd
import pytest
import requests

from analysis import annualize_monthly
from data_sources import (import_giovanni, infer_giovanni_unit, load_power,
                          parse_month, parse_power_payload, read_giovanni_csv)


def payload():
    return {'properties': {'parameter': {'T2M': {**{f'2020{m:02d}': m for m in range(1, 13)}, '202013': 999}}},
            'parameters': {'T2M': {'units': 'C', 'longname': 'Synthetic temperature'}},
            'header': {'fill_value': -999, 'sources': ['SYNTHETIC TEST']}}


def test_power_full_range_and_annual_summary_exclusion():
    result = parse_power_payload(payload(), 2020, 2020)
    assert len(result.monthly) == 12
    assert result.monthly.date.iloc[-1] == pd.Timestamp('2020-12-01')
    assert result.monthly.value.max() == 12
    assert result.provenance['ignored_annual_summaries'] == 1
    assert len(annualize_monthly(result.monthly)) == 1


def test_power_missing_month_reindexed_and_fill_decoded():
    p = payload()
    del p['properties']['parameter']['T2M']['202001']
    p['properties']['parameter']['T2M']['202002'] = -999
    p['properties']['parameter']['T2M']['202003'] = 'bad'
    p['properties']['parameter']['T2M']['202004'] = None
    result = parse_power_payload(p, 2020, 2021)
    assert len(result.monthly) == 24
    assert result.monthly.value.isna().sum() == 16
    assert annualize_monthly(result.monthly).empty
    assert result.warnings


def test_power_custom_fill_and_kelvin():
    p = payload()
    p['parameters']['T2M']['units'] = 'K'
    p['header']['fill_value'] = 1e15
    p['properties']['parameter']['T2M'] = {f'2020{m:02d}': 273.15 for m in range(1, 13)}
    p['properties']['parameter']['T2M']['202001'] = 1e15
    result = parse_power_payload(p, 2020, 2020)
    assert np.isnan(result.monthly.value.iloc[0])
    assert (result.monthly.value.iloc[1:] == 0).all()


@pytest.mark.parametrize('p', [None, [], {}, {'properties': None},
                             {'properties': {'parameter': {}}}])
def test_power_malformed_structure(p):
    with pytest.raises(ValueError, match='NASA POWER'):
        parse_power_payload(p, 2020, 2020)


@pytest.mark.parametrize('unit', ['F', 'mm/day', '', None])
def test_power_bad_units(unit):
    p = payload()
    p['parameters']['T2M']['units'] = unit
    with pytest.raises(ValueError, match='units'):
        parse_power_payload(p, 2020, 2020)


def test_power_invalid_keys_and_outside_range():
    p = payload()
    p['properties']['parameter']['T2M'].update({'202000': 10, '202014': 1, 'bad': 1, '201901': 1})
    result = parse_power_payload(p, 2020, 2020)
    assert len(result.monthly) == 12
    assert len(result.warnings) == 2


def test_power_annual_only_not_accepted():
    p = payload()
    p['properties']['parameter']['T2M'] = {'202013': 22}
    with pytest.raises(ValueError, match='no monthly'):
        parse_power_payload(p, 2020, 2020)


@pytest.mark.parametrize('exception,message', [(requests.Timeout(), 'timed out'),
                                               (requests.ConnectionError(), 'Cannot connect')])
def test_power_network_errors(monkeypatch, exception, message):
    def fail(*args, **kwargs):
        raise exception
    monkeypatch.setattr(requests, 'get', fail)
    with pytest.raises(ValueError, match=message):
        load_power(0, 0, 2020, 2020)


def response(body, status=200):
    r = requests.Response()
    r.status_code = status
    r._content = body
    r.url = 'https://example.invalid/synthetic-fixture'
    return r


@pytest.mark.parametrize('status', [400, 429, 500, 503])
def test_power_http_errors(monkeypatch, status):
    monkeypatch.setattr(requests, 'get', lambda *a, **k: response(b'failure', status))
    with pytest.raises(ValueError, match=f'HTTP {status}'):
        load_power(0, 0, 2020, 2020)


def test_power_non_json(monkeypatch):
    monkeypatch.setattr(requests, 'get', lambda *a, **k: response(b'<html>down</html>'))
    with pytest.raises(ValueError, match='invalid JSON'):
        load_power(0, 0, 2020, 2020)


def test_power_provenance_and_timeout(monkeypatch):
    body = json.dumps(payload()).encode()
    def get(url, params, timeout):
        assert params['start'] == 2020 and params['end'] == 2020
        assert timeout == (10, 60)
        return response(body)
    monkeypatch.setattr(requests, 'get', get)
    result = load_power(0, 0, 2020, 2020)
    assert result.original == body
    assert len(result.provenance['response_sha256']) == 64
    assert result.provenance['retrieved_at_utc']


def table(text):
    return read_giovanni_csv(text.encode('utf-8'))


def test_giovanni_bom_metadata_commented_header_quoted_fields():
    raw = '\ufeffTitle: Synthetic test, not observations\n# Units: K\n# _FillValue: -9999\n# Time,"Temperature (K)"\n202001,273.15\n202002,-9999\n202003,N/A\n'
    t = table(raw)
    assert t.header_line == 4
    assert infer_giovanni_unit(t, 'Temperature (K)') == 'K'
    result = import_giovanni(t, 'Time', 'Temperature (K)', 'K', 2020, 2020)
    assert result.monthly.value.iloc[0] == 0
    assert result.monthly.value.isna().sum() == 11
    assert 'Synthetic' in result.provenance['original_metadata']
    assert result.original == raw.encode('utf-8')
    assert len(result.provenance['file_sha256']) == 64


def test_giovanni_separate_year_month_and_declared_positive_fill():
    t = table('Missing Value,1e15\nYear,Month,Temperature [C]\n2020,1,10\n2020,2,1e15\n')
    result = import_giovanni(t, 'Year', 'Temperature [C]', 'C', 2020, 2020, month_column='Month')
    assert result.monthly.value.iloc[0] == 10
    assert np.isnan(result.monthly.value.iloc[1])


def test_giovanni_header_override():
    t = read_giovanni_csv(b'Unfamiliar preamble\nPeriod,measurement\n2020-01,10', 2)
    result = import_giovanni(t, 'Period', 'measurement', 'C', 2020, 2020)
    assert result.monthly.value.iloc[0] == 10


@pytest.mark.parametrize('text', ['', 'title only', 'Time,Temperature\n',
                                 'Time,Temperature\n202001,10,extra',
                                 'Time,Time\n202001,10',
                                 'Time,Temperature\n202001,"broken'])
def test_giovanni_bad_csv(text):
    with pytest.raises(ValueError):
        table(text)


@pytest.mark.parametrize('value', ['2020-01', '202001', '2020-01-15', '2020/01/01',
                                   '20200101', '2020-01-01T00:00:00Z',
                                   '2020-01-01T00:00:00+03:00'])
def test_supported_dates(value):
    assert parse_month(value).year == 2020
    assert parse_month(value).month == 1


@pytest.mark.parametrize('value', ['2020', '01/02/2020', '202013', '1590000000', 'bad'])
def test_ambiguous_or_invalid_dates(value):
    assert pd.isna(parse_month(value))


@pytest.mark.parametrize('text', ['Time,T (mm/day)\n202001,10',
                                 'Units: K\nTime,T (C)\n202001,10'])
def test_unsupported_or_conflicting_units(text):
    t = table(text)
    with pytest.raises(ValueError):
        infer_giovanni_unit(t, t.frame.columns[1])


def test_wrong_user_units_rejected():
    t = table('Time,T (K)\n202001,273.15')
    with pytest.raises(ValueError, match='conflict'):
        import_giovanni(t, 'Time', 'T (K)', 'C', 2020, 2020)


def test_giovanni_duplicate_month_rejected_daily_not_collapsed():
    t = table('Time,T\n2020-01-01,1\n2020-01-02,2')
    with pytest.raises(ValueError, match='same month'):
        import_giovanni(t, 'Time', 'T', 'C', 2020, 2020)


def test_giovanni_outside_range_and_missing_values():
    t = table('Time,T\n201901,50\n202001,-9999\n202002,inf\n202003,bad\n202004,10')
    result = import_giovanni(t, 'Time', 'T', 'C', 2020, 2020, missing_values='-9999')
    assert len(result.monthly) == 12
    assert result.monthly.value.dropna().tolist() == [10]
    assert any('outside' in w for w in result.warnings)


def test_giovanni_undeclared_fill_fails_instead_of_false_trend():
    t = table('Time,T\n202001,-9999')
    with pytest.raises(ValueError, match='absolute zero'):
        import_giovanni(t, 'Time', 'T', 'C', 2020, 2020)


def test_giovanni_invalid_dates_and_outside_only():
    for rows in ['bad,10', '201901,10']:
        with pytest.raises(ValueError):
            import_giovanni(table('Time,T\n' + rows), 'Time', 'T', 'C', 2020, 2020)


def test_multiple_variables_do_not_assume_global_units():
    t = table('Units: K\nTime,air,precipitation\n202001,273,1')
    assert infer_giovanni_unit(t, 'air') is None
