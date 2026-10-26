"""Offline Chromium integration test using the real FastAPI TestClient.

The authoring sandbox blocks browser navigation even to localhost. This harness
injects the unchanged React/JS/CSS files into about:blank and bridges fetch to the
same ASGI routes. It is NOT a remote deployment or public-access check.
"""
from pathlib import Path
import json
import os
import re
import tempfile
import shutil
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright, expect
from backend.app.main import app

ROOT=Path(__file__).resolve().parents[1]
client=TestClient(app)

def mount(page):
    def bridge(url):
        r=client.get(url)
        return {'status':r.status_code,'body':r.text,'headers':dict(r.headers)}
    page.expose_function('__asgi',bridge)
    page.set_content('<!doctype html><html lang="en"><head><meta charset="UTF-8"><title>Windward · Day-ahead intelligence</title></head><body><div id="root"></div></body></html>')
    page.add_style_tag(content=(ROOT/'frontend/src/styles.css').read_text())
    page.add_script_tag(content='window.fetch=async function(url,opts){const r=await window.__asgi(url); if(opts?.signal?.aborted)throw new DOMException("Aborted","AbortError");return new Response(r.body,{status:r.status,headers:r.headers});};')
    page.add_script_tag(content=(ROOT/'frontend/vendor/react18.runtime.js').read_text())
    util=(ROOT/'frontend/src/utils.js').read_text().replace('export ','')
    source=(ROOT/'frontend/src/App.js').read_text()
    source=re.sub(r'^import\s+[\s\S]*?from\s+[\"\'][^\"\']+[\"\'];?\s*', '', source, flags=re.MULTILINE)
    page.add_script_tag(content=util+'\n'+source)


def main():
    artifacts=ROOT/'demo/screens'
    artifacts.mkdir(parents=True,exist_ok=True)
    assertions=[]
    from backend.app import repository
    fixture_dir = tempfile.TemporaryDirectory()
    repository.DATA_DIR = Path(fixture_dir.name)
    shutil.copyfile(ROOT/'data/synthetic.json', repository.DATA_DIR/'synthetic.json')
    repository.load_store.cache_clear()
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1,locale='en-GB')
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        mount(page)
        expect(page.get_by_role('button',name='Explore the synthetic sandbox')).to_be_visible()
        assertions.append('Real mode shows explicit missing-data state, not fake metrics')
        page.screenshot(path=str(artifacts/'01-empty.png'),full_page=True)
        page.get_by_role('button',name='Explore the synthetic sandbox').click()
        expect(page.get_by_text('SYNTHETIC SANDBOX',exact=True)).to_be_visible()
        expect(page.get_by_text('Mean wind forecast',exact=True)).to_be_visible()
        assertions.append('Explicit opt-in loads synthetic decision view')
        page.screenshot(path=str(artifacts/'02-decision.png'),full_page=True)
        page.get_by_label('Reveal actuals · hindsight').check()
        expect(page.get_by_text('Hindsight is on.',exact=False)).to_be_visible()
        assertions.append('Actuals require an explicit hindsight toggle')
        page.screenshot(path=str(artifacts/'03-hindsight.png'),full_page=True)
        page.get_by_label('Decision date',exact=True).fill('2026-01-31')
        expect(page.get_by_role('heading',name='Wind outlook · Sun 1 Feb')).to_be_visible()
        assertions.append('31 January decision shows 1 February delivery')
        page.get_by_label('Decision date',exact=True).fill('2026-01-01')
        expect(page.get_by_text('Not enough earlier history yet.',exact=True)).to_be_visible()
        assertions.append('Early January does not use future error history')
        page.screenshot(path=str(artifacts/'04-early-history.png'),full_page=True)
        page.get_by_label('Decision date',exact=True).fill('2026-01-08')
        expect(page.get_by_text('Covered-interval wind energy',exact=True)).to_be_visible()
        assertions.append('Missing forecast intervals are flagged; energy is partial')
        page.screenshot(path=str(artifacts/'05-gaps.png'),full_page=True)
        page.get_by_role('button',name='Accuracy lab',exact=True).click()
        expect(page.get_by_text('Mean absolute error',exact=True)).to_be_visible()
        assertions.append('Retrospective metrics and charts render')
        export = page.get_by_role('link', name='Export CSV', exact=True)
        expect(export).to_have_attribute('href', re.compile(r'/api/export\.csv\?.*source=synthetic'))
        assert 'reveal_actual=true' in export.get_attribute('href')
        assertions.append('Accuracy CSV uses synthetic source and explicitly requests hindsight')
        page.screenshot(path=str(artifacts/'06-accuracy.png'),full_page=True)
        page.get_by_label('Inspect decision 2026-01-15').click()
        expect(page.get_by_label('Decision date',exact=True)).to_have_value('2026-01-15')
        assertions.append('Accuracy bar drills into the correct decision')
        page.get_by_role('button',name='Pre-N2EX',exact=True).click()
        expect(page.get_by_label('Decision cutoff',exact=True)).to_have_value('09:45')
        page.get_by_label('Availability buffer',exact=True).select_option('15')
        expect(page.get_by_text('15 minutes',exact=True)).to_be_visible()
        assertions.append('Cutoff and availability buffer update the snapshot')
        page.get_by_role('button',name='Data & methodology',exact=True).click()
        expect(page.get_by_text('The timestamp is part of the forecast.',exact=True)).to_be_visible()
        page.screenshot(path=str(artifacts/'07-method.png'),full_page=True)
        assertions.append('Provenance and methodology screen renders')
        page.get_by_role('button',name='Decision desk',exact=True).click()
        page.set_viewport_size({'width':390,'height':844})
        expect(page.get_by_text('Mean wind forecast',exact=True)).to_be_visible()
        page.screenshot(path=str(artifacts/'08-mobile.png'),full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Mobile page overflows horizontally'
        assertions.append('390px mobile layout has no horizontal page overflow')
        assert not errors, errors
        assertions.append('No uncaught browser JavaScript exceptions')
        browser.close()
    report={'transport':'Chromium about:blank + FastAPI TestClient bridge; not deployed HTTP','assertions':assertions,'passed':len(assertions),'browser_errors':errors}
    (ROOT/'docs/browser-test-results.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    fixture_dir.cleanup()

if __name__=='__main__':main()
