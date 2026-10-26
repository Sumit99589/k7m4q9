"""Load an immutable, checksummed snapshot. Real and synthetic data never mix."""
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
from .domain import Store, normalize

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("WIND_DATA_DIR", str(ROOT / "data")))

class DatasetUnavailable(Exception):
    pass

@lru_cache(maxsize=2)
def load_store(source: str = "real") -> Store:
    name = "snapshot.json" if source == "real" else "synthetic.json"
    file = DATA_DIR / name
    if not file.exists():
        raise DatasetUnavailable("No real Elexon snapshot is installed. Run python -m backend.app.ingest; synthetic mode is available only by explicit selection.")
    try:
        content = file.read_bytes()
        payload = json.loads(content)
        meta = dict(payload["metadata"])
        if not isinstance(payload["forecasts"], list) or not isinstance(payload["actuals"], list):
            raise ValueError("Record collections must be arrays")
        if any(not isinstance(r, dict) for rows in [payload["forecasts"], payload["actuals"]] for r in rows):
            raise ValueError("Records must be objects")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise DatasetUnavailable("Snapshot is unreadable or invalid; re-run the importer and restart the application") from exc
    if source == "real" and meta.get("mode") != "real":
        raise DatasetUnavailable("Refusing to serve non-real data as Elexon observations")
    if source == "synthetic" and meta.get("mode") != "synthetic":
        raise DatasetUnavailable("Synthetic source has an unexpected provenance mode")
    forecast, fq = normalize(payload["forecasts"], "WINDFOR")
    actual, aq = normalize(payload["actuals"], "FUELHH")
    meta.update({"snapshot_sha256": hashlib.sha256(content).hexdigest(),
                 "forecast_quality": fq, "actual_quality": aq})
    return Store(forecast, actual, meta)
