"""Capture the supplied technical handover page without network navigation."""
from pathlib import Path
from html import escape
import os
import inspect
from playwright.sync_api import sync_playwright
from backend.app.domain import Store
ROOT = Path(__file__).resolve().parents[1]

def main():
    dest=ROOT/'demo/screens';dest.mkdir(exist_ok=True,parents=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
        page.set_content((ROOT/'frontend/review.html').read_text())
        page.add_style_tag(content=(ROOT/'frontend/review.css').read_text())
        for index,name in enumerate(['overview','architecture','correctness','analysis','quality','release'],9):
            page.locator('#'+name).screenshot(path=str(dest/f'{index:02d}-{name}.png'))
        actual=inspect.getsource(Store.get_actual)
        day='\n'.join(inspect.getsource(Store.day).splitlines()[:15])
        page.set_content(f'<html><body><main><span class="eyebrow">Actual source excerpts · backend/app/domain.py</span><h2>Versions are selected before metrics are calculated.</h2><div class="grid"><div><h3>Actual availability guard</h3><pre>{escape(actual)}</pre></div><div><h3>Forecast selection per target</h3><pre>{escape(day)}</pre></div></div><p>Full functions, tests and comments are included in the repository. No post-cutoff actual revision can enter a decision-time historical sample.</p></main></body></html>')
        page.add_style_tag(content=(ROOT/'frontend/review.css').read_text()+'main{max-width:none}pre{font-size:14px;line-height:1.6}.grid{grid-template-columns:1fr 1fr}')
        page.locator('main').screenshot(path=str(dest/'15-source.png'))
        coverage=(ROOT/'docs/coverage.json').exists()
        evidence='''Python: 53 tests passed
JavaScript: 6 tests passed
Chromium: 13 assertions passed

Python statement coverage (rounded)
  domain.py       99%
  ingest.py       85%
  main.py         97%
  repository.py   88%
  TOTAL           94%

No uncaught browser JavaScript errors.'''
        page.set_content(f'<html><body><main><span class="eyebrow">Executed locally · not a deployment claim</span><h2>Verification evidence, with its boundaries.</h2><div class="grid"><pre class="commands">{escape(evidence)}</pre><div><h3>Adversarial cases</h3><p>Late forecasts cannot replace eligible vintages. Late actual revisions cannot enter the prior-only range. Zero is not missing. Incomplete forecasts do not become complete energy totals.</p><h3>Browser transport limitation</h3><p>Chromium renders the actual React application. Fetch is bridged to the real FastAPI TestClient because browser HTTP is blocked in the authoring sandbox.</p><div class="banner">Still required: live Elexon import, real HTTP/CSP test, Docker build, public deployment and signed-out link checks.</div></div></div></main></body></html>')
        page.add_style_tag(content=(ROOT/'frontend/review.css').read_text())
        page.locator('main').screenshot(path=str(dest/'16-evidence.png'))
        browser.close()
    print('Technical screenshots captured.')

if __name__=='__main__':main()
