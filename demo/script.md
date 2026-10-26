# Walkthrough script: Windward UK Day-Ahead Renewable Intelligence

Narrated screen walkthrough of the implemented React + Python application using real Elexon January 2026 data (`WINDFOR/stream` and `FUELHH/stream`). Voice: British English Neural Audio (`en-GB-RyanNeural`). 

---

## Part 1: Client Pitch (Energy Utility Wholesale Trading Desk)

### 01 · Part 1 · Day-Ahead Wind Intelligence for the UK Market
**Screen:** `02-decision.png`  
**Narration:**
> Welcome to Windward, a decision-time renewable intelligence platform developed specifically for the UK wholesale power trading desk. As an energy utility buying in the day-ahead auction, your mission is to meet consumer electricity demand reliably by calculating exactly how much additional power, such as thermal generation, must be procured beyond weather-dependent wind. Because purchase decisions must be locked in one day prior to delivery, traders cannot rely on hindsight; they need the exact latest forecast available at the decision gate, coupled with quantified historical forecast error to hedge procurement risk. Windward integrates live national wind actuals and forecasts from Elexon BMRS to deliver complete transparency.

### 02 · Part 1 · Decision Desk: Point-in-Time Forecast Curves
**Screen:** `02-decision.png`  
**Narration:**
> The Decision Desk anchors directly on the day the purchase decision is made. For January 2026, selecting January 15 immediately presents the forecast curve for delivery on January 16. Traders can configure their exact auction cutoff, such as nine AM for the desk assumption, or pre-EPEX and pre-N2EX presets, along with an optional data receipt buffer. The system selects the newest eligible forecast published before that cutoff. For this delivery day, we see an average forecast of 7,930 megawatts and 95.2 gigawatt-hours of covered energy, with an average forecast age of just 1.5 hours at decision time.

### 03 · Part 1 · Granular Evidence: Full Publication Audit Trail
**Screen:** `02-decision.png` (interval table)  
**Narration:**
> Trust requires granular verification. Below the main curve, an interactive interval table reveals the exact pedigree of every point. Each row details the target delivery half-hour, forecasted megawatts, precise Elexon publication timestamp, forecast age at auction cutoff, and revisions from earlier runs. Every view supports full CSV export tagged with a cryptographic SHA-256 snapshot hash. Rather than pretending a single forecast run generated the entire delivery day, Windward makes the composition of different publication vintages completely transparent to analysts and risk officers.

### 04 · Part 1 · Hindsight Analysis: Quantifying Outturns and Shortfall
**Screen:** `03-hindsight.png`  
**Narration:**
> Decision support must remain strictly separate from retrospective evaluation. Activating the hindsight toggle overlays actual outturns from Elexon's FUELHH stream. An explicit warning alerts users that outturn data was not available when the day-ahead auction cleared. We use the industry standard error convention: forecast minus actual. A positive error signifies wind underdelivery, indicating that thermal generation had to be dispatched or imbalance cashout paid. Visualizing these misses against the decision-time curve allows the desk to immediately spot ramp mismatches and systemic forecast biases.

### 05 · Part 1 · Accuracy Lab: Rigorous Quantitative Error Evaluation
**Screen:** `06-accuracy.png`  
**Narration:**
> The Accuracy Lab evaluates January 2026 forecast performance across multiple quantitative dimensions rather than a single misleading metric. For the full month across all 744 matched intervals, the Mean Absolute Error was 2,022 megawatts, while Root Mean Square Error reached 2,497 megawatts, penalizing extreme forecast swings. Crucially, signed mean bias was positive 1,746 megawatts, revealing that national wind was systematically over-forecasted. In fact, wind underdelivered against the day-ahead forecast in 84.7 percent of intervals. Weighted Absolute Percentage Error was 17.9 percent, providing a stable relative metric.

### 06 · Part 1 · Temporal Profiles: Diurnal Patterns and Lead-Time Decay
**Screen:** `06-accuracy.png` (breakdown section)  
**Narration:**
> To manage balancing risks, traders need to know when errors typically occur. The Accuracy Lab breaks down performance across time. The daily bar chart highlights volatile delivery days, allowing a one-click drill down into any specific day's decision snapshot. The hourly breakdown illustrates diurnal error shapes across UK settlement periods, while the horizon analysis measures how forecast accuracy degrades as lead time increases. These empirical insights help the trading desk price volumetric risk directly into day-ahead bids.

### 07 · Part 1 · Honest Uncertainty: Respecting Data Resolution and Gaps
**Screen:** `05-gaps.png`  
**Narration:**
> A core strength of Windward is technical integrity. Elexon's WINDFOR stream publishes forecasts on an hourly cadence, whereas FUELHH actuals arrive every half hour. Rather than smoothing or fabricating synthetic half-hourly numbers, Windward reports the exact 24 matching intervals and clearly discloses 50 percent interval coverage with partial energy totals. Furthermore, the empirical uncertainty band uses pooled residuals strictly from earlier January decision dates, ensuring no future error leakage occurs in early January.

