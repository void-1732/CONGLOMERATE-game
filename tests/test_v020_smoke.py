"""CONGLOMERATE Ver.0.20 current-release smoke/regression test.
Run: python tests/test_v020_smoke.py (needs Python Playwright + Chromium)
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import os, shutil

src=(Path(__file__).resolve().parents[1]/'index.html').read_text(encoding='utf-8')
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None,args=['--no-sandbox'])
    page=b.new_page(viewport={'width':1440,'height':900})
    failures=[]
    page.on('pageerror',lambda e:failures.append(str(e)))
    page.set_content(src,wait_until='domcontentloaded')
    for _ in range(4):page.locator('[data-action="wizardNext"]').click()
    assert page.evaluate('TECH_NODES.length')==800
    assert page.evaluate('check(S)')==[]
    page.locator('[data-section="corporate"]').click()
    page.locator('[data-page="capital"]').click()
    before=page.evaluate("acc(current(),'cash')")
    page.locator('[data-action="issueShares"]').click()
    assert page.evaluate('current().sharesOutstanding')==1200000
    assert page.evaluate("acc(current(),'cash')")>before
    assert page.evaluate('check(S)')==[]
    assert page.locator('[data-action="issueShares"]').is_disabled()
    page.locator('[data-section="operations"]').click()
    page.locator('[data-page="supply"]').click()
    assert page.locator('#backup_steel').count()==1
    assert page.locator('#content').get_by_text('供給障害・調達リスク分析').count()>0
    page.locator('#backup_steel').select_option(index=1)
    page.locator('[data-action="saveSupply"]').click()
    assert page.evaluate('current().supply.contracts.steel.backupId')!=''
    page.locator('[data-section="markets"]').click()
    page.locator('[data-page="market"]').click()
    assert '競合車種・価格競争' in page.locator('#content').inner_text()
    for _ in range(12):
        page.evaluate('async()=>await runMonth()')
        assert page.evaluate('check(S)')==[]
        c=page.evaluate('consolidate(S)')
        assert c['errors']==[] and c['cf']['reconciled']
    assert not failures,failures
    b.close()
print('PASS v0.20: 800 R&D, primary issuance, supplier alternate, rival UI, 12 monthly closures')
