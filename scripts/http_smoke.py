"""Real HTTP/browser release check. Not the offline ASGI-bridge test.

Run on a machine that permits browser HTTP navigation, after starting the server.
"""
import argparse
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    args = parser.parse_args()
    base = args.base_url.rstrip('/')
    with sync_playwright() as p:
        launch = {'headless': True}
        if os.environ.get('CHROMIUM_PATH'):
            launch['executable_path'] = os.environ['CHROMIUM_PATH']
        browser = p.chromium.launch(**launch)
        context = browser.new_context(locale='en-GB', viewport={'width':1440,'height':1000})
        page = context.new_page()
        errors=[]
        page.on('pageerror', lambda error: errors.append(str(error)))
        response = page.goto(base, wait_until='networkidle')
        assert response and response.status == 200, 'Homepage is not publicly reachable'
        assert "script-src 'self'" in response.headers.get('content-security-policy', ''), 'CSP is missing'
        page.get_by_label('Dataset', exact=True).select_option('synthetic')
        expect(page.get_by_text('Mean wind forecast', exact=True)).to_be_visible()
        page.get_by_label('Reveal actuals · hindsight').check()
        expect(page.get_by_text('Hindsight is on.', exact=False)).to_be_visible()
        page.get_by_role('button', name='Accuracy lab', exact=True).click()
        expect(page.get_by_text('Mean absolute error', exact=True)).to_be_visible()
        with page.expect_download() as event:
            page.get_by_role('link', name='Export CSV', exact=True).click()
        download=event.value
        assert download.failure() is None
        content=Path(download.path()).read_text()
        assert 'snapshot_sha256' in content and 'actual_mw' in content
        page.goto(base + '/api/docs', wait_until='networkidle')
        page.get_by_role('button', name='Run GET request').click()
        expect(page.get_by_role('status')).to_contain_text('HTTP 200')
        page.goto(base + '/review', wait_until='networkidle')
        expect(page.locator('h1')).to_contain_text('A small system.')
        assert not errors, errors
        context.close(); browser.close()
    print('HTTP/browser smoke passed: assets, CSP, React, API, CSV download, API explorer and review page.')


if __name__=='__main__': main()
