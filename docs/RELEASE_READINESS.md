# TrendLens release-readiness review

Review date: **15 November 2026 (Asia/Dubai)**. This is a release candidate, not a
claim of submission eligibility. No service, repository, or project submission was published.

## Scientific decision

This release uses the requested **explicit qualification** option. Slopes and existing
OLS calculations are unchanged. All fits now carry a machine-readable status that
statistical significance is not established because temporal dependence has not been
validated/corrected. The same statement appears near metrics and in findings/briefs.
Intervals excluding zero are described conditionally, never as a validated detection.

A generic correction was not added just before release: this app accepts short series
(minimum 10 annual values), arbitrary missing-year patterns, and uploads whose error
structure is unknown. A reliable inference workflow across that input space has not
been validated. This is not a claim that correction is impossible. For example,
[statsmodels' Newey–West HAC implementation](https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_hac.html)
assumes consecutive, evenly spaced observations and requires a lag/kernel choice.
Dropping missing years and treating neighboring rows as neighboring years would be wrong.
Future inference work needs a specified estimand, calendar-aware handling, lag/block
sensitivity, and coverage validation for short autocorrelated series. We do not use
a nonsignificant autocorrelation diagnostic as proof of independent errors.

The app provides exploratory estimates, not causal attribution, forecasts, calibrated
climate-change detection, or a formal comparison of slopes. Dataset/model uncertainty
remains outside the OLS interval. No claim of full challenge-science completion is made.

## Official 2026 resource use — evidenced through Giovanni

The exact [2026 challenge Resources page](https://www.spaceappschallenge.org/2026/challenges/earth-system-trend-detective/?tab=resources)
was retrieved directly with TLS verification enabled. Its NASA list contains Giovanni,
Hydrology Time Series, AppEEARS, Climate Data Online, and a SeaWiFS time-series paper.
**POWER is absent.** MERRA-2 appears in the challenge's background; that does not
establish that POWER is an accepted Resources-listed access path.

The general [submission guide](https://www.spaceappschallenge.org/resources/project-submission-guide/)
asks for NASA data/resource use. The more specific
[organizer clarification](https://github.com/nasa/spaceapps/discussions/1849)
requires a NASA data source included with the challenge Resources for Global Awards.
We apply that stricter interpretation; no organizer acceptance is invented.

| Actually used | Evidence | Eligibility conclusion |
|---|---|---|
| POWER T2M, two saved 2001–2025 point responses | Original bytes, request URLs, timestamps, header `MERRA2`, checksums; independent annual arithmetic | Genuine NASA data, but Resources-list requirement **not verified** |
| Giovanni M2IMNXASM v5.12.4 T2M | Successful user-operated browser workflow; original 299-row export and 11-row check; SHA-256; unit/region evidence; documented timestamp restoration; 24 complete annual values | **Actual use of a listed resource is now evidenced.** Manual/browser provenance limits remain; overall organizer eligibility is not certified |

The existing Abu Dhabi investigation and public default now analyze this Giovanni
snapshot. See [acquisition evidence, source citation and limitations](GIOVANNI_ACQUISITION.md).
The original files contain plotted x/y values only. Units and region were observed
in the acquisition workflow; the native service response and job URL were not retained.
Dates require a documented restoration to the acquisition timezone, Asia/Dubai,
using NASA frontend/format evidence. January 2001 is absent and excluded. A native
metadata-bearing export would strengthen the provenance, but no re-download or
independent source authentication is claimed here.

The **Python point API is still unverified** after user-reported HTTP 500 responses,
including for a one-year request. The successful browser area-averaging workflow is
separate. It requires authentication during acquisition only; the bundled public
demo needs none. No POWER data are relabeled as Giovanni or silently substituted.

## Provenance, licenses and disclosure

- Existing POWER bytes and manifest hashes are unchanged; each has 300 valid months
  and 25 complete years. Independent day-weighting tests are retained.
- Both original Giovanni browser CSVs and a separate provenance sidecar are bundled;
  299 monthly values yield 24 complete years after the documented timezone restoration.
- User selected MIT for original application code; `LICENSE` is present.
  `THIRD_PARTY_NOTICES.md` separates NASA data from code and records dependency terms.
- `AI_USE.md` discloses Codex assistance. The app does not run a model or invent data.
  Text and exported metadata disclose assistance; originals remain untouched.
- The [2026 participant terms](https://www.spaceappschallenge.org/legal/) require
  appropriate rights, open licensing and source attribution. The team must confirm
  rights to any materials/history not visible in this workspace. No blanket legal
  compliance or independent human review is certified.
- Official page URLs, response hashes and resource links are recorded in
  `verification_sources.json`. Raw fetched pages are local review evidence, not
  copied into the public application. POWER attribution follows its referencing guide.

## Public operation and exposure checks

`TRENDLENS_PUBLIC=1` starts with the verified saved data, leaves public POWER and CSV
imports usable, and disables authenticated Giovanni before any credential lookup.
The release image uses no Earthdata/AI secrets. Unexpected Streamlit tracebacks and
usage telemetry are disabled in configuration. The existing local authentication
workflow is retained outside public mode.

`scripts/check_release.py` validates an explicit release file set, checks source
hashes and scans recognizable credential patterns without printing matched values.
The local archive excludes credentials, environments, caches and browser artifacts.
This is a bounded heuristic check, not a guarantee against every possible secret.
There is no `.git` history in this workspace, so historical commits cannot be audited.
Do not publish an unchecked parent directory or a separate repository history.

## Validation record before Giovanni snapshot integration

- `python -m pytest -q`: **162 passed** (original workflows plus release gates).
- `python -m py_compile`: changed Python modules compile.
- Existing and freshly installed public environments: `pip check` reports no broken requirements.
- Release allowlist: **39 files**; no recognized credential-pattern matches.
- Source hashes and independent annual weighting: both genuine NASA snapshots pass.
- Public-mode tests prohibit network calls, exercise both demos and explicit live
  failure, block a synthetic server token before authentication, and inspect exports.
- Fresh Python 3.12/macOS environment installed from `requirements-public.txt`:
  `earthaccess` is absent; both demos passed with `requests.get` forbidden. The
  initial fresh-environment AppTest exceeded its 20-second limit; a repeat completed
  in 1.8 seconds. No runtime code change was needed between those attempts.
- Isolated Playwright/Chrome at 1440×1000 against the clean runtime: health endpoint,
  page identity, saved-data default, unavailable authenticated Giovanni, visible
  inference/disclosure text and comparison interaction passed; no browser errors
  or framework exception overlay. This verifies local operation, not production hosting.
- The scan is limited to the candidate files; no Git history exists here.

## Remaining gates

1. **Organizer acceptance:** listed-resource use is now evidenced by the Giovanni
   investigation. Final eligibility still depends on the official rules and organizer
   review; the browser-export provenance limits above must remain disclosed.
2. **Submission materials:** no compliant final slide deck/video or public submission
   link is present here. The guide requires a video up to 30 seconds or up to seven
   slides, with English-language requirements and public access without login.
   The in-app investigations do not replace this deliverable.
3. **Team attestations:** verify registration/local event, development timing, ownership,
   initial-idea provenance and complete AI-use declaration. These cannot be established
   from source files. The official guide ties the deadline to the registered event;
   do not infer the team's deadline solely from this workstation's timezone.
4. **Production smoke check and approval:** Docker/Linux build is unverified because
   the Docker daemon is unavailable. Follow `DEPLOYMENT.md` on the chosen host and
   obtain explicit publication approval. No account or hosting changes were made.

Autocorrelation-adjusted significance remains an explicitly unavailable capability,
not a hidden claim. It is not required to run the public exploratory demo; it would
be required before advertising calibrated significance detection.


## Giovanni snapshot release validation

The new snapshot checks verify unchanged bytes, all 11 overlapping values, the
browser timezone regression, month coverage, rejection of altered evidence, and
independently recomputed day-weighted annual means. Public-mode tests run with all
NASA HTTP requests forbidden and no Earthdata credentials, inspect the 24-year
Giovanni analysis and downloads, then exercise the unchanged 25-year POWER comparison.
The release allowlist and Docker COPY rules now include both CSVs, the manifest,
loader and acquisition documentation. This pass does not claim a Docker build,
a new live point request or a public deployment.

Current full suite: **168 passed**. Release allowlist: **45 files**, with zero
recognized credential-pattern findings. Original POWER hashes remain unchanged.

Fresh public runtime recheck after integration: **PASS** in the existing clean
Python 3.12 environment, with `earthaccess` absent, all HTTP requests forbidden,
and Earthdata environment variables removed. Giovanni default, 24-year analysis,
exact original CSV export, POWER comparison and return to the Giovanni example all
passed with no app exceptions. New visual browser QA was not performed because
computer-use permissions were unavailable; Streamlit AppTest exercised the flows.
