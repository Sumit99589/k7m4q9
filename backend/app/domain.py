"""Point-in-time wind analysis. Pure functions; no HTTP, database or UI dependencies."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
import math
from statistics import mean
from typing import Any, Iterable
from zoneinfo import ZoneInfo

UTC = timezone.utc
LONDON = ZoneInfo("Europe/London")
FIRST_DECISION = date(2026, 1, 1)
LAST_DECISION = date(2026, 1, 31)


def timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("A UTC offset or Z is required; naive timestamps are not accepted")
    return parsed.astimezone(UTC)


def iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z") if value else None


def decision_time(day: date, cutoff: str) -> datetime:
    return datetime.combine(day, time.fromisoformat(cutoff), LONDON).astimezone(UTC)


def slots(day: date) -> list[datetime]:
    """UTC half-hours for a London civil delivery day; 46/48/50 at DST boundaries."""
    start = datetime.combine(day, time(), LONDON).astimezone(UTC)
    end = datetime.combine(day + timedelta(days=1), time(), LONDON).astimezone(UTC)
    return [start + timedelta(minutes=30 * i) for i in range(int((end-start).total_seconds()/1800))]


def decision_dates(start: date = FIRST_DECISION, end: date = LAST_DECISION) -> list[date]:
    if start < FIRST_DECISION or end > LAST_DECISION or start > end:
        raise ValueError("Decision dates must be an ordered range within January 2026")
    return [start + timedelta(days=i) for i in range((end-start).days+1)]


@dataclass(frozen=True)
class Record:
    target: datetime
    published: datetime | None
    mw: float
    source_id: str


def normalize(rows: Iterable[dict[str, Any]], dataset: str) -> tuple[list[Record], dict[str, int]]:
    """Filter WIND, validate, collapse exact duplicates, quarantine ambiguous keys.

    A conflicting (target,publish) key is never resolved by API response order.
    Actual records without publishTime can be scored ex post but not used for
    point-in-time calibration. Negative operational readings are retained.
    """
    stats = {"input": 0, "non_wind": 0, "invalid": 0, "exact_duplicates": 0,
             "conflicting_keys": 0, "missing_publish_time": 0, "negative_values": 0}
    groups: dict[tuple, list[Record]] = defaultdict(list)
    for raw in rows:
        stats["input"] += 1
        if dataset == "FUELHH" and raw.get("fuelType") != "WIND":
            stats["non_wind"] += 1
            continue
        try:
            target = timestamp(str(raw["startTime"]))
            published = timestamp(str(raw["publishTime"])) if raw.get("publishTime") else None
            if dataset == "WINDFOR" and published is None:
                raise ValueError("Forecast publication time is required")
            value = raw["generation"]
            if isinstance(value, bool) or value is None:
                raise ValueError("Generation must be finite")
            value = float(value)
            if not math.isfinite(value) or target.second or target.microsecond or target.minute not in (0, 30):
                raise ValueError("Invalid value or non-half-hour target")
            if published is None:
                stats["missing_publish_time"] += 1
            if value < 0:
                stats["negative_values"] += 1
            groups[(target, published)].append(Record(target, published, value, str(raw.get("id", ""))))
        except (KeyError, ValueError, TypeError, OverflowError):
            stats["invalid"] += 1
    result = []
    for group in groups.values():
        if len({r.mw for r in group}) > 1:
            stats["conflicting_keys"] += 1
            continue
        stats["exact_duplicates"] += len(group)-1
        result.append(sorted(group, key=lambda r: r.source_id)[0])
    stats["accepted"] = len(result)
    return sorted(result, key=lambda r: (r.target, r.published or datetime.min.replace(tzinfo=UTC))), stats


class Store:
    def __init__(self, forecast: list[Record], actual: list[Record], metadata: dict[str, Any]):
        self.forecast: dict[datetime, list[Record]] = defaultdict(list)
        self.actual: dict[datetime, list[Record]] = defaultdict(list)
        for r in forecast:
            self.forecast[r.target].append(r)
        for r in actual:
            self.actual[r.target].append(r)
        for index in [self.forecast, self.actual]:
            for versions in index.values():
                versions.sort(key=lambda r: r.published or datetime.min.replace(tzinfo=UTC))
        self.metadata = metadata

    def get_actual(self, target: datetime, available_by: datetime | None = None) -> Record | None:
        candidates = self.actual.get(target, [])
        if available_by is not None:
            if target + timedelta(minutes=30) > available_by:
                return None
            candidates = [r for r in candidates if r.published and r.published <= available_by]
        return candidates[-1] if candidates else None

    def day(self, day: date, cutoff: str = "09:00", buffer_minutes: int = 0,
            actual_available_by: datetime | None = None) -> list[dict[str, Any]]:
        decision = decision_time(day, cutoff)
        eligible_by = decision - timedelta(minutes=buffer_minutes)
        points = []
        for i, target in enumerate(slots(day + timedelta(days=1))):
            eligible = [r for r in self.forecast.get(target, []) if r.published and r.published <= eligible_by]
            forecast = eligible[-1] if eligible else None
            previous = eligible[-2] if len(eligible) > 1 else None
            actual = self.get_actual(target, actual_available_by)
            error = forecast.mw-actual.mw if forecast and actual else None
            points.append({
                "start_time": iso(target), "settlement_period": i+1,
                "forecast_mw": forecast.mw if forecast else None,
                "actual_mw": actual.mw if actual else None,
                "publish_time": iso(forecast.published) if forecast else None,
                "actual_publish_time": iso(actual.published) if actual else None,
                "previous_forecast_mw": previous.mw if previous else None,
                "revision_mw": forecast.mw-previous.mw if forecast and previous else None,
                "error_mw": error,
                "lead_hours": round((target-forecast.published).total_seconds()/3600, 3) if forecast else None,
                "age_hours": round((decision-forecast.published).total_seconds()/3600, 3) if forecast else None,
                "status": "matched" if forecast and actual else "missing_forecast" if not forecast else "missing_actual",
            })
        return points


def quantile(values: list[float], p: float) -> float | None:
    """R7/linear empirical quantile. Not a calibrated prediction interval."""
    if not values:
        return None
    values = sorted(values)
    index = (len(values)-1)*p
    lower, upper = math.floor(index), math.ceil(index)
    return values[lower] + (values[upper]-values[lower])*(index-lower)


def rounded(value: float | None, digits: int = 2) -> float | None:
    return round(value, digits) if value is not None else None


def metrics(points: list[dict[str, Any]]) -> dict[str, Any]:
    matched = [p for p in points if p["forecast_mw"] is not None and p["actual_mw"] is not None]
    errors = [p["forecast_mw"]-p["actual_mw"] for p in matched]
    absolute = [abs(e) for e in errors]
    denominator = sum(abs(p["actual_mw"]) for p in matched)
    expected = len(points)
    return {
        "expected_intervals": expected, "forecast_intervals": sum(p["forecast_mw"] is not None for p in points),
        "actual_intervals": sum(p["actual_mw"] is not None for p in points), "matched_intervals": len(matched),
        "coverage_pct": rounded(100*len(matched)/expected) if expected else None,
        "mae_mw": rounded(mean(absolute)) if errors else None,
        "rmse_mw": rounded(math.sqrt(mean(e*e for e in errors))) if errors else None,
        "bias_mw": rounded(mean(errors)) if errors else None,
        "wape_pct": rounded(100*sum(absolute)/denominator) if denominator else None,
        "p90_abs_mw": rounded(quantile(absolute, .9)),
        "p90_shortfall_mw": rounded(quantile([max(e, 0) for e in errors], .9)),
        "overforecast_pct": rounded(100*sum(e>0 for e in errors)/len(errors)) if errors else None,
        "net_error_mwh": rounded(sum(errors)*.5) if errors else None,
        "absolute_error_mwh": rounded(sum(absolute)*.5) if errors else None,
        "forecast_energy_mwh_covered": rounded(sum(p["forecast_mw"]*.5 for p in points if p["forecast_mw"] is not None)) if any(p["forecast_mw"] is not None for p in points) else None,
        "forecast_mean_mw": rounded(mean([p["forecast_mw"] for p in points if p["forecast_mw"] is not None])) if any(p["forecast_mw"] is not None for p in points) else None,
    }


def historical_risk(store: Store, day: date, cutoff: str, buffer_minutes: int) -> dict[str, Any]:
    """Expanding-window residuals using only previous decisions and known outturns.

    Restricting actual publication times is essential: simply filtering delivery
    dates still leaks late actual revisions. No pre-January forecast errors used.
    """
    available_by = decision_time(day, cutoff) - timedelta(minutes=buffer_minutes)
    pairs, days_used = [], set()
    for prior in decision_dates():
        if prior >= day:
            break
        for point in store.day(prior, cutoff, buffer_minutes, actual_available_by=available_by):
            if point["error_mw"] is not None:
                pairs.append(point)
                days_used.add(prior.isoformat())
    enough = len(days_used) >= 7 and len(pairs) >= 168
    errors = [p["error_mw"] for p in pairs]
    residuals = [-e for e in errors]
    return {
        "status": "available" if enough else "insufficient_history",
        "sample_intervals": len(pairs), "sample_decision_days": len(days_used),
        "minimum_days": 7, "minimum_intervals": 168,
        "training_decision_start": min(days_used) if days_used else None,
        "training_decision_end": max(days_used) if days_used else None,
        "actuals_available_by": iso(available_by),
        "p10_residual_mw": rounded(quantile(residuals, .1)) if enough else None,
        "p90_residual_mw": rounded(quantile(residuals, .9)) if enough else None,
        "p90_shortfall_mw": rounded(quantile([max(e, 0) for e in errors], .9)) if enough else None,
        "mae_mw": rounded(mean([abs(e) for e in errors])) if enough else None,
        "description": "Prior-only pooled empirical 10th–90th residual range; exploratory, not calibrated probability or a trading recommendation.",
    }


def snapshot(store: Store, day: date, cutoff: str, buffer_minutes: int, reveal_actual: bool = False) -> dict[str, Any]:
    points = store.day(day, cutoff, buffer_minutes)
    risk = historical_risk(store, day, cutoff, buffer_minutes)
    for p in points:
        f = p["forecast_mw"]
        p["range_low_mw"] = rounded(f+risk["p10_residual_mw"]) if f is not None and risk["status"] == "available" else None
        p["range_high_mw"] = rounded(f+risk["p90_residual_mw"]) if f is not None and risk["status"] == "available" else None
    pubs = sorted({p["publish_time"] for p in points if p["publish_time"]})
    ages = [p["age_hours"] for p in points if p["age_hours"] is not None]
    summary = metrics(points)
    forecast_only_summary = {k:summary[k] for k in ["expected_intervals", "forecast_intervals", "forecast_energy_mwh_covered", "forecast_mean_mw"]}
    warnings = []
    if summary["forecast_intervals"] < len(points):
        warnings.append("Forecast coverage is incomplete. Missing half-hours are not interpolated or treated as zero; energy is for covered intervals only.")
    if ages and max(ages) > 12:
        warnings.append("At least one selected forecast was over 12 hours old at the decision cutoff (pilot freshness rule, not a market standard).")
    if len(pubs) > 1:
        warnings.append("This curve combines publication vintages. Selection is latest eligible per target, not a single forecast run.")
    if store.metadata.get("mode") == "synthetic":
        warnings.insert(0, "SYNTHETIC TEST DATA. These numbers are not Elexon observations or January 2026 findings.")
    if not reveal_actual:
        for p in points:
            for key in ["actual_mw", "actual_publish_time", "error_mw"]:
                p[key] = None
            p["status"] = "forecast_available" if p["forecast_mw"] is not None else "missing_forecast"
    return {
        "decision_date": day.isoformat(), "delivery_date": (day+timedelta(days=1)).isoformat(),
        "cutoff_local": cutoff, "decision_time": iso(decision_time(day, cutoff)),
        "eligible_publish_before": iso(decision_time(day, cutoff)-timedelta(minutes=buffer_minutes)),
        "availability_buffer_minutes": buffer_minutes, "timezone": "Europe/London",
        "reveal_actual": reveal_actual, "summary": summary if reveal_actual else forecast_only_summary,
        "publication_count": len(pubs), "latest_publish_time": pubs[-1] if pubs else None,
        "oldest_publish_time": pubs[0] if pubs else None,
        "max_forecast_age_hours": max(ages) if ages else None,
        "risk": risk, "warnings": warnings, "points": points, "provenance": store.metadata,
    }


def accuracy(store: Store, start: date, end: date, cutoff: str, buffer_minutes: int) -> dict[str, Any]:
    all_points, daily = [], []
    for day in decision_dates(start, end):
        points = store.day(day, cutoff, buffer_minutes)
        for p in points:
            p["decision_date"] = day.isoformat()
        all_points.extend(points)
        daily.append({"decision_date": day.isoformat(), "delivery_date": (day+timedelta(days=1)).isoformat(), **metrics(points)})
    hourly = []
    for h in range(24):
        group = [p for p in all_points if timestamp(p["start_time"]).astimezone(LONDON).hour == h]
        hourly.append({"hour": h, **metrics(group)})
    horizon = []
    for lower, upper in [(0,24), (24,36), (36,48), (48,96), (96, float("inf"))]:
        group = [p for p in all_points if p["lead_hours"] is not None and lower <= p["lead_hours"] < upper]
        horizon.append({"label": f"{lower}–{upper}h" if math.isfinite(upper) else "96h+", **metrics(group)})
    matched = [p for p in all_points if p["error_mw"] is not None]
    errors = [p["error_mw"] for p in matched]
    max_abs = max((abs(e) for e in errors), default=1000)
    step = max(250, math.ceil(max_abs/6/250)*250)
    histogram = []
    for i in range(-6,6):
        low, high = i*step, (i+1)*step
        histogram.append({"low": low, "high": high, "count": sum(low <= e < high or (i==5 and e==high) for e in errors)})
    return {"start_date": start.isoformat(), "end_date": end.isoformat(), "cutoff_local": cutoff,
            "availability_buffer_minutes": buffer_minutes, "summary": metrics(all_points),
            "daily": daily, "hourly": hourly, "horizon": horizon, "histogram": histogram,
            "worst_intervals": sorted(matched, key=lambda p: abs(p["error_mw"]), reverse=True)[:10],
            "provenance": store.metadata,
            "interpretation": "Ex-post score of decision-time forecasts against latest actual revision in this snapshot. Positive error = forecast exceeds actual. Not a trading backtest."}
