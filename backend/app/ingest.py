"""Reproducible Elexon-only batch ingestion. Never runs on a web request.

Usage: python -m backend.app.ingest
The default actual publication window ends 5 February (exclusive), allowing
three days after the last delivery day. These are latest actuals in the fetched
window, not a claim of settlement finality. Extend --actual-publish-end to capture
later revisions. Forecast selection remains restricted to January decisions.
"""
from __future__ import annotations
import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import time
from typing import Any
import httpx
from .domain import normalize, timestamp, Store, decision_dates, metrics

BASE = "https://data.elexon.co.uk/bmrs/api/v1"
ROOT = Path(__file__).resolve().parents[2]
log = logging.getLogger("ingest")


def payload_rows(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("data"), list):
        rows = payload["data"]
    else:
        raise ValueError("Expected a JSON array or an object with a data array; refusing an error payload")
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("Every data row must be an object")
    return rows


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes(content)
    os.replace(temp, path)


def fetch(client: httpx.Client, dataset: str, start: date, cache: Path, refresh: bool) -> tuple[list[dict], dict]:
    """One publication day per request; explicit filters prevent latest-only data.

    API windows may be inclusive at both ends. Overlap is intentional and exact
    deduplication happens later; local target/publication filtering is authoritative.
    """
    end = start + timedelta(days=1)
    url = f"{BASE}/datasets/{dataset}/stream"
    params = {"publishDateTimeFrom": f"{start}T00:00:00Z", "publishDateTimeTo": f"{end}T00:00:00Z"}
    dest = cache / dataset / f"{start}.json"
    manifest_file = dest.with_suffix(".meta.json")
    if dest.exists() and manifest_file.exists() and not refresh:
        raw = dest.read_bytes()
        meta = json.loads(manifest_file.read_text())
        if hashlib.sha256(raw).hexdigest() != meta["sha256"]:
            raise ValueError(f"Cached raw checksum mismatch: {dest}")
        return payload_rows(json.loads(raw)), {**meta, "cache_reused": True}
    for attempt in range(4):
        try:
            response = client.get(url, params=params)
            if response.status_code == 429 or response.status_code >= 500:
                response.raise_for_status()
            response.raise_for_status()
            rows = payload_rows(response.json())
            raw = response.content
            meta = {"dataset": dataset, "url": str(response.url), "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "http_date": response.headers.get("date"), "sha256": hashlib.sha256(raw).hexdigest(),
                    "rows": len(rows), "cache_reused": False}
            atomic_write(dest, raw)
            atomic_write(manifest_file, json.dumps(meta, indent=2).encode())
            return rows, meta
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            retryable = isinstance(exc, httpx.TransportError) or exc.response.status_code == 429 or exc.response.status_code >= 500
            if attempt == 3 or not retryable:
                raise
            delay = min(2**attempt, 8)
            if isinstance(exc, httpx.HTTPStatusError):
                retry_after = exc.response.headers.get("Retry-After", "")
                if retry_after.isdigit():
                    delay = min(int(retry_after), 30)
            log.warning("%s %s retry %s after %ss", dataset, start, attempt+1, delay)
            time.sleep(delay)
    raise RuntimeError("Unreachable")


def days(start: date, end: date):
    while start < end:
        yield start
        start += timedelta(days=1)


