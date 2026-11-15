"""Terravect / TrendLens — transparent, exploratory NASA temperature trends."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
import pandas as pd

import streamlit as st

from analysis import INFERENCE_STATUS, align_annual, annual_coverage, annualize_monthly, calculate_trend
from charts import build_chart, build_comparison_chart, comparison_data
from data_sources import MonthlyDataset, import_giovanni, infer_giovanni_unit, load_power, read_giovanni_csv
from giovanni import EarthdataLoginRequired, LOGIN_INSTRUCTIONS, load_giovanni

from dashboard import apply_style, render_header, step
from demos import DEMO_LOCATIONS, DEMO_SOURCE, DEMO_YEARS, load_demo
from giovanni_snapshot import GIOVANNI_DEMO_SOURCE, load_giovanni_snapshot
from insights import explain_trend, investigation_brief
from release import AI_DISCLOSURE, public_mode, release_metadata

st.set_page_config(page_title='TrendLens · Terravect', page_icon='🌍', layout='wide')
apply_style()
LOCATIONS = {
    'Abu Dhabi, UAE': (24.4539, 54.3773), 'Oslo, Norway': (59.9139, 10.7522),
    'Singapore': (1.3521, 103.8198), 'Phoenix, USA': (33.4484, -112.0740),
    'Nairobi, Kenya': (-1.2921, 36.8219),
}
cached_power = st.cache_data(ttl=3600, show_spinner='Retrieving NASA POWER data…')(load_power)


def show_result(name: str, dataset: MonthlyDataset, start: int, end: int,
                annual=None, key: str = 'first'):
    st.subheader(name)
    st.caption(f"{dataset.provenance['source']} · Monthly temperature → day-weighted annual means · {start}–{end}")
    for warning in dataset.warnings:
        st.warning(warning)
    coverage = annual_coverage(dataset.monthly, start, end)
    complete = annualize_monthly(dataset.monthly)
    annual = complete if annual is None else annual
    excluded = coverage.loc[~coverage['complete'], 'year'].tolist()
    omitted = sorted(set(complete['year']) - set(annual['year']))
    if excluded:
        st.warning('Incomplete years excluded: ' + ', '.join(map(str, excluded)) + '.')
    if omitted:
        st.info('Complete years excluded to match the comparison: ' + ', '.join(map(str, omitted)) + '.')
    info = None
    if annual.empty:
        st.warning('No complete years available for this analysis. Each year needs 12 valid monthly means.')
    else:
        try:
            info = calculate_trend(annual)
        except ValueError as exc:
            st.warning(str(exc))
    if info:
        a, b, c = st.columns(3)
        a.metric('Temperature trend · °C/decade', f'{info["slope_per_decade"]:+.3f}',
                 help='The fitted change per ten years. The sign indicates direction, not statistical significance.')
        lower, upper = info['lower_95_per_decade'], info['upper_95_per_decade']
        b.metric('95% OLS interval · °C/decade', 'Not estimable' if lower is None else f'{lower:+.3f} to {upper:+.3f}',
                 help='Unadjusted OLS uncertainty in the slope, not a range containing 95% of temperatures.')
        c.metric('Complete years analyzed', str(info['n_years']),
                 help='All 12 monthly values are required. Comparisons use only shared complete years.')
        st.caption(INFERENCE_STATUS)
    trend_tab, evidence_tab = st.tabs(['Trend & interpretation', 'Data & downloads'])
    with trend_tab:
        st.plotly_chart(build_chart(annual, info, name, start, end), width='stretch', key=f'{key}_chart')
        st.caption(f'Selected range: {start}–{end}. Analysis uses {len(annual)} complete years. '
                   'Gaps are not filled. The dashed fit is a model, not additional observations.')
        if info:
            explanation = explain_trend(info)
            st.markdown('#### What does this tell us?')
            st.write(explanation['magnitude'])
            if info['inference_warning']:
                st.warning(explanation['evidence'])
            else:
                st.info(explanation['evidence'])
            with st.expander('Understand the uncertainty'):
                st.write(explanation['limits'])
                p_value = info['p_value']
                st.write('**Two-sided OLS p-value:** ' + ('Not estimable' if p_value is None else f'{p_value:.4g}'))
                st.write('If the true linear slope were zero and OLS assumptions held, the p-value measures '
                         'how unusual a slope test statistic at least this extreme would be. '
                         'It is not the probability that the trend is real or caused by human activity.')
            st.caption('The p-value and confidence interval are not autocorrelation-adjusted. '
                       'They do not include dataset/model uncertainty. No causal attribution is made.')
        st.markdown('<div class="science-note"><strong>Keep investigating</strong><br>'
                    'Try a longer time window in live mode. Does the fitted direction persist? '
                    'Inspect coverage before interpreting a change. A grid cell does not represent an entire city.</div>',
                    unsafe_allow_html=True)
    with evidence_tab:
        st.markdown('#### Follow the evidence')
        st.write('Years used: ' + (', '.join(map(str, annual['year'])) or 'none'))
        st.dataframe(coverage, hide_index=True, width='stretch')
        with st.expander(f'Coverage and provenance — {name}'):
            st.json(dataset.provenance)
        st.caption('Download the source, processed data, and methods together to reproduce this investigation.')
        provenance = dict(dataset.provenance, software=release_metadata(), analysis={
            'annual_method': '12 valid monthly means, weighted by Gregorian calendar days',
            'years_used': annual['year'].tolist(), 'incomplete_years_excluded': excluded,
            'comparison_years_excluded': omitted, 'coverage': coverage.to_dict(orient='records'),
            'statistics': {k: v for k, v in info.items() if k != 'fitted'} if info else None,
        })
        st.download_button('Download annual data (°C)', annual.rename(columns={'value': 'temperature_c'}).to_csv(index=False),
                           file_name=f'{key}_annual.csv', mime='text/csv', key=f'{key}_annual')
        st.download_button('Download monthly data (°C)', dataset.monthly.rename(columns={'value': 'temperature_c'}).to_csv(index=False),
                           file_name=f'{key}_monthly.csv', mime='text/csv', key=f'{key}_monthly')
        st.download_button('Download provenance and methods', json.dumps(provenance, indent=2, allow_nan=False),
                           file_name=f'{key}_provenance.json', mime='application/json', key=f'{key}_provenance')
        if dataset.original:
            is_power = dataset.provenance['source'] == 'NASA POWER'
            st.download_button('Download original source response', dataset.original,
                               file_name=f'{key}_source.' + ('json' if is_power else 'csv'),
                               mime='application/json' if is_power else 'text/csv', key=f'{key}_original')
        st.download_button('Download investigation brief', investigation_brief(name, info, dataset.provenance),
                           file_name=f'{key}_investigation.txt', mime='text/plain', key=f'{key}_brief')
    return info


def launch_demo(compare: bool = False):
    st.session_state.update(source_mode=DEMO_SOURCE if compare else GIOVANNI_DEMO_SOURCE, year_range=DEMO_YEARS,
                            first_location=DEMO_LOCATIONS[0], compare=compare,
                            second_location=DEMO_LOCATIONS[1])
    # Remount navigation at Investigation after a launch. Ordinary tab changes
    # stay client-side, avoiding competing reruns with the launch callback.
    st.session_state['navigation_revision'] = st.session_state.get('navigation_revision', 0) + 1


def select_location(label: str, key: str, choices: list[str]):
    name = st.selectbox(label, choices, key=key)
    if name == 'Custom coordinates':
        lat = st.number_input('Latitude (°)', min_value=-90.0, max_value=90.0, value=24.4539,
                              format='%.4f', key=f'{key}_lat')
        lon = st.number_input('Longitude (°)', min_value=-180.0, max_value=180.0, value=54.3773,
                              format='%.4f', key=f'{key}_lon')
        return f'Point {lat:.4f}°, {lon:.4f}°', (lat, lon)
    return name, LOCATIONS[name]


def show_comparison(a, b, first, second, start, end):
    left_annual, right_annual = align_annual(annualize_monthly(first.monthly), annualize_monthly(second.monthly))
    st.subheader('Two places. One common timeline.')
    st.caption(f'{a} ↔ {b} · {start}–{end} · 2 m air temperature')
    st.info(f'Both location analyses use the same {len(left_annual)} complete calendar years within {start}–{end}.')
    relative = st.segmented_control('Chart view', ['Relative to period mean', 'Absolute temperature'],
                                    default='Relative to period mean', key='comparison_view') != 'Absolute temperature'
    st.plotly_chart(build_comparison_chart(left_annual, right_annual, (a, b), start, end, relative),
                    width='stretch', key='comparison_chart')
    if relative:
        st.caption('Each line is centered on its own mean over the shared complete years in the selected period. '
                   'Zero means that location’s period average, not 0 °C. This is not a standard climate-normal baseline. '
                   'Centering preserves slopes; missing years remain gaps.')
    else:
        st.caption('Absolute temperatures show how warm each location is. A warmer location does not necessarily have a faster trend.')
    if len(left_annual) >= 10:
        rows = []
        for name, annual in ((a, left_annual), (b, right_annual)):
            info = calculate_trend(annual)
            low, high = info['lower_95_per_decade'], info['upper_95_per_decade']
            rows.append({'Location': name, 'Trend (°C/decade)': f"{info['slope_per_decade']:+.3f}",
                         '95% OLS interval (°C/decade)': 'Not estimable' if low is None else f'{low:+.3f} to {high:+.3f}',
                         'Common years': len(annual)})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch')
        st.caption('Slope intervals are ordinary OLS, not autocorrelation-adjusted, and omit dataset/model uncertainty.')
    st.warning('No statistical test of the difference between slopes has been performed. '
               'Comparing individual p-values or confidence intervals does not establish a significant difference. '
               'These are model grid-cell values, not city-wide or regional averages.')
    with st.expander('Download the aligned comparison'):
        data = comparison_data(left_annual, right_annual, start, end)
        st.caption(f'First = {a}; second = {b}. Departures subtract each point’s mean across '
                   'the exact years in this CSV. Use the per-location provenance downloads below for source records.')
        st.download_button('Download comparison CSV', data.to_csv(index=False),
                           file_name='trendlens_comparison.csv', mime='text/csv')
        record = {'locations': {'first': a, 'second': b}, 'selected_years': [start, end],
                  'software': release_metadata(), 'inference_status': INFERENCE_STATUS,
                  'years_used': left_annual.year.tolist(),
                  'baseline': 'Each point’s arithmetic mean of annual means over the shared complete years',
                  'baseline_c': {'first': float(left_annual.value.mean()) if len(left_annual) else None,
                                 'second': float(right_annual.value.mean()) if len(right_annual) else None},
                  'sources': [first.provenance, second.provenance],
                  'slope_difference_test': 'Not performed'}
        st.download_button('Download comparison methods', json.dumps(record, indent=2, allow_nan=False),
                           file_name='trendlens_comparison_methods.json', mime='application/json')
    st.markdown('#### Inspect each location')
    left_tab, right_tab = st.tabs([a, b])
    with left_tab:
        show_result(a, first, start, end, left_annual, 'first')
    with right_tab:
        show_result(b, second, start, end, right_annual, 'second')


render_header()
with st.sidebar:
    st.markdown('## Terravect / TrendLens')
    st.caption('NASA Space Apps 2026 · Follow the evidence')
    step(1, 'Choose your evidence')
    source_choices = ([GIOVANNI_DEMO_SOURCE, DEMO_SOURCE, 'NASA POWER live', 'NASA Giovanni CSV upload'] if public_mode() else
                      ['NASA POWER live', 'NASA Giovanni live (point)', 'NASA Giovanni CSV upload', DEMO_SOURCE, GIOVANNI_DEMO_SOURCE])
    if st.session_state.get('source_mode') not in source_choices:
        st.session_state['source_mode'] = source_choices[0]
    source_mode = st.radio('Data source', source_choices, key='source_mode')
    if public_mode():
        st.caption('Public mode · No Earthdata credentials required. Authenticated Giovanni access is disabled.')
    is_demo = source_mode == DEMO_SOURCE
    is_saved = source_mode in (DEMO_SOURCE, GIOVANNI_DEMO_SOURCE)
    st.selectbox('Variable', ['2 m air temperature (T2M)'] if 'CSV' not in source_mode else ['Monthly absolute temperature'],
                 help='This investigation currently supports absolute temperature only. Other variables require different scientific methods.')
    st.caption('Temperature only · °C · Monthly means')
    step(2, 'Set the timeframe')
    latest_full_year = datetime.now(timezone.utc).year - 1
    st.session_state.setdefault('year_range', (2001, latest_full_year))
    if is_saved:
        st.session_state['year_range'] = DEMO_YEARS
    start, end = st.slider('Year range (inclusive)', min_value=1981, max_value=latest_full_year,
                           key='year_range', disabled=is_saved)
    st.caption('Choose at least 10 complete years for a trend. Shorter series can still be viewed and downloaded.')
    if is_saved:
        st.caption('Saved examples use a fixed 2001–2025 window. Select live POWER to change it.')
    step(3, 'Locate your question')
    if source_mode in ('NASA POWER live', DEMO_SOURCE):
        choices = DEMO_LOCATIONS if is_demo else list(LOCATIONS) + ['Custom coordinates']
        if st.session_state.get('first_location') not in choices:
            st.session_state['first_location'] = choices[0]
        a, a_coords = select_location('First location', 'first_location', choices)
        compare = st.checkbox('Compare a second location', value=False, key='compare')
        if compare:
            second_choices = [x for x in choices if x != a]
            if st.session_state.get('second_location') not in second_choices:
                st.session_state['second_location'] = second_choices[0]
            b, b_coords = select_location('Second location', 'second_location', second_choices)
        else:
            b = None
        st.caption('A point samples a model grid cell, not the whole city. POWER units are checked on every response.')
    elif source_mode == GIOVANNI_DEMO_SOURCE:
        st.caption('Abu Dhabi area · 54.25–54.50°E, 24.25–24.75°N · Giovanni area average. '
                   'January 2001 is absent; 24 complete years are analyzed.')
    elif source_mode == 'NASA Giovanni live (point)':
        a, a_coords = select_location('Point location', 'giovanni_location', list(LOCATIONS) + ['Custom coordinates'])
        st.caption('MERRA-2 M2IMNXASM v5.12.4 · T2M · native monthly means. Earthdata Login required.')
    else:
        st.caption('Choose the region and variable from your CSV metadata in the investigation panel.')
    st.divider()
    st.caption('READ THE RESULT')
    st.markdown('**Magnitude** → how fast?  \n**Uncertainty** → how precise?  \n**Coverage** → which years count?')

investigation_tab, examples_tab, methods_tab = st.tabs(
    ['Investigation', 'Example investigations', 'Methods & sources'],
    default='Investigation', key=f"navigation_{st.session_state.get('navigation_revision', 0)}")

with investigation_tab:
    if source_mode == GIOVANNI_DEMO_SOURCE:
        st.caption('SAVED GIOVANNI BROWSER EXPORT · Acquired 15 Nov 2026 · No login or live request')
        try:
            show_result('Abu Dhabi area · Giovanni MERRA-2', load_giovanni_snapshot(start, end), start, end, key='giovanni_demo')
        except ValueError as exc:
            st.error(str(exc))
    elif source_mode in ('NASA POWER live', DEMO_SOURCE):
        if is_demo:
            source_label, source_action = st.columns([3, 1], vertical_alignment='center')
            source_label.caption('SAVED NASA RESPONSE · 2001–2025 · Retrieved 14 Nov 2026 UTC · No live request')
            source_action.button('Use live NASA data', help='Use the same locations with live POWER. Change the timeframe in the sidebar.',
                                 on_click=lambda: st.session_state.update(source_mode='NASA POWER live'))
        try:
            if is_demo:
                first = load_demo(a, start, end)
            else:
                first = cached_power(*a_coords, start, end)
            if compare and b:
                if a_coords == b_coords:
                    st.warning('These coordinates identify the same point. Choose a different second location to compare.')
                else:
                    second = load_demo(b, start, end) if is_demo else cached_power(*b_coords, start, end)
                    show_comparison(a, b, first, second, start, end)
            else:
                show_result(a, first, start, end)
        except ValueError as exc:
            st.error(str(exc))
            if not is_demo and st.button('Retry NASA POWER'):
                cached_power.clear()
                st.rerun()
            st.button('Open the saved NASA example', on_click=launch_demo)
    elif source_mode == 'NASA Giovanni live (point)':
        st.info('Retrieve a point grid-cell temperature series directly from NASA Giovanni. '
                'This is MERRA-2 M2IMNXASM v5.12.4, not a regional average or a POWER download. '
                'Availability in the catalogue does not guarantee access for every period.')
        selection = (*a_coords, start, end)
        # Only scientific data are stored per browser session. No authentication
        # object/token enters Streamlit cache keys, session state, or downloads.
        if st.button('Retrieve Giovanni point series', type='primary'):
            st.session_state.pop('giovanni_result', None)
            try:
                with st.spinner('Requesting NASA Giovanni monthly data…'):
                    dataset = load_giovanni(*selection)
                st.session_state['giovanni_result'] = (selection, dataset)
            except EarthdataLoginRequired as exc:
                st.warning(str(exc))
            except ValueError as exc:
                st.error(str(exc))
        saved = st.session_state.get('giovanni_result')
        if saved and saved[0] == selection:
            show_result(f'{a} · Giovanni MERRA-2 M2IMNXASM', saved[1], start, end, key='giovanni')
        else:
            st.caption('No Giovanni measurements loaded for this selection. Choose Retrieve to request actual data.')
        with st.expander('Earthdata Login and access help'):
            st.write(LOGIN_INSTRUCTIONS)
            st.code('.venv/bin/python scripts/earthdata_login.py', language='bash')
            st.caption('The launcher uses earthaccess interactive login without saving credentials. '
                       'The token stays in the local app process environment. Existing Earthdata environment or netrc authentication is also supported. '
                       'If NASA rejects access or exhausts quota, POWER and CSV upload remain available; no source is substituted automatically.')
    else:
        st.info('Upload an actual Giovanni monthly temperature time-series CSV. '
                'No Giovanni dataset is bundled or claimed as used. Only absolute Celsius or Kelvin monthly means on a Gregorian calendar are supported.')
        uploaded = st.file_uploader('Giovanni time-series CSV', type=['csv'])
        if uploaded is not None:
            upload_key = hashlib.sha256(uploaded.getvalue()).hexdigest()[:16]
            with st.expander('Import options'):
                header_line = st.number_input('Header line (0 = automatic)', min_value=0, value=0, step=1, key=f'header_{upload_key}')
                missing_values = st.text_input('Additional numeric missing-value sentinels', placeholder='For example: -9999, 1e15', key=f'fills_{upload_key}')
            try:
                table = read_giovanni_csv(uploaded.getvalue(), header_line or None)
                st.caption(f'Detected header on line {table.header_line}; {len(table.frame)} data rows.')
                st.dataframe(table.frame.head(8), hide_index=True)
                with st.expander('Original CSV metadata'):
                    st.text(table.metadata or 'No metadata preamble found. Supply the source details below.')
                split_dates = st.checkbox('Separate year and month columns', value={'year', 'month'} <= {c.lower() for c in table.frame}, key=f'split_{upload_key}')
                date_col = st.selectbox('Year column' if split_dates else 'Time/date column', table.frame.columns, key=f'date_{upload_key}')
                month_col = st.selectbox('Month column', [c for c in table.frame if c != date_col], key=f'month_{upload_key}') if split_dates else None
                choices = [c for c in table.frame if c not in {date_col, month_col}]
                if not choices:
                    raise ValueError('A separate measurement column is required.')
                value_col = st.selectbox('Temperature measurement column', choices, key=f'value_{upload_key}')
                inferred = infer_giovanni_unit(table, value_col)
                units = st.selectbox('Source temperature units', ['Choose units', 'C', 'K'],
                                     index={'C': 1, 'K': 2}.get(inferred, 0), key=f'units_{upload_key}_{value_col}_{inferred}')
                product = st.text_input('Dataset product and version', key=f'product_{upload_key}')
                variable = st.text_input('Variable description', value=value_col, key=f'variable_{upload_key}_{value_col}')
                region = st.text_input('Region or coordinates', key=f'region_{upload_key}')
                source = st.text_input('Dataset DOI or source URL (recommended)', key=f'source_{upload_key}')
                confirmed = st.checkbox('I verified that this variable is absolute temperature, uses the selected units, and contains Gregorian-calendar monthly means.', key=f'confirmed_{upload_key}_{value_col}_{units}')
                if confirmed and units != 'Choose units' and product.strip() and variable.strip() and region.strip():
                    dataset = import_giovanni(table, date_col, value_col, units, start, end,
                        month_column=month_col, missing_values=missing_values, filename=uploaded.name,
                        metadata={'product_and_version': product, 'variable': variable, 'region': region,
                                  'source_url_or_doi': source, 'monthly_mean_and_units_confirmed': True})
                    if not source.strip():
                        st.warning('No DOI or source URL supplied. Add it for reproducible attribution.')
                    show_result(f'{product} — {region}', dataset, start, end, key='upload')
                else:
                    st.info('Select units, enter product/version and region, and confirm monthly temperature semantics to analyze this upload.')
            except ValueError as exc:
                st.error(f'CSV import: {exc}')

with examples_tab:
    st.subheader('Start with a question, not a blank chart.')
    st.write('Two reproducible investigations using NASA Giovanni and NASA POWER monthly data. '
             'Saved responses make these examples available even without a connection; every result is calculated from the source.')
    left, right = st.columns(2)
    with left, st.container(border=True):
        st.caption('01 / READ A LOCAL TREND')
        st.markdown('### Has Abu Dhabi’s temperature changed?')
        st.write('Investigate annual temperature for a small area around Abu Dhabi using Giovanni MERRA-2. '
                 'Separate the fitted trend from year-to-year variability, then check its uncertainty.')
        st.caption('Giovanni · T2M · 2001–2025 request · 24 complete years (2002–2025)')
        st.button('Investigate Abu Dhabi', type='primary', on_click=launch_demo, key='demo_single')
    with right, st.container(border=True):
        st.caption('02 / COMPARE TWO PLACES')
        st.markdown('### Does a warmer place change faster?')
        st.write('Compare Abu Dhabi with Oslo. Switch between absolute temperature and departures from each '
                 'location’s period mean to distinguish a warm climate from a changing one.')
        st.caption('Abu Dhabi + Oslo · T2M · 2001–2025 · 25 shared years')
        st.button('Compare Abu Dhabi & Oslo', type='primary', on_click=launch_demo, args=(True,), key='demo_compare')
    st.markdown('#### A two-minute investigation')
    st.markdown('1. Open an example and read the temperature trend in °C per decade.\n'
                '2. Check whether the 95% slope interval includes zero, and read the assumptions.\n'
                '3. In the comparison, switch chart views. Temperature level and trend are different quantities.\n'
                '4. Open **Data & downloads** to inspect complete years and retain the original NASA evidence.')
    st.caption('POWER snapshots: 14 November 2026 UTC. Giovanni browser exports: 15 November 2026, Asia/Dubai. '
               'Revisions to NASA products can change later live downloads. '
               'The saved response is labeled explicitly and never silently replaces a failed live request.')

with methods_tab:
    st.caption('Development disclosure: ' + AI_DISCLOSURE)
    with st.expander('Methods, limitations, and sources', expanded=True):
        st.markdown('''
    **Data:** [NASA POWER monthly API](https://power.larc.nasa.gov/docs/services/api/temporal/monthly/),
    parameter `T2M`, is derived from MERRA-2. A requested point represents a model grid cell,
    not an entire city or an independent weather-station observation. Uploaded CSVs retain their
    original metadata and file hash; their origin and scientific meaning require user verification.

    **Calculation:** Each calendar year needs 12 valid monthly means. Annual temperature is
    weighted by days in each month, including leap days. Missing months exclude the whole year;
    there is no interpolation. Duplicate months are rejected. POWER's `YYYY13` annual summaries
    are excluded. Both comparison fits use the exact intersection of complete years. The chart
    always shows the selected range, including excluded years. The fit spans only analyzed years.

    **Inference:** Ordinary least squares uses actual calendar years and reports a slope in
    °C/decade, a two-sided t-test p-value and a 95% slope interval. These are **not
    autocorrelation-adjusted** and assume independent errors, constant error variance, and
    normal errors for the exact small-sample t inference. A trend magnitude is not a significance
    claim. Ten years is a minimum guardrail, not proof of statistical power. Gaps, short periods,
    multiple comparisons, model uncertainty and changes in spatial coverage limit interpretation.
    No causal attribution or statistical test of differences between locations is provided.

    **Giovanni:** Live point access uses the documented
    [Giovanni time-series API](https://github.com/nasa/gesdisc-tutorials/blob/main/notebooks/How_to_Access_GiC_Time_Series_Service.ipynb)
    with Earthdata Login. The selected product is MERRA-2 **M2IMNXASM v5.12.4**, variable **T2M**,
    native monthly means of instantaneous assimilated fields. Numerical agreement with POWER is not assumed.
    The original response, requested point, returned grid coordinates, units and processing are retained.
    No area averaging is performed by the live point client. Catalogue availability is checked on each retrieval;
    a result is shown only after a successful data response and validation.

    **Saved Giovanni investigation:** the Abu Dhabi example uses an actual browser export from
    Giovanni's area-averaging workflow, separately from the still-unverified live point client.
    Dataset DOI: [10.5067/5ESKGQTZG7FO](https://doi.org/10.5067/5ESKGQTZG7FO).
    It represents the requested box 54.25–54.50°E, 24.25–24.75°N. It is not the POWER point series.
    The CSV contains only plotted x/y values; units and region are documented from the observed
    acquisition workflow. Browser timestamps are restored to monthly labels using Asia/Dubai;
    January 2001 is absent and excluded. Original bytes, hashes, cross-export checks and
    timestamp evidence/limitations are included in provenance. Native job metadata was not retained.

    For uploads, retain the actual export and its product/version, variable, DOI, region,
    units and retrieval details. This application does not authenticate uploaded files or support
    monthly totals, temperature anomalies, non-temperature variables or non-Gregorian calendars.
    Read the [Giovanni guide](https://giovanni.gsfc.nasa.gov/giovanni/doc/UsersManualworkingdocument.docx.html)
    for export and citation instructions. Synthetic test fixtures are software checks only;
    they are never substituted for NASA data.
    ''')
