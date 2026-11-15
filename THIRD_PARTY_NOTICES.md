# Source attribution and third-party terms

The MIT license in `LICENSE` applies to the contributors' original code and
documentation. It does not relicense NASA data, third-party software, or uploaded files.

## NASA POWER data

Credit: NASA Langley Research Center, Prediction Of Worldwide Energy Resources
(POWER) project, supported by NASA's Earth Science Division. The bundled data use
the **POWER Monthly and Annual API v2.10.0**, accessed **14 November 2026 UTC**,
parameter **T2M**, 2001–2025, at Abu Dhabi and Oslo. Response headers identify
**MERRA2** as the source. These are model grid-cell estimates. We do not assign
the separate Giovanni M2IMNXASM DOI to POWER responses.

The [NASA-managed POWER open-data listing](https://registry.opendata.aws/nasa-power/)
describes unrestricted use/access/download and links **CC BY 4.0**. Retain attribution
and the [CC BY 4.0 license link](https://creativecommons.org/licenses/by/4.0/).
The [POWER referencing guide](https://power.larc.nasa.gov/docs/referencing/) requests
project credit, service/version, and access date. Its publication/redistribution
notification is a request; no notification has been sent on the team's behalf.

Original JSON responses are unchanged. Derived annual data use day-weighted monthly
means; chart departures subtract each point's mean over shared complete years.
These transformations and the OLS limitations are recorded in downloads. Retain
`data/demos/manifest.json` with the originals to preserve requests and checksums.
NASA has not endorsed or validated this application or its conclusions.

## Direct software dependencies

| Package | Tested version | Main project license | Upstream |
|---|---|---|---|
| Streamlit | 1.67.0 | Apache-2.0 | https://github.com/streamlit/streamlit |
| pandas | 2.3.3 | BSD-3-Clause | https://github.com/pandas-dev/pandas |
| NumPy | 2.5.4 | BSD-3-Clause; bundled components have additional notices | https://github.com/numpy/numpy |
| SciPy | 1.18.1 | BSD-3-Clause; bundled components have additional notices | https://github.com/scipy/scipy |
| Plotly.py | 6.9.0 | MIT | https://github.com/plotly/plotly.py |
| Requests | 2.34.2 | Apache-2.0 | https://github.com/psf/requests |
| earthaccess (local authenticated workflow only) | 0.19.0 | MIT | https://github.com/nsidc/earthaccess |
| pytest (development only) | 9.2.0 | MIT | https://github.com/pytest-dev/pytest |

These identifiers were checked against installed distribution metadata/license files.
They summarize the main projects, not every bundled binary's terms. Preserve the
upstream license/NOTICE files installed with packages, including transitive and
vendored components; do not strip `.dist-info` directories from release images.
`requirements-public.txt` pins direct dependencies only. Re-resolved dependencies
and the base image must retain their own notices. No third-party source is vendored
in this repository. Browser QA uses Playwright/Chrome outside the released app.

## Other data and resources

Giovanni API implementation references NASA's
[GES DISC point-series tutorial](https://github.com/nasa/gesdisc-tutorials/blob/main/notebooks/How_to_Access_GiC_Time_Series_Service.ipynb).
The saved Abu Dhabi investigation additionally bundles actual **Giovanni browser
exports**, acquired 15 November 2026 (Asia/Dubai): Global Modeling and Assimilation
Office (GMAO), **MERRA-2 instM_2d_asm_Nx: 2d, Monthly mean, Single-Level,
Assimilation, Single-Level Diagnostics V5.12.4 (M2IMNXASM)**, distributed by GES DISC,
[doi:10.5067/5ESKGQTZG7FO](https://doi.org/10.5067/5ESKGQTZG7FO), variable T2M.
Acknowledge NASA GES DISC Giovanni for the area-averaged visualization/acquisition.
The [NASA dataset listing](https://data.nasa.gov/dataset/merra-2-instm-2d-asm-nx-2dmonthly-meansingle-levelassimilationsingle-level-diagnostics-0-6-224d6)
marks access public and links [U.S. government works terms](https://www.usa.gov/government-works).
This is a separate product citation from POWER, not a transfer of POWER's license.
Retain `data/demos/giovanni_manifest.json` with the unchanged chart CSVs. Derived
values restore the browser-local monthly labels and convert K to °C; annual means
require all twelve months. Scope, evidence and missing January 2001 are documented
in `docs/GIOVANNI_ACQUISITION.md`. No NASA endorsement or live point-API verification
is claimed.
User-uploaded exports retain their own product terms and require source verification.
Scientific and challenge-rule references are listed in `docs/RELEASE_READINESS.md`.