def ingest(output: Path, raw_dir: Path, refresh: bool = False, actual_publish_end: date = date(2026,2,5)) -> dict:
    if actual_publish_end < date(2026,2,3):
        raise ValueError("Actual publication window must extend past the final delivery day")
    collected = {"WINDFOR": [], "FUELHH": []}
    manifest = []
    windows = {"WINDFOR": (date(2025,12,29), date(2026,2,1)), "FUELHH": (date(2026,1,2), actual_publish_end)}
    with httpx.Client(timeout=httpx.Timeout(60, connect=15), headers={"Accept":"application/json", "User-Agent":"WindwardPilot/1.0 (Elexon public data research)"}) as client:
        for dataset, (start, end) in windows.items():
            for day in days(start, end):
                rows, meta = fetch(client, dataset, day, raw_dir, refresh)
                collected[dataset].extend(rows)
                manifest.append(meta)
                log.info("%s %s: %s raw records", dataset, day, len(rows))
    # Validate all rows before considering their target dates. Do not silently drop malformed rows.
    fc, fq = normalize(collected["WINDFOR"], "WINDFOR")
    ac, aq = normalize(collected["FUELHH"], "FUELHH")
    start = timestamp("2026-01-02T00:00:00Z")
    end = timestamp("2026-02-02T00:00:00Z")
    forecast_count, actual_count = len(fc), len(ac)
    forecast_pub_start = timestamp("2025-12-29T00:00:00Z")
    forecast_pub_end = timestamp("2026-02-01T00:00:00Z")
    actual_pub_end = timestamp(f"{actual_publish_end}T00:00:00Z")
    fc = [r for r in fc if start <= r.target < end and r.published is not None
          and forecast_pub_start <= r.published < forecast_pub_end]
    ac = [r for r in ac if start <= r.target < end
          and (r.published is None or start <= r.published < actual_pub_end)]
    if not fc or not ac:
        raise ValueError("No usable January-decision forecasts or actuals; existing snapshot is unchanged")
    from .domain import iso
    def serialize(records, dataset):
        return [{"startTime":iso(r.target), "publishTime":iso(r.published), "generation":r.mw,
                 "id":r.source_id, **({"fuelType":"WIND"} if dataset=="FUELHH" else {})} for r in records]
    metadata = {
        "mode":"real", "source":"Elexon Insights: WINDFOR + FUELHH/WIND only",
        "retrieved_at": datetime.now(timezone.utc).isoformat(), "decision_scope":"2026-01-01 through 2026-01-31",
        "delivery_scope":"2026-01-02 through 2026-02-01", "timezone":"Europe/London",
        "forecast_publication_start":"2025-12-29T00:00:00Z", "forecast_publication_end_exclusive":"2026-02-01T00:00:00Z",
        "actual_publication_end_exclusive":f"{actual_publish_end}T00:00:00Z",
        "actual_revision_policy":"Latest in fetched publication window; not settlement-final or an as-first-observed archive",
        "availability_assumption":"publishTime is a proxy for availability; ingestion latency is not recorded",
        "alignment":"Exact startTime only; no interpolation or implicit hourly expansion",
        "ingest_quality":{"WINDFOR":fq, "FUELHH":aq}, "request_manifest":manifest,
        "scope_exclusions":{"WINDFOR":forecast_count-len(fc), "FUELHH":actual_count-len(ac)},
    }
    store = Store(fc, ac, metadata)
    metadata["default_cutoff_coverage"] = [{"decision_date":d.isoformat(), **metrics(store.day(d))} for d in decision_dates()]
    # Persist normalized accepted records AND ingestion quality; raw responses retain all originals.
    result = {"metadata":metadata, "forecasts":serialize(fc, "WINDFOR"), "actuals":serialize(ac,"FUELHH")}
    atomic_write(output, json.dumps(result, separators=(",",":"), allow_nan=False).encode())
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT/"data"/"snapshot.json")
    parser.add_argument("--raw-dir", type=Path, default=ROOT/"data"/"raw")
    parser.add_argument("--refresh", action="store_true", help="Re-fetch cached raw response windows")
    parser.add_argument("--actual-publish-end", type=date.fromisoformat, default=date(2026,2,5), help="Exclusive publication-date boundary for actual revisions")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        meta = ingest(args.output, args.raw_dir, args.refresh, args.actual_publish_end)
    except (httpx.HTTPError, ValueError, OSError) as exc:
        log.error("Ingestion failed; no synthetic fallback: %s", exc)
        raise SystemExit(1) from exc
    log.info("Wrote %s; inspect default_cutoff_coverage and ingest_quality before publication", args.output)
    log.info("Counts: %s", meta["ingest_quality"])

if __name__ == "__main__":
    main()
