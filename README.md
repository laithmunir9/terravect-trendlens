# TrendLens — Terravect

A scientific investigation dashboard for the team's NASA Space Apps Challenge 2026 project, **Be An Earth System Trend Detective!** It explores temperature trend magnitude separately from statistical significance and retains source provenance. This is an exploratory tool, not a validated climate-change detection system.

**[Open the public application](https://terravect-trendlens.streamlit.app/)** ·
**[Public source repository](https://github.com/laithmunir9/terravect-trendlens)**

Published on Streamlit Community Cloud with Python 3.12 and no configured secrets.
Fresh unauthenticated browser checks passed for Giovanni data/charts/downloads,
POWER comparison modes and exports, methods disclosure, and mobile layout (390×844).
Desktop checks used 1440×1000. Downloaded originals and annual/comparison values
matched the reviewed snapshots. [Deployment and verification details](docs/DEPLOYMENT.md).

## What TrendLens adds

TrendLens turns NASA temperature records into guided, reproducible investigations:
users can see the rate of change, which years support it, what the uncertainty means,
and the original evidence behind every result. Its contribution is the investigation
workflow: complete-year coverage checks, comparisons over exactly shared years,
accessible explanations, and downloadable source data and methods. It does not claim
a new climate model, dataset, statistical test, or causal discovery.

The primary demonstration uses a saved **NASA Giovanni** MERRA-2 area-average export
for Abu Dhabi. The second compares unchanged **NASA POWER** point snapshots for Abu
Dhabi and Oslo. Both saved investigations work without Earthdata credentials or NASA
network access. The hosted app itself still requires internet access to Streamlit.

## Streamlit Community Cloud

Deploy branch `main` with entrypoint **`cloud/streamlit_app.py`**, Python **3.12**,
and **no secrets**. This entrypoint always enables credential-free public mode;
`cloud/requirements.txt` selects the tested public dependencies. The default screen
is the Giovanni investigation, and the existing POWER comparison remains available.
See [deployment instructions](docs/DEPLOYMENT.md) for exact settings and validation.

## Release candidate status — 15 November 2026

The completed dashboard and examples are preserved. Original application code is
now **MIT licensed**; see [LICENSE](LICENSE), [third-party notices](THIRD_PARTY_NOTICES.md),
and [AI-assisted development disclosure](AI_USE.md). NASA source measurements are
not AI-generated; findings use deterministic calculations/templates.

For credential-free public operation, set **`TRENDLENS_PUBLIC=1`**. This starts with
the labeled Giovanni browser snapshot and disables authenticated Giovanni access
before credential lookup. Public POWER and CSV upload remain available. Local mode
keeps the existing Giovanni workflow. [Deployment instructions](docs/DEPLOYMENT.md)
cover local operation and the approved Community Cloud publication workflow.

**Challenge-listed data is now used:** the Abu Dhabi investigation analyzes an actual
Giovanni browser export of MERRA-2 M2IMNXASM T2M. Giovanni is in the official 2026
challenge Resources list; POWER is separate and is not claimed to meet that requirement.
The user completed the authenticated browser workflow; the Python point API remains
unverified. This is evidence of listed-resource use, not organizer certification of
Global Awards eligibility. Read the [acquisition evidence and limitations](docs/GIOVANNI_ACQUISITION.md),
[source-backed review and remaining gates](docs/RELEASE_READINESS.md), and
[verification records](docs/verification_sources.json).

**Scientific release policy:** OLS slopes remain descriptive/exploratory. Intervals
and p-values are unadjusted; statistical significance is explicitly **not established**
without validated treatment of temporal dependence. This qualification is in the UI,
briefs, and methods metadata. No new statistical correction is claimed.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Python 3.12 and Streamlit 1.67 were used for milestone validation. The Streamlit minimum reflects the tested tab navigation and `width='stretch'` UI APIs. Live POWER requires internet access; saved examples work offline. Failed requests produce an error; no saved or simulated data are substituted automatically. Nothing is deployed automatically.

## Judge walkthrough: two reproducible investigations

Open **Example investigations**, then choose either example. Both run offline without
credentials and calculate results from retained source bytes, with checksums verified
on load. The fixed requested window is **2001–2025**.

- **Abu Dhabi:** NASA Giovanni browser export, monthly MERRA-2 **M2IMNXASM v5.12.4 T2M**,
  acquired **15 November 2026 (Asia/Dubai)**. NASA area-average request over
  **54.25–54.50°E, 24.25–24.75°N**, in Kelvin. The 299 rows require a documented browser
  timezone restoration; January 2001 is absent. Analysis uses **24 complete years,
  2002–2025**, with no filling. A separate 2020 export matches all 11 overlapping values.
  Chart CSVs have no native metadata preamble; source details come from the observed
  workflow, filenames, NASA documentation and frontend review. See
  [exact evidence, timestamp handling and limits](docs/GIOVANNI_ACQUISITION.md).
- **Abu Dhabi versus Oslo:** the existing NASA POWER point snapshots are unchanged:
  **300 months / 25 complete years** each, retrieved **14 November 2026 UTC**. They
  retain original JSON, request URLs and response metadata. This comparison continues
  to use POWER for both places; it does not mix Giovanni area averages with POWER points.

1. **Investigate Abu Dhabi:** read the fitted rate and 95% slope interval, inspect year-to-year variation, then read the plain-language explanation. Under **Data & downloads**, inspect coverage and download the original response, annual/monthly CSVs, methods JSON and investigation brief.
2. **Compare Abu Dhabi & Oslo:** switch between **Relative to period mean** and **Absolute temperature**. The first view subtracts each location's own arithmetic mean over the exact same complete years; it does not use a standard climate normal. Subtracting a constant preserves each slope. Compare trend magnitudes in the table, then inspect either location. No test of the difference between slopes is claimed. Download the aligned comparison CSV and its baseline/source methods record.

Select **NASA POWER live** in the sidebar to explore locations over another period. The POWER saved view also retains its **Use live NASA data** button. The sidebar also accepts custom coordinates, with valid latitude/longitude bounds. Temperature is currently the only supported variable; precipitation or other quantities would need appropriate aggregation and inference methods.

All narratives are generated from the computed statistics, including intervals containing zero and undefined/exact-fit inference. The reported total fitted change is slope × elapsed years, not an observed endpoint difference. Intervals and p-values remain unadjusted for autocorrelation and omit dataset/model uncertainty; causal attribution and forecasts are not provided.

To independently reproduce the snapshot retrieval and day-weighting checks without overwriting the bundled evidence:

```bash
.venv/bin/python scripts/verify_live_power.py --output /tmp/trendlens-power-recheck --start 2001 --end 2025
.venv/bin/python -m pytest tests/test_demos.py -q
```

Later NASA revisions may produce different bytes or results. Keep the original bundle and its manifest together; replacing only a response file deliberately fails the checksum check.

## Automated Giovanni point access

Choose **NASA Giovanni live (point)** to request monthly MERRA-2 **M2IMNXASM v5.12.4**, variable **`M2IMNXASM_5_12_4_T2M`** (2-meter air temperature). This directly identifies a native monthly-mean product of instantaneous assimilated fields; numerical agreement with POWER is not assumed. It is model/reanalysis data, not independent station observations. The dataset DOI is [10.5067/5ESKGQTZG7FO](https://doi.org/10.5067/5ESKGQTZG7FO).

The implementation follows [NASA's point-series tutorial](https://github.com/nasa/gesdisc-tutorials/blob/main/notebooks/How_to_Access_GiC_Time_Series_Service.ipynb):

- Catalogue: `GET https://api.giovanni.earthdata.nasa.gov/configured-variables`
- Measurements: `GET https://api.giovanni.earthdata.nasa.gov/timeseries`
- Public query parameters: `data=M2IMNXASM_5_12_4_T2M`, `location=[latitude,longitude]`, `time=YYYY-01-01T00:00:00/YYYY-12-31T23:59:59`.
- Authentication: Earthdata bearer token in the `Authorization` header only. Tokens are never included in URLs, provenance, downloads, Streamlit cache keys or session state. Redirects with credentials are not followed.

The public catalogue checked on **14 November 2026** returned 867 variables, including the selected monthly M2IMNXASM T2M variable. `M2TMNXSLV_5_12_4_T2M` was absent. Catalogue presence is not proof that a point request succeeds for every location or date. The unauthenticated point smoke request returned **HTTP 403**, with JSON code `401` and message **“Bad or missing token.”** No local Earthdata authentication was configured during that initial check. Later user-run point requests returned HTTP 500, including for 2020 alone. **The Python point retrieval remains unverified. Subsequently, the user successfully retrieved area-averaged data through the official browser workflow; the reviewed exports now power the saved Abu Dhabi investigation.**

To authenticate locally without saving credentials to disk, run this yourself in Terminal:

```bash
cd /path/to/terravect-trendlens-starter
.venv/bin/python scripts/earthdata_login.py
```

The launcher uses `earthaccess.login(strategy='interactive', persist=False)`, then starts a loopback-only Streamlit app at **http://127.0.0.1:8512** with the token in its process environment. Keep that Terminal open. In the app choose **NASA Giovanni live (point)** and **Retrieve Giovanni point series**. Start with 2020–2020 for a small smoke check; select a longer range after it succeeds. Do not paste credentials or tokens into chat. Re-run the launcher when the token expires; there is no automatic credential persistence or refresh. An existing `EARTHDATA_TOKEN`, Earthdata username/password environment configuration, or user-managed `.netrc` is also supported through the documented authentication routes. This launcher does not create `.netrc` or repository secret files.

Retrieval is explicit rather than repeated on every Streamlit rerun. Only successful, validated scientific data are retained in the current browser session. Changing the point or dates hides stale results; a failed retry clears the previous result. POWER and CSV upload remain independently usable.

The parser locates the CSV table without assuming exactly 13 metadata rows. It requires source units, parameter name and returned coordinates, preserves all metadata and original timestamps, checks the returned point against the product grid, rejects submonthly/duplicate records and dates outside the request, and masks missing values before Kelvin-to-Celsius conversion. It recognizes response-declared fills and MERRA-2's documented default `1e15`, including its float32 representation. Absent months remain missing and exclude their annual summary. The original response, SHA-256, catalogue-check provenance, NASA product/version/DOI, source URL, requested and returned coordinates, exact timestamps and processing steps are available in downloads.

**Spatial meaning:** this is point/grid-cell extraction on the native 0.5° latitude × 0.625° longitude grid. No regional average is computed or implied. For area averages, NASA documents a separate [Giovanni/Harmony averaging workflow](https://github.com/nasa/gesdisc-tutorials/blob/main/notebooks/How_To_Access_the_Giovanni_Averaging_Service_Using_Python.ipynb), with `average='area'`, an actual bounding box and quota checks. The saved Abu Dhabi data was acquired through the browser area-averaging workflow; an automated Harmony client is not implemented here.

**If access fails:** an expired/missing token requires interactive login; HTTP 429 requires waiting; an explicit quota/credit error requires quota renewal or GES DISC support; service/network errors require a retry. No alternate source is silently substituted. POWER is the simplest working automated alternative. If the required Giovanni variable is removed, NASA's [GES DISC subsetting tutorial](https://github.com/nasa/gesdisc-tutorials) documents Harmony/OPeNDAP access to the underlying product; that is a separate ingestion path, not a verified fallback implemented here.

Optional reproducible CLI checks:

```bash
# Public availability check only; does not download observations:
.venv/bin/python scripts/verify_live_giovanni.py --catalogue-only --output /tmp/trendlens-giovanni-smoke
# Run yourself in Terminal for an authenticated 2020 point retrieval:
.venv/bin/python scripts/verify_live_giovanni.py --interactive --output /tmp/trendlens-giovanni-smoke
```

The CLI exits unsuccessfully on blocked access and writes no substitute measurements. Successful retrieval saves the original CSV, normalized monthly/annual CSVs and provenance. A short smoke series does not provide enough years for a trend estimate.

## Architecture

- `app.py`: Streamlit settings, cached retrieval, comparison orchestration, import controls, coverage reports and downloads.
- `data_sources.py`: POWER HTTP/JSON validation; Giovanni-style CSV parsing, units conversion, missing-value decoding, original content and provenance.
- `giovanni.py`: authenticated Giovanni point API client, live catalogue check, native monthly response validation and provenance.
- `giovanni_snapshot.py`: reviewed browser-export loader, specific timezone restoration, cross-export validation and public Giovanni investigation.
- `analysis.py`: monthly validation, annual coverage, day-weighted aggregation, exact common-year alignment and exploratory OLS statistics.
- `charts.py`: pure Plotly figure construction, explicit selected-year bounds and visible annual-data gaps.
- `dashboard.py` and `.streamlit/config.toml`: responsive dashboard styling and guided navigation.
- `insights.py`: computed-result explanations and traceable downloadable investigation briefs.
- `demos.py` and `data/demos/`: checksum-verified genuine NASA snapshots for two explicitly selected offline investigations.
- `tests/`: offline synthetic numerical/parser fixtures, chart checks and Streamlit interaction regressions. Synthetic values are never used as application fallback data.
- `scripts/verify_live_power.py`: opt-in live checks against original NASA responses, saved to a chosen output directory.
- `scripts/earthdata_login.py`: user-run, non-persistent interactive login and local app launcher.
- `scripts/verify_live_giovanni.py`: opt-in catalogue and authenticated point-data smoke check.

## Methods and interpretation

1. POWER uses `T2M` from the monthly point API. Units and fill values come from each response. Month `13` is the API's annual summary; it is excluded. Monthly means are recomputed into annual means rather than mixing NASA's summaries with monthly values.
2. Each year requires exactly 12 finite monthly means. Missing, malformed or infinite measurements count as missing. Missing months exclude the entire year; there is no interpolation. Duplicate months fail validation, including duplicate rows that happen to agree. Invalid dates are rejected.
3. Annual mean = sum(monthly mean × days in month) / days in year. Leap days are included. This method applies to monthly mean absolute temperature on the Gregorian calendar, not totals or rates requiring another aggregation method. Exclusion of incomplete years may itself introduce selection bias.
4. The POWER two-location comparison intersects the exact set of complete years **before either fit**, including interior gaps. Coverage reports distinguish incomplete years from complete years omitted to match the other location. Less than ten common years means no comparative trend estimate, but available annual values remain viewable. Automated Giovanni access currently analyzes one point at a time.
5. OLS regresses annual means against actual calendar years. Slopes and both 95% interval endpoints use **°C/decade**. The p-value is a two-sided slope t-test with `n−2` degrees of freedom. The interval concerns the fitted slope, not individual observations or dataset uncertainty.
6. P-values and intervals are **ordinary OLS, not autocorrelation-adjusted**. Exact small-sample inference assumes independent, normally distributed errors with constant variance. Serial correlation, spatial dependence, multiple testing, short windows and model uncertainty are not corrected. Ten years is a guardrail, not a power calculation. Constant series withhold inferential statistics; exact linear fits carry a warning.
7. Trend magnitude and statistical significance are distinct. An interval containing zero does not prove no change. Individual location p-values or overlapping/nonoverlapping intervals are not a formal test of slope differences. No difference test or causal attribution is implemented.
8. A POWER point represents a model grid-cell estimate, not a thermometer station or city/country average. Uploaded regional products can have varying spatial coverage; this app cannot assess their upstream quality flags or spatial representativeness.

The x-axis always retains the selected inclusive year range, with endpoint ticks. Missing annual observations break the annual-data line. The dashed OLS model is drawn only across the fitted years and is not additional data. Source snapshots, parsed monthly values, annual values, and a JSON methods/provenance record are downloadable separately. Keep these together for reproducibility. Cached POWER provenance retains the actual retrieval time (cache TTL: one hour).

## Giovanni CSV imports

**No genuine Giovanni CSV was imported in the initial reliability milestone.** The importer and its tests do not establish compliance with challenge data-source requirements or validate any Giovanni scientific result. Automated-access verification status is stated above.

Supported:

- UTF-8/BOM comma-separated exports with comment or plain-text metadata before the header; quoted fields; commented headers; a manual header-line override for unfamiliar column names.
- A time column containing `YYYYMM`, `YYYY-MM`, `YYYYMMDD`, year-first dates or ISO timestamps; alternatively separate integer year/month columns. Timestamp labels retain their stated calendar month, without shifting timezone offsets into the previous month. Ambiguous day/month dates and annual summary rows are rejected.
- Explicit Celsius or Kelvin absolute temperatures; Kelvin is converted by subtracting 273.15. Selected-column unit labels and single-variable global `Units:` metadata are checked for conflicts. Missing units require a user selection, never a Celsius assumption. Multiple-variable exports require selection of the measurement and explicit verification of its units.
- Blank, non-numeric, NaN and infinite measurements become missing. Numeric `_FillValue` / `Missing Value` metadata and user-entered numeric sentinels are masked **before conversion**. Undeclared temperatures below absolute zero fail with instructions to check units/sentinels. Positive fill values cannot universally be distinguished from numbers: confirm every source's fill-value declaration.
- Original file bytes, SHA-256, metadata text, selected columns, units, transformations, selected years and user-entered product/version/region/citation are preserved.

The UI requires product/version, region and confirmation of monthly temperature semantics before analysis. File origin is user-supplied and is not authenticated. Inspect the metadata and measurement column carefully: CSV cannot prove frequency, physical meaning or quality. Daily exports with multiple rows per month are rejected rather than silently reduced. Annual, seasonal, climatological, non-Gregorian, anomaly, precipitation, multilevel and multi-location tables are outside this milestone. Non-comment footer rows, inconsistent column counts and non-UTF-8 encodings require re-export/cleanup; nothing is silently discarded as a supposed footer.

For a genuine investigation, export a monthly absolute-temperature time series from Giovanni; retain its original CSV and retrieval date; record product/version, variable, source DOI, region/bounding box, units, fill values, temporal/spatial averaging and applicable quality limitations. Cite the dataset itself as well as Giovanni. Confirm the current challenge's official resource and submission rules separately.

## Validation

Release checks: run `python -m pytest -q` and `python scripts/check_release.py`.
The latter scans only the explicit release file set and verifies the bundled NASA
response checksums. It reports pattern categories without exposing matching values;
it is not an exhaustive secret scanner. To prepare a local archive without publishing:

```bash
python scripts/check_release.py --archive /tmp/trendlens-release-candidate.tar.gz
```

Public-mode tests run with network calls forbidden, verify both real-data demos,
test deliberate live-source failure, block even synthetic server credentials, and
check that exports retain source bytes, AI disclosure and qualified inference status.

Dashboard milestone: **154 tests passed**. The original integration, parsing, authentication,
coverage and statistical tests remain in place. New checks cover saved NASA data and independent
annual weighting, source checksums, offline demo selection, custom coordinates, interval-aware
interpretation, and shared-year chart centering without changing slopes or hiding gaps.

Local browser QA used isolated Playwright/Chrome at **1440×1100** and **390×844**. The Browser
plugin was unavailable and the Playwright tool's shared profile was locked, so the installed
Playwright runtime launched a separate temporary browser. Checks covered page identity,
nonblank rendering, no framework exceptions or browser errors, example → investigation navigation,
relative → absolute comparison values, methods navigation, brief download, and mobile overflow.
Live POWER retrieval and the bundled original responses were checked separately. Authenticated
Giovanni browser-export acquisition is now evidenced and tested separately; Python point retrieval remains unverified. See `docs/GIOVANNI_ACQUISITION.md` for the new validation record. The completed release-candidate suite passed **168 tests**. The deployment pass subsequently ran **9 targeted release tests**, including the new Community Cloud entrypoint check; the final public-file review covered **47 files** with no recognized credential-pattern matches.

```bash
pip install -r requirements-dev.txt
python -m pytest -q
python -m py_compile app.py analysis.py data_sources.py charts.py giovanni.py scripts/earthdata_login.py scripts/verify_live_giovanni.py
```

Offline tests require no NASA connection. They cover leap-year weighting, incomplete years, duplicate and invalid times, annual summaries, HTTP/JSON failures, missing values, Celsius/Kelvin conversion, metadata and headers, known slopes, independently calculated OLS uncertainty, constant series, gaps, exact comparison alignment, chart endpoints, and Streamlit flows. Automated-access milestone result: **133 tests passed**, including 49 new checks for Giovanni parsing, authentication/error sanitization, catalogue availability, coordinate order, native monthly frequency, missing values, provenance and UI session behavior. Mocked HTTP response fixtures are explicitly synthetic; saved snapshot tests separately exercise the genuine downloaded files. The original 84 tests still pass. Initial reliability-milestone browser checks covered desktop 1440×1100 and mobile 390×844. Browser-plugin tooling was unavailable; Playwright was used directly.

Optional live verification (fails rather than substituting synthetic data):

```bash
python scripts/verify_live_power.py --output /tmp/trendlens-power-check --start 2001 --end 2025
```

On 14 November 2026, live checks for Abu Dhabi (24.4539, 54.3773) and Oslo (59.9139, 10.7522) passed for 2001–2025: each had 300 monthly values and 25 complete common years. Annual means were checked independently against the genuine monthly response values using `calendar.monthrange`. This is an arithmetic/integration check, not independent validation of MERRA-2 or comparison with station observations. The verification script saves the original responses, monthly/annual CSVs, request URLs, retrieval times, response hashes and analysis records; local validation artifacts are outside this repository.

## Audit findings addressed

| Original issue | Milestone change |
| --- | --- |
| Duplicate months silently discarded | Reject duplicates explicitly |
| Blanket `<= -900` fill rule | Source-declared exact sentinels and finite-value checks |
| Comparison fits could use different years | Fit both on exactly the same complete years |
| Slope CI mislabeled as °C | Both endpoints labeled °C/decade |
| Automatic chart range and continuous lines across gaps | Explicit selected-year bounds, endpoint ticks, and gaps |
| Short/empty series lost coverage and downloads | Coverage and downloads remain available; inference withheld |
| Constant/invalid annual series could produce misleading inference | Strict annual validation; undefined inference withheld |
| POWER response assumptions and generic errors | Validate structure/units/fill values; actionable network/HTTP/JSON errors |
| CSV assumed Celsius and discarded metadata | Explicit checked units, Kelvin conversion, metadata/hash/original-file retention |
| No reproducible provenance exports | Original content plus processing/coverage/statistics sidecar |
| Only two numerical tests | Parser, statistics, comparison, chart, failure-state and UI regression coverage |
| Unverified statement about project creation after challenge start | Removed; no unsupported timing/compliance claim |

## Remaining work before submission

The current, specific blockers are maintained in [RELEASE_READINESS.md](docs/RELEASE_READINESS.md):
Organizer eligibility acceptance, the required final demo/submission links,
and team attestations. GitHub and Streamlit Community Cloud publication and
production smoke verification are complete; NASA Space Apps submission is not authorized.
Autocorrelation-adjusted inference is deliberately not advertised; a calibrated
significance claim would require additional validated scientific work.

## Primary references

- [NASA POWER monthly and annual API](https://power.larc.nasa.gov/docs/services/api/temporal/monthly/): response scope and MERRA-2 meteorological source.
- [NASA Giovanni User Guide](https://giovanni.gsfc.nasa.gov/giovanni/doc/UsersManualworkingdocument.docx.html): time-series CSV exports, dataset provenance, and citation guidance.
- [NASA Giovanni in the Cloud](https://giovanni.earthdata.nasa.gov/): current cloud UI and access/quota notices.
- [NASA point-series API tutorial](https://github.com/nasa/gesdisc-tutorials/blob/main/notebooks/How_to_Access_GiC_Time_Series_Service.ipynb): supported endpoint, query parameters, bearer authentication and CSV metadata.
- [MERRA-2 M2IMNXASM NASA catalogue](https://data.nasa.gov/dataset/merra-2-instm-2d-asm-nx-2dmonthly-meansingle-levelassimilationsingle-level-diagnostics-0-6-224d6): product meaning, temporal resolution and DOI.
- [MERRA-2 File Specification](https://gmao.gsfc.nasa.gov/pubs/docs/Bosilovich785.pdf): native grid, units and missing-value metadata (Table 2.2-1).
- [earthaccess authentication guide](https://earthaccess.readthedocs.io/en/stable/user/howto/authenticate/): interactive, environment and netrc authentication.
