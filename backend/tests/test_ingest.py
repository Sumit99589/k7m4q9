from datetime import date
import json
import httpx
import pytest
from backend.app.ingest import payload_rows, fetch, atomic_write

def test_payload_shapes_and_rejection():
    assert payload_rows([{'a':1}])==[{'a':1}]
    assert payload_rows({'data':[]})==[]
    with pytest.raises(ValueError):payload_rows({'error':'failure'})
    with pytest.raises(ValueError):payload_rows([42])

def test_explicit_publication_window_and_cache(tmp_path):
    requests=[]
    def handler(request):
        requests.append(request)
        return httpx.Response(200,json=[{'generation':1}],headers={'date':'Mon, 26 Oct 2026 00:00:00 GMT'})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        rows,meta=fetch(client,'WINDFOR',date(2026,1,1),tmp_path,False)
        assert requests[0].url.params['publishDateTimeFrom']=='2026-01-01T00:00:00Z'
        assert requests[0].url.params['publishDateTimeTo']=='2026-01-02T00:00:00Z'
        assert str(requests[0].url).startswith('https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream')
        _,cached=fetch(client,'WINDFOR',date(2026,1,1),tmp_path,False)
        assert len(requests)==1 and cached['cache_reused']
        assert len(meta['sha256'])==64

def test_retry_transient_failure(tmp_path,monkeypatch):
    monkeypatch.setattr('backend.app.ingest.time.sleep',lambda _:None)
    calls=[]
    def handler(request):
        calls.append(1)
        return httpx.Response(429 if len(calls)<3 else 200,json=[])
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetch(client,'WINDFOR',date(2026,1,1),tmp_path,False)
    assert len(calls)==3

def test_404_is_not_silently_interpreted_as_empty(tmp_path):
    with httpx.Client(transport=httpx.MockTransport(lambda req:httpx.Response(404,json={'error':'not found'}))) as c:
        with pytest.raises(httpx.HTTPStatusError):fetch(c,'WINDFOR',date(2026,1,1),tmp_path,False)
    assert not list(tmp_path.rglob('*.json'))

def test_invalid_json_payload_not_cached(tmp_path):
    with httpx.Client(transport=httpx.MockTransport(lambda req:httpx.Response(200,json={'error':'bad'}))) as c:
        with pytest.raises(ValueError):fetch(c,'WINDFOR',date(2026,1,1),tmp_path,False)
    assert not list(tmp_path.rglob('*.json'))

def test_corrupted_cache_fails_closed(tmp_path):
    with httpx.Client(transport=httpx.MockTransport(lambda req:httpx.Response(200,json=[]))) as c:
        fetch(c,'FUELHH',date(2026,1,1),tmp_path,False)
        (tmp_path/'FUELHH'/'2026-01-01.json').write_text('[{}]')
        with pytest.raises(ValueError,match='checksum'):fetch(c,'FUELHH',date(2026,1,1),tmp_path,False)

def test_atomic_replace(tmp_path):
    dest=tmp_path/'snapshot.json'
    atomic_write(dest,b'old');atomic_write(dest,b'new')
    assert dest.read_bytes()==b'new'
    assert not list(tmp_path.glob('*.tmp'))


def test_full_ingest_preserves_lineage_and_coverage(tmp_path, monkeypatch):
    import backend.app.ingest as module
    def fake_fetch(client, dataset, start, cache, refresh):
        row = {"startTime": "2026-01-02T00:00:00Z", "generation": 100,
               "publishTime": "2026-01-01T08:00:00Z"}
        if dataset == 'FUELHH':
            row.update(fuelType='WIND', generation=80, publishTime='2026-01-02T00:40:00Z')
        return [row, {**row, 'publishTime': '2026-02-05T00:00:00Z'},
                {**row, 'publishTime': '2025-12-28T00:00:00Z'}], {"dataset": dataset, "url": "mock://fixture", "sha256": "fixture"}
    monkeypatch.setattr(module, 'fetch', fake_fetch)
    output = tmp_path / 'snapshot.json'
    meta = module.ingest(output, tmp_path / 'raw')
    saved = json.loads(output.read_text())
    assert meta['mode'] == 'real'  # Mock adapter path only; no network or real observation.
    assert len(saved['forecasts']) == 1 and len(saved['actuals']) == 1
    assert meta['default_cutoff_coverage'][0]['matched_intervals'] == 1
    assert meta['ingest_quality']['WINDFOR']['exact_duplicates'] > 0
    assert len(meta['request_manifest']) > 60
    assert meta['scope_exclusions'] == {'WINDFOR': 2, 'FUELHH': 2}


def test_full_ingest_failure_does_not_replace_previous_snapshot(tmp_path, monkeypatch):
    import backend.app.ingest as module
    monkeypatch.setattr(module, 'fetch', lambda *args: ([], {'dataset': 'fixture'}))
    output = tmp_path / 'snapshot.json'
    output.write_text('previous snapshot')
    with pytest.raises(ValueError, match='No usable'):
        module.ingest(output, tmp_path / 'raw')
    assert output.read_text() == 'previous snapshot'
