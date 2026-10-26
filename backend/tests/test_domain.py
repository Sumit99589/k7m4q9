from datetime import date, timedelta
import math
import pytest
from backend.app.domain import (timestamp, iso, slots, decision_time, decision_dates, normalize,
                                Record, Store, metrics, quantile, snapshot, historical_risk, accuracy)

T = timestamp

def record(value, published='2026-01-01T08:00:00Z', target='2026-01-02T00:00:00Z'):
    return Record(T(target), T(published) if published else None, value, '')

def store(fc=(),ac=()):
    return Store(list(fc), list(ac), {'mode':'synthetic'})

def point(f,a):
    return {'forecast_mw':f,'actual_mw':a}

def test_future_forecast_cannot_replace_eligible_forecast():
    s=store([record(100),record(900,'2026-01-01T09:01:00Z')],[record(80,'2026-01-02T00:40:00Z')])
    assert s.day(date(2026,1,1))[0]['forecast_mw']==100

def test_cutoff_equality_is_eligible_but_buffer_excludes_it():
    s=store([record(90),record(100,'2026-01-01T09:00:00Z')])
    assert s.day(date(2026,1,1))[0]['forecast_mw']==100
    assert s.day(date(2026,1,1),buffer_minutes=1)[0]['forecast_mw']==90

def test_latest_selected_separately_per_target():
    s=store([record(100),record(150,'2026-01-01T08:30:00Z'),record(200,'2026-01-01T07:00:00Z','2026-01-02T00:30:00Z')])
    result=snapshot(s,date(2026,1,1),'09:00',0)
    assert [p['forecast_mw'] for p in result['points'][:2]]==[150,200]
    assert result['publication_count']==2
    assert result['points'][0]['revision_mw']==50

def test_missing_forecast_is_none_not_zero():
    result=store().day(date(2026,1,1))
    assert len(result)==48 and all(p['forecast_mw'] is None for p in result)
    assert metrics(result)['mae_mw'] is None
    assert metrics(result)['forecast_energy_mwh_covered'] is None

def test_future_outturn_revision_excluded_from_asof():
    s=store([record(100)],[record(70,'2026-01-02T01:00:00Z'),record(50,'2026-01-05T10:00:00Z')])
    assert s.get_actual(T('2026-01-02T00:00:00Z')).mw==50
    assert s.get_actual(T('2026-01-02T00:00:00Z'),T('2026-01-03T09:00:00Z')).mw==70

def test_outturn_without_publication_cannot_calibrate():
    s=store([], [record(70,None)])
    assert s.get_actual(T('2026-01-02T00:00:00Z')).mw==70
    assert s.get_actual(T('2026-01-02T00:00:00Z'),T('2026-01-03T09:00:00Z')) is None

def test_unfinished_interval_cannot_calibrate():
    s=store([], [record(70,'2026-01-02T00:00:00Z')])
    assert s.get_actual(T('2026-01-02T00:00:00Z'),T('2026-01-02T00:15:00Z')) is None

def test_hidden_actuals_not_sent_to_client_or_summary():
    result=snapshot(store([record(100)],[record(80)]),date(2026,1,1),'09:00',0)
    assert result['points'][0]['actual_mw'] is None
    assert result['points'][0]['error_mw'] is None
    assert 'mae_mw' not in result['summary']
    assert result['points'][0]['status']=='forecast_available'

def test_error_sign_and_mwh_conversion():
    m=metrics([point(100,80),point(60,100)])
    assert m['bias_mw']==-10
    assert m['mae_mw']==30
    assert m['rmse_mw']==round(math.sqrt(1000),2)
    assert m['wape_pct']==33.33
    assert m['net_error_mwh']==-10
    assert m['forecast_energy_mwh_covered']==80

def test_zero_actual_denominator_is_not_infinite():
    m=metrics([point(100,0),point(0,0)])
    assert m['wape_pct'] is None
    assert m['mae_mw']==50

def test_zero_forecast_and_actual_are_valid():
    assert metrics([point(0,0)])['matched_intervals']==1
    assert metrics([point(0,0)])['forecast_energy_mwh_covered']==0

def test_missing_points_do_not_enter_metrics():
    m=metrics([point(100,90),point(None,70),point(120,None)])
    assert m['matched_intervals']==1 and m['expected_intervals']==3
    assert m['mae_mw']==10 and m['coverage_pct']==33.33

def test_quantile_interpolation_and_zero_shortfall():
    assert quantile([0,10],.9)==9
    assert quantile([], .9) is None
    assert metrics([point(0,10),point(10,20)])['p90_shortfall_mw']==0

