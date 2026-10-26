"""Read-only FastAPI API and same-origin React delivery."""
from datetime import date
from functools import lru_cache
from pathlib import Path
import csv
import io
import logging
import time
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from .domain import FIRST_DECISION, LAST_DECISION, accuracy, decision_dates, snapshot
from .repository import DatasetUnavailable, load_store

log = logging.getLogger("windward")
app = FastAPI(title="Windward — decision-time wind intelligence", version="1.0.0", docs_url=None, openapi_url="/api/openapi.json", redoc_url=None)
Source = Literal["real", "synthetic"]
Cutoff = Annotated[str, Query(pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")]
Buffer = Annotated[int, Query(ge=0, le=60)]
ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"

@app.middleware("http")
async def headers_and_logs(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'"
    response.headers["Cache-Control"] = "no-store"
    log.info("%s %s %s %.1fms", request.method, request.url.path, response.status_code, 1000*(time.perf_counter()-start))
    return response

@app.exception_handler(DatasetUnavailable)
async def unavailable(request: Request, exc: DatasetUnavailable):
    return JSONResponse(status_code=503, content={"detail": str(exc), "code": "DATASET_UNAVAILABLE"})


def validate(day: date):
    if not FIRST_DECISION <= day <= LAST_DECISION:
        raise HTTPException(422, "Decision date must be between 2026-01-01 and 2026-01-31 inclusive")

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "windward", "version": "1.0.0"}

@app.get("/api/meta")
def metadata(source: Source = "real"):
    store = load_store(source)
    return {"decision_start": FIRST_DECISION, "decision_end": LAST_DECISION,
            "delivery_start": "2026-01-02", "delivery_end": "2026-02-01",
            "default_cutoff": "09:00", "timezone": "Europe/London", "provenance": store.metadata}

@lru_cache(maxsize=512)
def cached_snapshot(source: str, day: date, cutoff: str, buffer: int, reveal: bool):
    return snapshot(load_store(source), day, cutoff, buffer, reveal)

@app.get("/api/snapshot")
def get_snapshot(decision_date: date = date(2026,1,15), cutoff: Cutoff = "09:00",
                 buffer_minutes: Buffer = 0, reveal_actual: bool = False, source: Source = "real"):
    validate(decision_date)
    return cached_snapshot(source, decision_date, cutoff, buffer_minutes, reveal_actual)

@lru_cache(maxsize=128)
def cached_accuracy(source: str, start: date, end: date, cutoff: str, buffer: int):
    return accuracy(load_store(source), start, end, cutoff, buffer)

@app.get("/api/accuracy")
def get_accuracy(start_date: date = FIRST_DECISION, end_date: date = LAST_DECISION,
                 cutoff: Cutoff = "09:00", buffer_minutes: Buffer = 0, source: Source = "real"):
    validate(start_date); validate(end_date)
    if start_date > end_date:
        raise HTTPException(422, "start_date must not be after end_date")
    return cached_accuracy(source, start_date, end_date, cutoff, buffer_minutes)

@app.get("/api/export.csv")
def export_csv(start_date: date = FIRST_DECISION, end_date: date = LAST_DECISION,
               cutoff: Cutoff = "09:00", buffer_minutes: Buffer = 0, source: Source = "real",
               reveal_actual: bool = False):
    validate(start_date); validate(end_date)
    if start_date > end_date:
        raise HTTPException(422, "start_date must not be after end_date")
    store = load_store(source)
    output = io.StringIO()
    fields = ["data_mode", "snapshot_sha256", "decision_date", "delivery_date", "decision_time", "eligible_publish_before",
              "start_time", "settlement_period", "forecast_mw", "publish_time", "previous_forecast_mw", "revision_mw", "age_hours", "lead_hours", "status"]
    if reveal_actual:
        fields += ["actual_mw", "actual_publish_time", "error_mw"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for day in decision_dates(start_date, end_date):
        snap = cached_snapshot(source, day, cutoff, buffer_minutes, reveal_actual)
        for p in snap["points"]:
            writer.writerow({**p, "data_mode": store.metadata["mode"], "snapshot_sha256": store.metadata["snapshot_sha256"],
                             "decision_date": day.isoformat(), "delivery_date": snap["delivery_date"],
                             "decision_time": snap["decision_time"], "eligible_publish_before": snap["eligible_publish_before"]})
    return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="windward-{source}-{start_date}-{end_date}.csv"'})

# Register explicit API routes before the static files. Unknown API routes stay 404.
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")

@app.get("/", include_in_schema=False)
def index():
    return FileResponse(FRONTEND / "index.html")

@app.get("/api/docs", include_in_schema=False)
def api_explorer():
    return FileResponse(FRONTEND / "api.html")

@app.get("/review", include_in_schema=False)
def review():
    return FileResponse(FRONTEND / "review.html")
