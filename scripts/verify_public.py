"""Signed-out public-link precheck; does not submit the form.

This launches a fresh non-persistent Chromium context with no account cookies.
The video still needs a human signed-out playback check (consent/autoplay vary).
"""
import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlparse
import httpx
from playwright.sync_api import sync_playwright


def https_url(value):
    parsed = urlparse(value)
    if parsed.scheme != 'https' or not parsed.netloc:
        raise argparse.ArgumentTypeError('An actual public HTTPS URL is required')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', required=True, type=https_url)
    parser.add_argument('--repo', required=True, type=https_url)
    parser.add_argument('--video', required=True, type=https_url)
    parser.add_argument('--output', default='docs/public-access-report.json')
    args=parser.parse_args()
    repo=urlparse(args.repo)
    if repo.hostname != 'github.com' or len(repo.path.strip('/').split('/')) != 2:
        parser.error('--repo must be https://github.com/OWNER/REPO')
    if urlparse(args.video).hostname not in ('youtube.com','www.youtube.com','youtu.be'):
        parser.error('--video must be a YouTube link, not a local file')
    report={'context':'Fresh, signed-out, non-persistent Chromium browser context','checks':{},
            'manual_video_playback_required':True,'form_submitted':False}
    with httpx.Client(follow_redirects=True, timeout=30) as client:
        r=client.get('https://api.github.com/repos/'+repo.path.strip('/'))
        r.raise_for_status()
        assert r.json().get('private') is False, 'Repository is not public'
        report['checks']['repo_api_public']=True
        r=client.get(args.app.rstrip('/')+'/api/meta?source=real')
        r.raise_for_status()
        assert r.json()['provenance']['mode']=='real', 'Real Elexon snapshot must be installed for submission'
        report['checks']['real_snapshot_present']=True
    with sync_playwright() as p:
        opts={'headless':True}
        if os.environ.get('CHROMIUM_PATH'): opts['executable_path']=os.environ['CHROMIUM_PATH']
        browser=p.chromium.launch(**opts)
        context=browser.new_context(locale='en-GB')
        page=context.new_page()
        for label,url in [('app',args.app),('repo',args.repo),('video',args.video)]:
            response=page.goto(url,wait_until='domcontentloaded',timeout=60000)
            assert response and response.status < 400, f'{label} returned an error'
            if label=='app':
                page.get_by_text('Mean wind forecast',exact=True).wait_for(timeout=30000)
            report['checks'][label]={'url':url,'status':response.status,'title':page.title(),'final_url':page.url}
        context.close();browser.close()
    dest=Path(args.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    print('Precheck only. Open all links in an incognito window and play the video signed out before submitting.')


if __name__=='__main__': main()
