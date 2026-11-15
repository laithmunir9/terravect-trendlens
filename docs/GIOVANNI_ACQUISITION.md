# Giovanni acquisition and validation — 15 November 2026

TrendLens now uses data downloaded through **NASA Giovanni**, a resource explicitly
listed in the [official challenge Resources tab](https://www.spaceappschallenge.org/2026/challenges/earth-system-trend-detective/?tab=resources).
This establishes a documented use of a listed resource; it is not an organizer
decision on overall Global Awards eligibility. POWER remains a separate source.

## Acquisition evidence

The user signed into [Giovanni in the Cloud](https://giovanni.earthdata.nasa.gov/),
authorized the GES DISC application, selected Time Series and monthly **2-meter air
temperature**, and generated a successful plot. The supplied screenshot showed
**M2IMNXASM_5.12.4**, **K**, the requested region **54.25, 24.25, 54.50, 24.75**
(west, south, east, north), and the **2020-01-01–2020-12-31** date range.
The user then downloaded both that chart CSV and a 2001–2025 export for the same
product and region. The generated filenames retain those request parameters.

| Snapshot | Original rows | SHA-256 |
|---|---:|---|
| `giovanni_abu_dhabi_2020.csv` | 11 | `49c142126d9d25e32b555649894da2635e3d161cf58b8835213c0c01b0a21f25` |
| `giovanni_abu_dhabi_2001_2025.csv` | 299 | `f20402e193fd70f516e6843395d9b18c1f3320ed3f0337fe59d50d3d439e2320` |

Both originals are preserved without changing bytes. The separate
[`giovanni_manifest.json`](../data/demos/giovanni_manifest.json) records original
filenames, settings, source references, hashes, review evidence and limitations.
The exact retrieval instant, native job CSV/NetCDF and Harmony job URL were not
retained. We report the acquisition **date**, not a fabricated server timestamp.
The chart CSVs contain only `x,y`; the units and geographic meaning come from the
observed workflow and source references, not from a metadata header in those files.
The source is a model/reanalysis area-average request; the CSV does not establish
which native cells contributed or their weights. It is not a city-wide observation
or the same spatial operation as the POWER point extraction.

Citation: Global Modeling and Assimilation Office (GMAO), MERRA-2 **M2IMNXASM
v5.12.4**, monthly T2M, GES DISC, [10.5067/5ESKGQTZG7FO](https://doi.org/10.5067/5ESKGQTZG7FO),
accessed via NASA Giovanni on 15 November 2026. See `THIRD_PARTY_NOTICES.md`.

## Important browser timestamp reconstruction

The short export begins `2020-01-31T20:00:00.000Z` and ends
`2020-11-30T20:00:00.000Z`. The long export follows the same pattern. Treating those
UTC month numbers directly as the scientific calendar labels would assign values
to the preceding month.

The deployed [NASA frontend bundle](https://giovanni.earthdata.nasa.gov/assets/index-qzNfl4bx.js)
was inspected on 15 November 2026; its SHA-256 is in the manifest. Its CSV parser
passes each service timestamp through `new Date(t)` and `toISOString()`. Its range
filter uses those converted dates, and the toolbar exports plotted x/y values.
NASA's [averaging-service format reference](https://raw.githubusercontent.com/nasa/harmony-regression-tests/main/test/giovanni-averaging-service/reference_data/8539508_GIOVANNI-areaAvgTimeSeries.GPM_3IMERGHH_07_precipitation.20210829-20210829.110W_25N_78W_35N.csv)
uses timezone-less time strings for the data rows. That reference is format evidence
only; none of its precipitation data is included in TrendLens.

In the acquisition environment, **Asia/Dubai (UTC+04:00)**, parsing a timezone-less
February 1 midnight produces January 31 at 20:00 UTC. Converting the exported values
back to that local calendar restores first-of-month midnight for **every row**.
This independently reproducible JavaScript example illustrates the mechanism:

```bash
TZ=Asia/Dubai node -e "console.log(new Date('2020-02-01T00:00:00').toISOString())"
# 2020-01-31T20:00:00.000Z
```

This reconstruction is supported by the acquisition timezone, exact timestamp
pattern, deployed frontend logic and NASA format reference. **It is not a comparison
against the native response from these specific jobs**, which was not retained.
That provenance limitation is disclosed in the app, brief and downloaded methods.
The rule is confined to the checksum-verified snapshots; other uploads and the live
point parser are unchanged. If acquisition metadata contradicts this reconstruction,
withhold these results until it is resolved rather than guessing another shift.

## Validation and analysis

- Strict x/y schema; original file hashes; unique, ordered, finite monthly values.
- Restored long-record coverage: **February 2001–December 2025**, 299 months.
- Restored check-record coverage: **February–December 2020**, 11 months.
- All 11 overlapping temperature values match exactly between the two downloads.
  This is an internal consistency check, not independent climate validation.
- January 2001 is absent. No imputation or POWER replacement is performed.
- Convert temperature with **°C = K − 273.15**; observed range is approximately
  **18.648–36.309 °C**. These bounds are descriptive, not verification of climate truth.
- Annual means use Gregorian month lengths and all 12 valid months. Only
  **2002–2025 (24 years)** enter the existing exploratory OLS calculation.
- The resulting descriptive slope is approximately **+0.356 °C/decade**. Its OLS
  interval and p-value remain unadjusted for autocorrelation. **Statistical
  significance is not established**, and no causal claim is made.

## Reproduce the public demonstration

```bash
.venv/bin/python -m pytest tests/test_giovanni_snapshot.py tests/test_release.py -q
.venv/bin/python scripts/check_release.py
TRENDLENS_PUBLIC=1 .venv/bin/python -m streamlit run app.py
```

Public mode opens **NASA Giovanni saved demo**. The existing **Investigate Abu Dhabi**
button opens the same dataset. Under **Data & downloads**, download original bytes,
monthly/annual data and provenance/methods. Comparison continues to use the two
unchanged POWER snapshots, with 25 shared complete years. No credentials or network
are needed for either saved investigation.

To acquire a fresh equivalent source, select the same variable, box and dates in
Giovanni; retain its source/job metadata as well as the chart CSV. NASA also documents
the supported [Harmony area-averaging workflow](https://github.com/nasa/gesdisc-tutorials/blob/main/notebooks/How_To_Access_the_Giovanni_Averaging_Service_Using_Python.ipynb),
which preserves native metadata. Fresh requests may differ after NASA product or
frontend revisions; review them separately instead of replacing the frozen evidence.

## Scope of verification

Successful manual browser acquisition is evidenced by the observed workflow and
the user's original downloads. **TrendLens's Python point API remains unverified**:
the user reported HTTP 500 for both long and one-year requests. This browser workflow
uses the separate Giovanni area-averaging service. No claim that the point API was
fixed or successfully re-run is made. No credentials, cookies, private request
headers or browser profiles are included in the public snapshot. Publication occurred
later under explicit owner approval; see `DEPLOYMENT.md` for the hosted verification.


Validation on 15 November 2026: **168 tests passed**; release allowlist scan checked
**45 files** with zero recognized credential-pattern findings. A clean public
runtime with no `earthaccess` installed and HTTP calls prohibited successfully
loaded the Giovanni default, exported the unchanged original bytes, ran the POWER
comparison, and returned to the Giovanni investigation. AppTest reported no app
exceptions. Docker build and a new visual browser check were not performed.