def test_january_boundaries_include_february_delivery():
    assert len(decision_dates())==31
    result=store().day(date(2026,1,31))
    assert result[0]['start_time']=='2026-02-01T00:00:00Z'
    assert result[-1]['start_time']=='2026-02-01T23:30:00Z'

@pytest.mark.parametrize('start,end',[(date(2025,12,31),date(2026,1,1)),(date(2026,1,31),date(2026,2,1)),(date(2026,1,3),date(2026,1,2))])
def test_invalid_decision_ranges(start,end):
    with pytest.raises(ValueError):decision_dates(start,end)

def test_london_dst_grid_and_cutoff():
    assert len(slots(date(2026,3,29)))==46
    assert len(slots(date(2026,10,25)))==50
    assert iso(decision_time(date(2026,7,1),'09:00'))=='2026-07-01T08:00:00Z'

def test_utc_offset_normalization_and_naive_rejection():
    assert T('2026-01-02T01:00:00+01:00')==T('2026-01-02T00:00:00Z')
    with pytest.raises(ValueError):T('2026-01-02T00:00:00')

def test_normalize_filters_other_fuels_and_rejects_bad_values():
    base={'startTime':'2026-01-02T00:00:00Z','generation':1,'fuelType':'WIND','publishTime':'2026-01-02T01:00:00Z'}
    records,q=normalize([base,{**base,'fuelType':'CCGT'},{**base,'generation':float('nan')},{**base,'generation':True},{**base,'startTime':'2026-01-02T00:15:00Z'}], 'FUELHH')
    assert len(records)==1 and q['non_wind']==1 and q['invalid']==3

def test_identical_duplicates_collapsed_conflicts_quarantined():
    row={'startTime':'2026-01-02T00:00:00Z','publishTime':'2026-01-01T08:00:00Z','generation':100}
    records,q=normalize([row,row], 'WINDFOR')
    assert len(records)==1 and q['exact_duplicates']==1
    records,q=normalize([row,{**row,'generation':200}], 'WINDFOR')
    assert not records and q['conflicting_keys']==1

def test_missing_forecast_publish_rejected():
    rows,q=normalize([{'startTime':'2026-01-02T00:00:00Z','generation':100}],'WINDFOR')
    assert not rows and q['invalid']==1

def test_negative_operational_readings_retained_and_flagged():
    rows,q=normalize([{'startTime':'2026-01-02T00:00:00Z','publishTime':'2026-01-01T08:00:00Z','generation':-1}],'WINDFOR')
    assert rows[0].mw==-1 and q['negative_values']==1

def test_early_month_risk_is_not_fitted_to_full_month():
    from backend.app.repository import load_store
    s=load_store('synthetic')
    risk=historical_risk(s,date(2026,1,1),'09:00',0)
    assert risk['status']=='insufficient_history' and risk['sample_intervals']==0
    risk=historical_risk(s,date(2026,1,15),'09:00',0)
    assert risk['status']=='available' and risk['training_decision_end']<'2026-01-15'

def test_future_forecasts_and_actuals_do_not_change_prior_risk():
    from backend.app.repository import load_store
    original=load_store('synthetic')
    fc=[r for values in original.forecast.values() for r in values]
    ac=[r for values in original.actual.values() for r in values]
    future=T('2026-01-20T00:00:00Z')
    poisoned=[Record(r.target,future,1e9,'poison') for r in ac]
    altered=Store(fc,ac+poisoned,{'mode':'synthetic'})
    assert historical_risk(original,date(2026,1,15),'09:00',0)==historical_risk(altered,date(2026,1,15),'09:00',0)

def test_monthly_metrics_are_weighted_by_pairs_not_mean_of_daily_maes():
    from backend.app.repository import load_store
    s=load_store('synthetic')
    result=accuracy(s,date(2026,1,1),date(2026,1,31),'09:00',0)
    assert result['summary']['expected_intervals']==1488
    assert result['summary']['matched_intervals']==1486
    assert sum(b['count'] for b in result['histogram'])==1486
    points=[p for d in decision_dates() for p in s.day(d)]
    assert result['summary']==metrics(points)

def test_hourly_forecast_not_silently_expanded():
    s=store([record(100),record(200,target='2026-01-02T01:00:00Z')])
    result=s.day(date(2026,1,1))
    assert result[1]['forecast_mw'] is None
    assert metrics(result)['forecast_energy_mwh_covered']==150
