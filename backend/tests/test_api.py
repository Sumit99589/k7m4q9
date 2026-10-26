import csv
import io
from fastapi.testclient import TestClient
import pytest
from backend.app.main import app

client=TestClient(app)

def test_health_and_frontend():
    assert client.get('/api/health').json()['status']=='ok'
    response=client.get('/')
    assert response.status_code==200 and 'Windward' in response.text
    assert 'frame-ancestors' in response.headers['Content-Security-Policy']

def test_real_dataset_is_never_a_synthetic_fallback():
    from backend.app.repository import DATA_DIR
    if not (DATA_DIR/'snapshot.json').exists():
        r=client.get('/api/snapshot')
        assert r.status_code==503 and r.json()['code']=='DATASET_UNAVAILABLE'

@pytest.mark.parametrize('query',['decision_date=2026-02-01','decision_date=2025-12-31','cutoff=25:00','cutoff=9am','buffer_minutes=-1','buffer_minutes=61','source=unknown'])
def test_rejects_invalid_inputs(query):
    assert client.get('/api/snapshot?'+query).status_code==422

def test_rejects_inverted_accuracy_range():
    assert client.get('/api/accuracy?source=synthetic&start_date=2026-01-20&end_date=2026-01-01').status_code==422

def test_openapi_and_unknown_api():
    assert client.get('/api/openapi.json').status_code==200
    assert client.get('/api/does-not-exist').status_code==404

def test_snapshot_schema_and_cutoff_safety():
    d=client.get('/api/snapshot?source=synthetic&decision_date=2026-01-31').json()
    assert d['delivery_date']=='2026-02-01'
    assert len(d['points'])==48
    assert all(p['actual_mw'] is None for p in d['points'])
    assert all(p['publish_time']<=d['eligible_publish_before'] for p in d['points'] if p['publish_time'])

def test_csv_has_lineage_and_no_actuals_by_default():
    r=client.get('/api/export.csv?source=synthetic&start_date=2026-01-15&end_date=2026-01-15')
    assert r.status_code==200 and 'attachment' in r.headers['content-disposition']
    rows=list(csv.DictReader(io.StringIO(r.text)))
    assert len(rows)==48 and rows[0]['data_mode']=='synthetic'
    assert len(rows[0]['snapshot_sha256'])==64
    assert 'actual_mw' not in rows[0]
    assert rows[0]['decision_time']=='2026-01-15T09:00:00Z'

def test_csv_hindsight_is_explicit():
    r=client.get('/api/export.csv?source=synthetic&reveal_actual=true')
    rows=list(csv.DictReader(io.StringIO(r.text)))
    assert len(rows)==1488 and 'actual_mw' in rows[0]


def test_metadata_declares_synthetic_origin():
    assert client.get('/api/meta?source=synthetic').json()['provenance']['mode']=='synthetic'


def test_review_and_api_explorer_have_local_assets():
    for path in ["/review", "/api/docs"]:
        response = client.get(path)
        assert response.status_code == 200
        assert '/static/review.css' in response.text
        assert 'cdn.jsdelivr.net' not in response.text
    assert client.get('/static/api.js').status_code == 200


def test_corrupt_snapshot_fails_closed(tmp_path, monkeypatch):
    from backend.app import repository
    monkeypatch.setattr(repository, 'DATA_DIR', tmp_path)
    repository.load_store.cache_clear()
    (tmp_path / 'snapshot.json').write_text('{broken json')
    response = client.get('/api/meta?source=real')
    assert response.status_code == 503
    assert response.json()['code'] == 'DATASET_UNAVAILABLE'
    repository.load_store.cache_clear()
