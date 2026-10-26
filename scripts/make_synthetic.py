"""Deterministic UI/test fixture, never evidence about the electricity market."""
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import random

rng = random.Random(20260126)
forecasts, actuals = [], []
for d in range(31):
    delivery = datetime(2026,1,2,tzinfo=timezone.utc)+timedelta(days=d)
    base = 10100+5200*math.sin(d*.49)+1400*math.cos(d*.93)
    bias = 450+600*math.sin(d*.82)
    for h in range(48):
        target = delivery+timedelta(minutes=30*h)
        actual = round(max(400, base+1800*math.sin(h/48*2*math.pi+d*.3)+rng.gauss(0,90)),1)
        ts = target.isoformat().replace('+00:00','Z')
        # Include first publication and a later correction to exercise as-of actual handling.
        actuals.append({"startTime":ts,"publishTime":(target+timedelta(minutes=40)).isoformat(),"generation":actual+25,"fuelType":"WIND"})
        actuals.append({"startTime":ts,"publishTime":(target+timedelta(days=2)).isoformat(),"generation":actual,"fuelType":"WIND"})
        for hours_before, scale in [(33,1.7),(23.5,1.4),(20.5,1.25),(17.5,1),(14.5,.8),(11.5,.7),(5.5,.5),(-3.5,.25)]:
            # Hours are relative to delivery midnight, not each target.
            published = delivery-timedelta(hours=hours_before)
            error = bias*scale+900*scale*math.sin(h*.13+d)+rng.gauss(0,160*scale)
            forecast = round(max(0,actual+error),1)
            # Deliberate missing forecast intervals: assert gaps are visible rather than imputed.
            if d==7 and h in (20,21):
                continue
            forecasts.append({"startTime":ts,"publishTime":published.isoformat(),"generation":forecast})
metadata = {"mode":"synthetic", "source":"Deterministic mathematical test fixture, seed 20260126. NOT Elexon data.",
            "retrieved_at":None,"fixture_version":"1", "decision_scope":"2026-01-01 through 2026-01-31",
            "delivery_scope":"2026-01-02 through 2026-02-01", "timezone":"Europe/London",
            "actual_revision_policy":"Fabricated first readings and later revisions for testing only",
            "availability_assumption":"Synthetic publish times; no empirical market availability claim",
            "alignment":"Exact half-hour target; two deliberately missing forecasts",
            "notice":"Do not submit these metrics as January 2026 pilot findings."}
p=Path(__file__).resolve().parents[1]/"data"/"synthetic.json"
p.write_text(json.dumps({"metadata":metadata,"forecasts":forecasts,"actuals":actuals},separators=(',',':')))
print(f"Wrote explicitly synthetic fixture: {len(forecasts)} forecasts, {len(actuals)} actual revisions")
