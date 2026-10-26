# Analysis contract and limitations

## 1. Question answered

For a chosen January decision day and local cutoff, what wind generation forecast was published for the next delivery day? How well did forecasts selected by that same rule match the subsequent operational wind outturn?

This is a retrospective historical pilot with a point-in-time decision view, not a live trading system. The only generation inputs are Elexon's WINDFOR and FUELHH records filtered to `fuelType == "WIND"`. Research on market timing provides context but adds no third-party observations to the analysis.

## 2. Calendar and availability

Decision dates run from 2026-01-01 through 2026-01-31, inclusive. Delivery is the next London civil day, so 2026-02-01 belongs in the data and 2026-01-01 delivery does not. January's London offset is UTC, but code uses `zoneinfo` rather than assuming this for every date. The slot generator handles 46, 48 or 50 half-hours across daylight-saving changes.

Cutoff is configurable in `HH:MM`, default 09:00. The client did not specify an exchange or internal submission buffer. The chosen default and labelled presets are scenario assumptions, not declarations of an exchange rule. A non-negative buffer of at most 60 minutes can be subtracted from the decision time.

`publishTime` is taken as the best available availability proxy. Historical publisher timestamps cannot prove API receipt at the client. A fixed buffer is a sensitivity analysis, not a reconstructed publication-delay distribution. Store actual receipt timestamps in a future live service.

The default importer starts forecast publications at 2025-12-29 and ends before 2026-02-01. This is a bounded retrieval window, not proof of a complete publication archive. Verify that it captures the relevant vintages before accepting the real snapshot; expand the import window if the live service reveals relevant older publications.

## 3. Forecast selection

For each target time `t` on delivery day `D+1`, define `C` as decision time minus buffer. Select the forecast with maximum publication timestamp among rows with `startTime=t` and `publishTime<=C`. Equality is eligible. Never choose a later revision because it is the latest row downloaded today.

Selection is per target rather than per batch. The final curve can legitimately contain mixed publication vintages; the UI shows the count and warning. Previous eligible revision and change are retained for inspection. With no eligible forecast, the result is null. There is no backfill, zero substitution or interpolation.

Rows require timezone-aware timestamps, finite numerical generation and exact half-hour target alignment. Booleans, missing generation, NaN/infinity and malformed timestamps are invalid. Operational negative values are retained and counted, not silently clipped. Exact duplicates collapse. Conflicting generation values for the same target/publication key are quarantined because response order is not a defensible tie-breaker. Such a conflict can leave an older unambiguous version as the latest accepted record; inspect quality counts before release.

## 4. Actual revisions and matching

The strict join key is `startTime`. The descriptive retrospective score uses the latest actual record by publication time within the fetched snapshot. The default actual publication window ends 2026-02-05 exclusive, giving a modest revision allowance after final delivery. This is neither settlement finality nor an as-first-observed archive. Extend `--actual-publish-end` and repeat the import to assess revision sensitivity.

Actual rows without publication time may support an ex-post score but are excluded from decision-time calibration. A published version takes precedence over undated records for the same target. Forecast publication time is always required.

If WINDFOR targets are hourly rather than half-hourly, this implementation matches only the exact timestamps. It does not assume that a forecast describes both half-hours or that linear interpolation is valid. The coverage denominator remains the expected delivery half-hours. Verify dataset resolution and averaging conventions against the live response; an agreed resampling rule would be a separately versioned methodology change.

Dataset population matters: these are operational Elexon series, not a guarantee of all UK wind output, all renewables, all embedded generation or an individual utility's contracted supply. Validate that forecast and actual series populations are sufficiently comparable before interpreting error as forecast skill.

## 5. Metrics

For the `N` matched intervals, let `F_i` be forecast MW, `A_i` actual MW and `e_i=F_i-A_i`.

