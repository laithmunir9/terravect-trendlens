# Fixed Giovanni trend inference feasibility — 15 November 2026

**Decision: retain the current qualified conclusions.** This focused pass did not
establish a calibrated autocorrelation-robust significance test. No new significance
assessment, interval, p-value, or inference method is exposed in the app, downloads,
or generated findings. Existing datasets, annual aggregation, descriptive estimates,
and ordinary OLS outputs are unchanged. The offline candidate is not a supported
method for uploads or other investigations.

## Fixed design and candidate

The checksum-verified Abu Dhabi Giovanni snapshot yields **24 consecutive complete
calendar years, 2002–2025**. January 2001 is missing; the existing annualizer excludes
2001 and weights monthly means by calendar days, including leap days. This audit
uses those annual values without modification. Adjacent observations are one
calendar year apart; leap years do not create missing annual periods. It does not
treat the 288 underlying months as 288 independent annual-trend observations.

The estimand is the linear slope of these annual area-average reanalysis temperatures
over this fixed window. The model is `annual temperature = intercept + slope ×
centered calendar year + error`. The candidate keeps the existing OLS slope
(**0.355843 °C/decade**) and changes only its estimated covariance:

- Bartlett/Newey–West HAC, weights `1 − j/(L+1)` for calendar lag `j ≤ L`.
- Covariance multiplier `n/(n−2) = 24/22` for the fitted intercept and slope.
- Approximate two-sided Student t reference with 22 degrees of freedom, nominal
  5% rejection and corresponding nominal 95% interval. This correction and reference
  distribution are conventions, **not an exact small-sample test** under dependence.
- Inspect every lag from 1 to 6 annual periods; lag 0 is a heteroskedasticity-only
  diagnostic, not an autocorrelation correction. The common rule
  `floor(4(n/100)^(2/9))` gives lag 2. The 1–6 range checks short through six-year
  bandwidth sensitivity; it is not evidence that longer dependence is absent.
  No bandwidth is selected by the smallest p-value.

For centered years `x`, residuals `e`, and `z = x*e / sum(x²)`, the candidate slope
variance is `24/22 × [sum(z²) + 2 sum_j (1−j/(L+1)) sum_t z_t z_(t−j)]`.
This is the slope entry of the full sandwich covariance. Tests compare against an
independently assembled full design/kernel matrix, including lag 0.

The [statsmodels HAC documentation](https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_hac.html)
specifies consecutive equally spaced periods and documents the bandwidth rule;
its [implementation](https://www.statsmodels.org/stable/_modules/statsmodels/stats/sandwich_covariance.html)
provides the Bartlett sandwich and covariance correction reference. No statsmodels
dependency was added. The audit rejects gaps, reordered/duplicate years, other
windows, nonfinite data, and constant or numerically exact linear series.

Candidate slope standard errors (°C/decade) are:

| Maximum lag (years) | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Candidate SE | 0.07139 | 0.08029 | 0.08478 | 0.08899 | 0.09032 | 0.08973 | 0.08807 |

These are unvalidated covariance diagnostics, not endorsed uncertainty intervals.
Observed candidate p-values are deliberately not reported as a significance
assessment. Stability across bandwidths cannot establish test calibration.

## Small-sample failure evidence

The reproducible audit simulates 20,000 independent **zero-trend** series per noise
scenario on the exact same 24-year design, using NumPy seed `20261115`. Errors are
Gaussian stationary AR(1), initialized at their stationary distribution, with unit
innovation variance. Each correlation scenario uses fresh draws; all bandwidths
within a scenario use the same draws. These are stress scenarios, not estimates
of the actual climate error process. Error variance scale does not affect the test.

The empirical rejection percentages for a nominal **5%** test are:

| AR(1) correlation | Lag 1 | Lag 2 | Lag 3 | Lag 4 | Lag 5 | Lag 6 | Reject at every lag 1–6 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0.0 | 8.16 | 10.28 | 12.71 | 14.84 | 17.09 | 19.03 | 7.84 |
| 0.3 | 15.45 | 16.61 | 18.59 | 20.55 | 22.79 | 24.50 | 14.63 |
| 0.6 | 27.47 | 26.51 | 27.12 | 28.68 | 30.21 | 32.01 | 24.82 |
| 0.9 | 54.70 | 51.90 | 50.68 | 50.80 | 51.45 | 52.34 | 49.46 |

Monte Carlo standard errors are at most 0.36 percentage points (approximately
±0.7 points for a 95% Monte Carlo margin). Under these zero-slope scenarios, nominal
interval coverage equals one minus the rejection rate. The over-rejection is much
larger than simulation noise, including moderate dependence and independent errors.
Even requiring rejection at every tested lag fails to control false positives.
These simulations falsify adequate calibration for this candidate; they do not
validate any competing method or establish the actual series' correlation structure.

## Assumptions and alternatives

HAC's asymptotic justification needs a correctly specified deterministic trend,
zero-mean errors relative to that trend, suitable finite moments and sufficiently
weak temporal dependence. A practical finite bandwidth must adequately represent
the relevant covariance. HAC does not automatically address persistent low-frequency
variation, structural breaks, nonlinear trends, or dataset/model uncertainty.
With 24 observations these conditions cannot be established by an insignificant
residual autocorrelation test. Small residual correlation is not proof of independence.

[Müller (2014), *HAC Corrections for Strongly Autocorrelated Time Series*](https://www.princeton.edu/~umueller/HACtest.pdf)
documents small-sample problems and explains that fixed-bandwidth asymptotics need
nonstandard critical values; strong persistence remains a difficulty. This supports
the caution here but does not itself validate our particular trend design.

Potential alternatives require more work than this focused pass: an AR(1) GLS or
parametric bootstrap would impose a noise model and must account for estimated
correlation uncertainty; block bootstrap inference needs block-length sensitivity
and coverage checks with very few effective blocks; fixed-b/trend-specific methods
need the correct critical values and finite-sample validation. We did not implement
these alternatives or establish that robust inference is impossible. No method was
chosen after comparing which one gives a favorable observed result.

Even a future calibrated rejection would be **conditional evidence against a zero
linear slope in this specific window under the stated model**. It would not by
itself distinguish forced change from internal variability, establish anthropogenic
attribution, represent global climate, or prove definitive climate-change detection.
Failure to reject would likewise not prove absence of change.

## Reproduce and verify

From the repository root:

```sh
.venv/bin/python scripts/audit_giovanni_hac.py
.venv/bin/python -m pytest -q tests/test_giovanni_hac_audit.py tests/test_analysis.py tests/test_giovanni_snapshot.py tests/test_insights.py tests/test_app.py tests/test_release.py
```

The audit reads only the reviewed snapshot and prints its checksum, fixed years,
candidate SE sensitivity and synthetic-null calibration; it writes no dataset or
application state. It is not imported by the application. Tests cover the independent
covariance formula, fixed calendar guard, invalid/degenerate cases, batched
simulations, unit conversion, original slope/status and the calibration failure.
Existing analysis, snapshot, narrative, UI and release tests guard working behavior.
