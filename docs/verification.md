# Verification record

This record distinguishes executed checks from prepared commands. All numerical market values used during authoring were synthetic fixtures.

| Check | Result |
|---|---|
| Python unit, domain, API and importer tests | 53 passed |
| JavaScript utility tests | 6 passed |
| Browser integration assertions | 13 passed; no uncaught JavaScript exceptions |
| Python statement coverage | 396 / 423 statements, 93.62%, displayed rounded as 94% |
| JavaScript syntax | Passed for App.js and utils.js |
| Native Uvicorn HTTP route smoke | Passed for health, January-boundary snapshot, root, review, API explorer, JS asset and OpenAPI |
| Configuration parsing | JSON, TOML and YAML parsed successfully; direct Python dependency declarations match |
| Vendored runtime integrity | SHA-256 matches the checked-in manifest |
| Real Elexon import | Not completed; external data host could not be reached |
| Full browser HTTP/CSP enforcement | Not executed successfully in this restricted browser environment |
| Docker build/run | Not executed; Docker unavailable |
| Vercel deployment and GitHub CI | Prepared configurations only; not executed |
| Public repo, YouTube upload, incognito verification and form | Not completed |

The browser harness renders the actual React components in Chromium with a fetch bridge to FastAPI TestClient. It runs against an isolated synthetic fixture directory and an intentionally absent real snapshot. That is meaningful component/API integration evidence, but not public network, CDN, browser security-policy or deployment verification.

The native HTTP smoke uses a real Uvicorn process and HTTP client, not a browser. It proves local HTTP routing and response behaviour, not browser CSP enforcement or a production URL.

`coverage.json` contains the detailed coverage report. `browser-test-results.json` lists the browser assertions. The prepared GitHub workflow additionally includes browser HTTP and Docker stages, which still need a real successful CI run.

The MP4 has H.264 1920 × 1080 video, AAC audio, English text subtitles and two chapter markers. Technical duration is 541.2 seconds. Part 1 is approximately 256.1 seconds; Part 2 is approximately 285.1 seconds. Both are below five minutes; the total is below ten minutes. Screens are actual application captures, not evidence of real Elexon data. Narration is synthetic eSpeak speech. Captions have approximate timing and should be reviewed before publication.