| Metric | Formula / interpretation |
|---|---|
| Mean absolute error | `sum(abs(e_i))/N`, MW; typical absolute discrepancy |
| Root mean squared error | `sqrt(sum(e_i**2)/N)`, MW; penalises large misses more |
| Bias | `sum(e_i)/N`, MW; positive means systematic overforecast |
| WAPE | `100*sum(abs(e_i))/sum(abs(A_i))`; null if denominator is zero |
| Overforecast rate | `100*count(e_i>0)/N`; ties are not overforecasts |
| P90 absolute error | Linear empirical 90th percentile of `abs(e_i)` |
| P90 shortfall reference | Linear empirical 90th percentile of `max(e_i,0)`; includes zero on overdelivery |
| Net energy error | `0.5*sum(e_i)`, MWh across matched half-hours |
| Absolute energy error | `0.5*sum(abs(e_i))`, MWh; no cancellation |
| Forecast covered energy | `0.5*sum(F_i)` over available forecasts, whether actual exists or not |
| Matched coverage | `100*N/expected_intervals`; forecast and actual counts are reported separately |

Zero generation is a valid observation. MAPE is not used because near-zero actual wind can destabilise per-interval percentages. WAPE still needs its denominator and coverage interpreted carefully. The absolute-actual denominator accommodates retained negative operational readings.

Aggregate metrics are computed on all raw matched intervals, not means of rounded daily summaries. Rounding occurs in the presentation response. Half-hour MW must be multiplied by 0.5 to obtain MWh; GWh is MWh divided by 1,000. Partial coverage cannot be described as a full-day energy total.

Daily bars group by decision day, with delivery day retained. Hour-of-day groups use delivery clock hour. Lead time means target minus selected forecast publication, not target minus the desk cutoff. The full-month accuracy view is explicitly hindsight: it may not be fed back into an early-January decision as if already known.

## 6. Decision-time error context

For a decision on day `D`, take only earlier January decision days. Reconstruct each earlier forecast using the same cutoff/buffer. Then admit its actual only if the interval has completed and the actual's publication is no later than the current decision's buffered cutoff. This second restriction prevents late actual revisions from leaking into historical context.

Require at least seven earlier decision days with usable observations and 168 matched half-hours. These are transparent minimum-sample heuristics, not statistically justified sufficiency thresholds. Early January therefore legitimately shows insufficient history; the January-only constraint does not permit silently training on December errors.

Compute the pooled 10th and 90th percentiles of residual `A-F`, using linear/R7 interpolation, and add them to the current forecast. Display the P90 positive-error reference separately. The range is not clipped to a fabricated installed capacity. It is descriptive, not a validated predictive distribution, confidence interval, reserve requirement or buy recommendation. Adjacent half-hours and forecast vintages are correlated; 168 samples do not imply 168 independent events.

There is no held-out coverage calibration, regime conditioning, conformal guarantee, confidence interval for metrics, economic objective or exchange execution model. A future study should evaluate rolling-origin performance and range coverage on genuinely held-out periods before assigning probability language.

## 7. Procurement interpretation

A conceptual portfolio balance would subtract contracted wind and other secured supply from forecast customer demand, adjusted for existing positions and operational constraints. Those quantities are not present here. National wind error cannot be multiplied by an invented market share, interpreted as thermal output that must be purchased, or converted to a financial saving without additional authorised data. The product supports situational awareness and forecast-risk review only.

## 8. Provenance and acceptance

Every real snapshot records request URLs, query windows, retrieval times, raw response SHA-256 values, normalisation counts and the actual-revision policy. The server adds the snapshot file's SHA-256. CSV rows carry that hash and the decision/publication timestamps. Raw responses stay local by default.

Before reporting January findings: successfully fetch the live endpoints; inspect schemas and resolution; review exclusions/conflicts/negative values; verify all intended dates and coverage; independently hand-check several as-of selections and metric calculations; compare cutoff and revision-window sensitivity; and archive the accepted snapshot hash. No real Elexon observations were available to perform these acceptance steps in this authoring session.
