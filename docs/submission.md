# Publishing and submission runbook

**Not yet executed.** There are no public links to verify in this release. Do not describe local screenshots, a local MP4 or configuration files as deployment/upload completion.

## 1. Complete data acceptance

On a network-connected machine, install dependencies and run `python -m backend.app.ingest`. Inspect the raw manifests, quality counts, coverage and a few independently calculated errors. Ensure `source=real` serves genuine Elexon records. Do not rename the synthetic file or edit its mode to bypass this check. Verify applicable data redistribution terms before committing a real snapshot into a public repository. Review the dependency caveat in `THIRD_PARTY_NOTICES.md` and replace/audit the runtime for release.

Run Python/JavaScript tests, build and start the Docker image, and run `scripts.http_smoke.py` against the running app. The supplied CI workflow can repeat these checks once a repository exists; it is not evidence that a GitHub run has already succeeded.

## 2. Create the anonymous public repository

Use an authenticated GitHub account and an anonymous repository name. The commands below require the GitHub CLI and a configured git identity. They do not invent an account owner.

```bash
git init
git add .
git commit -m "Implement decision-time wind pilot with auditable analysis"
git branch -M main
gh auth login
gh repo create k7m4q9 --public --source=. --remote=origin --push
```

Check `git status` and the staged file list first. No credentials, private client data or raw response caches should be included. Confirm the repository is public, then paste its actual URL into README.md.

## 3. Deploy to Vercel

Connect the repository to Vercel and use its FastAPI framework configuration with root `app.py`. Python version and dependency files are supplied. The accepted `data/snapshot.json` and frontend assets must be included in the function bundle. Do not trigger ingestion inside a serverless request or depend on ephemeral filesystem writes.

Alternatively, from an authenticated Vercel CLI session:

```bash
vercel login
vercel deploy --prod
```

Review the actual build log and inspect the deployed root, `/api/health`, `/api/meta?source=real`, `/api/docs`, `/review`, and CSV download. Run `python -m scripts.http_smoke --base-url YOUR_ACTUAL_APP_URL`. Ensure the evaluator's production URL is accessible without deployment-protection authentication, without changing unrelated account security settings. Replace the pending deployed-link entry in README.md and push the update.

## 4. Prepare the required YouTube video

The separately supplied `windward-walkthrough.mp4` is a narrated implementation walkthrough using explicitly labelled synthetic data, with captions and chapter timings in `demo/`. It is not evidence of real January forecast performance. Review its contents and re-record the results/provenance portions once real data is accepted; do not claim synthetic accuracy as a market result. Keep customer and technical sections each within five minutes and total duration within ten minutes.

In an authorised YouTube account, upload the reviewed MP4 and set visibility to **Unlisted**, not Private. Suggested title: `January wind forecasting pilot | Customer demo and engineering review`. Include chapter timestamps from the timing manifest and a description of the pilot's scope. Upload the provided SRT captions after verifying synchronisation. Wait for video processing to complete before treating the link as usable. Paste the real unlisted URL into the README.

## 5. Verify signed-out access

Open a new incognito/private window with no active GitHub, Vercel or YouTube login. Open the exact URLs that will be submitted, not a different preview deployment or signed-in dashboard.

Confirm the application loads, serves real data, updates the cutoff, opens accuracy and downloads CSV. Confirm the public repository displays its README and code. Confirm the YouTube link plays with sound, has both sections, is no longer than ten minutes and does not request access. Seeking near the ending is important; a playable opening alone does not verify the complete video. Record the date, browser, URLs and outcome in the checklist below.

An optional fresh-browser precheck is supplied:

```bash
python -m scripts.verify_public \
  --app ACTUAL_HTTPS_APP_URL \
  --repo ACTUAL_HTTPS_GITHUB_REPO_URL \
  --video ACTUAL_HTTPS_YOUTUBE_URL
```

This checks repository visibility, real snapshot presence and signed-out page reachability. It deliberately does **not** claim to verify YouTube playback, visibility settings, audio, final duration or consent screens. Do the manual playback check even when the script succeeds.

## 6. Submit only when complete

Form: https://forms.cloud.microsoft/r/FTX6K2bbnU

Open the form, review its actual fields, and supply the real public application, repository and unlisted video URLs. Do not submit placeholders. The form was not accessible or completed in the authoring session. Record confirmation only after the actual form acknowledges submission.

| Acceptance gate | Status / evidence |
|---|---|
| Real Elexon import and sample reconciliation | Pending |
| Runtime dependency replacement/audit | Pending |
| Docker build and HTTP/browser smoke | Pending |
| Public repository and final README links | Pending |
| Production Vercel app with real data | Pending |
| Reviewed video uploaded as unlisted | Pending |
| Incognito app / repo / full video checks | Pending |
| Form acknowledgement | Pending |
