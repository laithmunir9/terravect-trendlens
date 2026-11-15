# NASA POWER demo evidence

These are original public NASA POWER monthly JSON responses, not synthetic fixtures.
The manifest records the request, coordinates, retrieval time, source/API metadata,
selected years and SHA-256 of each unchanged response.

- Variable: T2M, monthly mean air temperature at 2 meters, Celsius.
- Requested points: Abu Dhabi (24.4539, 54.3773); Oslo (59.9139, 10.7522).
- Period: January 2001–December 2025; retrieved 14 November 2026 UTC.
- Source: NASA POWER; meteorology derived from MERRA-2.
- Scope: model grid-cell estimates, not city-wide averages or station observations.
- API documentation: https://power.larc.nasa.gov/docs/services/api/temporal/monthly/

The application ignores the response's month-13 summaries and recomputes annual
means from all 12 months, weighted by calendar days. The live verification script
independently checked those calculations using `calendar.monthrange`. Tests repeat
the arithmetic check against these saved original responses. Neither check validates
MERRA-2 against independent observations.

Saved responses are an explicit source choice, never a fallback for failed live
retrieval. The application calculates all displayed findings at runtime. No fixed
scientific conclusion is bundled. See the root README for the two-minute walkthrough.


## Giovanni browser-export evidence (separate source)

`giovanni_abu_dhabi_2001_2025.csv` and `giovanni_abu_dhabi_2020.csv` are byte-identical
copies of the two user-downloaded plot exports. Their original filenames, SHA-256,
product/units/bounds, observed manual workflow and timestamp reconstruction evidence
are recorded in `giovanni_manifest.json`. They are browser-produced CSVs, not the
metadata-bearing native service responses. See `../../docs/GIOVANNI_ACQUISITION.md`.

The long record contains 299 values. Restore UTC timestamps to the acquisition
calendar (Asia/Dubai) before assigning months: February 2001–December 2025. January
2001 is absent; 24 complete years remain. The short record contains February–December
2020 and agrees exactly with those 11 values in the longer record. Never interpret
these month-end UTC strings directly as the preceding calendar month. This specific
conversion is restricted to the reviewed saved exports, not applied to other uploads.

Giovanni now supplies the existing Abu Dhabi investigation and public default.
The POWER files, loader and comparison are preserved. Public runtime needs no token.
