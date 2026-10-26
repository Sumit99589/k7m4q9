# Demonstration assets

The separately supplied `windward-walkthrough.mp4` is a **9:01 narrated screen walkthrough**, not a YouTube upload. It uses actual application/review-page captures, synthetic market data and eSpeak-generated synthetic speech.

| Chapter | Starts | Length |
|---|---:|---:|
| Part 1: Customer pilot | 00:00 | 04:16 |
| Part 2: Technical review | 04:16 | 04:45 |

`script.md` contains the narration. `storyboard.json` connects each paragraph to a screen and on-screen explanation. `timing.json` contains exact scene timings. `captions.srt` is also embedded as a selectable English subtitle track in the MP4; its proportional timing is approximate and needs review before uploading.

Reproduction on a compatible Linux machine requires the normal development dependencies, `requirements-media.txt`, eSpeak, FFmpeg and a DejaVu Sans system font. No font files are distributed.

```bash
python -m pip install -r requirements-dev.txt -r requirements-media.txt
python -m scripts.browser_smoke
python -m scripts.capture_review
python -m scripts.create_walkthrough --output ../windward-walkthrough.mp4
```

Set `CHROMIUM_PATH` to the available Chromium binary when required. Intermediate rendering files are excluded from the repository archive and git. The code does not upload media or perform external account actions.

Before assignment submission, accept genuine Elexon data, review the narrative and replace the illustrative market-results portions with actual findings. Then upload the reviewed video as unlisted, verify signed-out playback and use the real URL in the README and form. Do not present the existing synthetic scores as January observations.