### 08 · Part 1 · Methodology & Client Impact: A Solid Foundation
**Screen:** `07-method.png`  
**Narration:**
> The Data and Methodology view presents the complete analytical contract: dataset endpoints, formulas, quality checks, and cryptographic hashes. We clearly delineate operational scope: national Elexon wind generation is a crucial baseline, though individual utility thermal procurement also depends on contracted portfolio hedges and consumer demand. Windward provides your trading desk with an auditable, quantified wind forecast foundation that eliminates guesswork, minimizes imbalance exposure, and optimizes day-ahead thermal procurement.

---

## Part 2: Technical Lead Review (Architecture & Engineering)

### 09 · Part 2 · Technical Review: Lean, Decoupled Architecture
**Screen:** `09-overview.png`  
**Narration:**
> Moving to the internal technical lead review: our system architecture is intentionally lean, auditable, and decoupled. The backend is written in Python using FastAPI, providing strict type validation, asynchronous performance, and security hardening. The frontend is a modular React single-page application served from the same origin, eliminating cross-origin complexity. All analysis operates over an immutable, checksummed historical snapshot. Decoupling data ingestion from web request handling ensures deterministic performance with zero database overhead.

### 10 · Part 2 · Ingestion Pipeline: Resilient Elexon Stream Integration
**Screen:** `10-architecture.png`  
**Narration:**
> The ingestion pipeline in backend app ingest connects directly to Elexon's BMRS stream APIs. It downloads publication windows for WINDFOR and FUELHH WIND, applying exponential backoff and retry handling for HTTP 429 and transient transport errors. Raw daily responses are hashed and cached on disk. The ingest pipeline normalizes payloads, handles settlement periods, strips non-wind fuels, deduplicates exact timestamps, quarantines conflicting records, and performs an atomic filesystem replace of data snapshot json.

### 11 · Part 2 · As-of Temporal Correctness: Preventing Look-Ahead Bias
**Screen:** `15-source.png`  
**Narration:**
> Preventing look-ahead bias is paramount in energy trading systems. In backend app domain, our Store class enforces two separate availability guards. First, for any target interval, only forecasts with publishTime earlier than or equal to the decision cutoff minus availability buffer are considered. Second, when computing decision-time historical calibration, actual outturns are strictly guarded: an interval must be fully completed and its publication timestamp must precede the decision time. Future actual revisions cannot contaminate historical decision samples.

### 12 · Part 2 · Analytical Domain: Exact Matching and Robust Metrics
**Screen:** `12-analysis.png`  
**Narration:**
> All domain functions are pure and stateless, taking timezones and daylight saving boundaries into account. Forecasting metrics join on exact UTC timestamps. Missing intervals remain null rather than defaulting to zero, preventing distorted averages. Summary metrics aggregate matched half-hours directly rather than averaging daily scores. We compute WAPE as total absolute error divided by total actual generation, preventing division-by-zero anomalies during low wind periods. Empirical error percentiles require a minimum of seven prior days and 168 observations.

### 13 · Part 2 · Frontend Engineering: Native React Without Build Overhead
**Screen:** `11-correctness.png`  
**Narration:**
> The frontend is engineered with React 18 using native ES modules and React createElement, completely bypassing unnecessary Node build pipelines for production simplicity. Custom SVG visualizations feature responsive viewBox scaling, gap-tolerant path drawing that breaks cleanly across unobserved intervals, and full keyboard navigation. Strict Content Security Policy headers restrict script execution strictly to self, with zero external CDN dependencies or tracking scripts.

### 14 · Part 2 · Quality Assurance: Comprehensive Automated Test Harness
**Screen:** `16-evidence.png`  
**Narration:**
> Our verification harness includes 53 Python backend tests, achieving 94 percent statement coverage across domain logic, API routes, and ingestion edge cases. An additional 6 frontend tests validate time formatting and gap handling. Furthermore, automated Playwright Chromium smoke tests run against live HTTP endpoints, validating Content Security Policy headers, React mounting, interactive filters, CSV file downloads, and the OpenAPI documentation explorer.

### 15 · Part 2 · Production Readiness: Multi-Platform Containerization
**Screen:** `14-release.png`  
**Narration:**
> For deployment, the codebase includes a hardened multi-stage Dockerfile that runs as an unprivileged non-root appuser, paired with Docker Compose configured with read-only data mounts, dropped capabilities, and active health checks on port 8000. For cloud hosting, vercel json defines an optimized serverless FastAPI deployment bundled with static assets and the real January data snapshot. Interactive Swagger and OpenAPI documentation is accessible at api slash docs.

### 16 · Part 2 · Submission Handover: Fully Verified Pilot Release
**Screen:** `14-release.png`  
**Narration:**
> In summary, the project fulfills all assignment requirements: live ingestion of Elexon's WINDFOR and FUELHH streams for January 2026, rigorous decision-time forecasting and quantitative error evaluation, a polished React and Python web application, automated test coverage, Docker and Vercel deployment configurations, and this structured walkthrough video. The repository is packaged under the anonymous identifier k7m4q9 with complete documentation, ready for team review and client rollout. Thank you.
