# Engineering handover

## Shape of the system

```text
Elexon WINDFOR + FUELHH/WIND
          |
          v  batch command, outside request path
HTTP adapter -> raw response cache + manifests
          |
          v  normalise, quarantine, scope, quality checks
immutable data/snapshot.json
          |
          v  source-separated loader + SHA-256
pure Python domain functions
          |
          v  read-only FastAPI routes
React decision / accuracy / methodology views + CSV
```

`ingest.py` owns network interaction. `domain.py` knows nothing about HTTP or UI. `repository.py` chooses an explicitly named source, validates its mode and caches it. `main.py` validates input, translates absent datasets into 503, and delivers the same-origin frontend. This separation makes temporal logic testable without a network or browser.

## Important choices and tradeoffs

**Immutable file rather than database.** The scope is a fixed month. A versioned JSON snapshot has a small operational footprint, works in a read-only container or serverless bundle and is easy to inspect. Raw responses and hashes support audit. The tradeoff is manual ingestion/redeployment and linear scanning of short version lists. Multi-year history, incremental ingestion, concurrent updates or multiple providers would justify a database and indexed publication/target keys.

**Batch ingestion, not startup or request-time fetching.** A web request must not trigger 60-plus external calls. Raw requests use timeouts, bounded retries for transport/429/5xx errors, publication-day windows and checksummed cache reuse. Only a successful validated import atomically replaces the snapshot. The pilot does not implement a scheduler, distributed lock or multiwriter transaction.

**As-of selection per target.** A newest complete batch is not assumed. Explicit version selection prevents hindsight leakage and exposes mixed vintages. Historical calibration applies the availability rule to actual revisions as well as forecasts. Data without a publication timestamp cannot establish point-in-time availability.

**Separate historical and decision contracts.** Default decision responses remove actual values, actual publication times, realised error and retrospective summary metrics. Accuracy is intentionally a hindsight view. The UI's toggle is an educational distinction, not an access-control boundary; the pilot API is public and can return actuals when requested.

**React without a build chain.** Native modules, hooks and `createElement` implement the app. SVG plots have exported exact data and accessible descriptions. A local runtime avoids CDN dependencies. The checked-in ReactDOM reports a prerelease identifier; replace it with matching audited maintained packages before a production release. This is a transparent offline compromise, not an architecture recommendation to extract dependencies from unrelated products. See `THIRD_PARTY_NOTICES.md`.

**Bounded in-process caches.** Two source stores, up to 512 day snapshots and 128 accuracy requests are cached. Date ranges, cutoff patterns and buffers are bounded. Cache invalidation is a restart/redeploy after snapshot acceptance. Serverless workers may each compute their own cache. This is acceptable at pilot scale, not a shared distributed cache.

**One origin.** FastAPI serves the React assets and API. No CORS wildcard or third-party runtime request is needed. A local API explorer replaces Swagger's CDN-based default so the self-only script policy works. Security headers include CSP, no-sniff, anti-framing and referrer policy. The application uses text rendering, not untrusted HTML injection.

## API map

| Route | Purpose |
|---|---|
| `GET /api/health` | Process liveness, not a claim that real data is installed |
| `GET /api/meta?source=real` | Scope and snapshot provenance; 503 if absent |
| `GET /api/snapshot` | One decision's next-day curve; defaults real/15 January/09:00 |
| `GET /api/accuracy` | Ordered January decision range, explicit hindsight |
| `GET /api/export.csv` | Auditable interval rows; actual columns require `reveal_actual=true` |
| `GET /api/openapi.json` | Generated parameter contract |
| `GET /api/docs` | Local GET explorer |
| `GET /review` | Human technical handover |

All analytical routes accept `source=real|synthetic`. Snapshot and accuracy additionally accept local cutoff and a 0–60 minute buffer. Unknown API routes stay 404, rather than becoming an HTML fallback. Response dictionaries are covered by contract tests but not comprehensively declared as typed Pydantic response models; adding those is a useful next hardening step.

## Failure and security behaviour

Missing or malformed real snapshots fail closed. Synthetic mode requires deliberate selection and always carries its provenance. Duplicate conflicts are quarantined and counted. Partial coverage is not hidden behind a complete-looking curve or full-day energy total. No secrets or account credentials are embedded.

The public pilot has no authentication, authorisation, personal data, trade execution or administrative writes. It is not ready to host a utility's confidential positions. Production use requires identity/roles, perimeter controls, dependency and container scans, rate limiting, structured monitoring, access logging appropriate to privacy requirements and formal data acceptance. The current log middleware records path/status/duration; it is not a complete observability platform.

## Packaging and verification

Python 3.13, pinned direct Python dependencies and a non-root Docker image are supplied. Compose mounts data read-only and drops capabilities. No Docker daemon was available during authoring, so the container build remains a release check. The Vercel FastAPI configuration is prepared but unexecuted. Vercel does not run this Dockerfile; they are separate delivery paths.

Local verification: 53 Python tests, 6 JavaScript tests and 13 browser assertions passed. Python statement coverage rounds to 94%; it does not prove branch correctness. The offline browser harness uses a TestClient fetch bridge because browser HTTP navigation is prohibited here. `scripts/http_smoke.py` and the CI workflow are prepared for full HTTP, CSP, downloads and container checks in a network-enabled environment. Those external checks have not yet passed merely because the configuration exists.

Known gaps: live API contract, real source-population comparability, actual data resolution, final coverage, maintained dependency replacement, full dependency lock and security scan, physical Docker execution, real HTTP/browser test, public deployment, incognito checks and upload/submission.

## 16-hour scope allocation

This is a proposed timebox, not a claim about measured hours worked.

| Workstream | Budget |
|---|---:|
| Domain research and interpretation | 2.0 h |
| Importer and auditable data model | 2.5 h |
| As-of logic and numerical analysis | 2.5 h |
| React interface and charts | 3.0 h |
| Automated tests and edge cases | 2.0 h |
| Container and deployment checks | 1.0 h |
| README, pitch and technical walkthrough | 2.0 h |
| Public-access verification and submission | 1.0 h |
| **Total** | **16.0 h** |

Do not spend the timebox building portfolio optimisation, payment systems, authentication infrastructure or a data warehouse. Preserve the non-negotiable release gates: real data provenance, no temporal leakage, visible coverage, working public links and a playable video.
