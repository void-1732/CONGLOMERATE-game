"""CONGLOMERATE v0.24 current-release smoke / integration test.

Requires: pip install playwright; python -m playwright install chromium
Run from repository: python tests/test_v024_center.py
"""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright

html = (Path(__file__).resolve().parents[1] / 'index.html').read_text(encoding='utf-8')
with sync_playwright() as pw:
    browser = pw.chromium.launch(
        headless=True,
        executable_path=os.getenv('CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None,
        args=['--no-sandbox'],
    )
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.set_content(html, wait_until='domcontentloaded')
    page.evaluate("S=newGame({...setup,era:1900,country:'JP',difficulty:'easy'});VIEW_FIRM=S.playerId;PAGE='automation';render()")
    assert page.evaluate('TECH_NODES.length') == 800
    assert page.locator('.ai-tab').count() == 4
    page.locator('[data-ai-tab="settings"]').click()
    page.locator('[data-ai-feature="production"]').select_option('proposal')
    page.locator('[data-ai-category="logistics"]').click()
    page.locator('[data-ai-feature="procurement"]').select_option('routine')
    page.locator('[data-ai-category="manufacturing"]').click()
    assert page.locator('[data-ai-feature="production"]').input_value() == 'proposal'
    page.locator('#aiMode').select_option('delegated')
    page.locator('[data-ai-command="preview"]').click()
    assert page.locator('.ai-preview').count() == 1
    page.locator('[data-ai-command="commit"]').click()
    assert page.evaluate('current().delegate.aiCenter.modes.production') == 'proposal'
    page.evaluate("PAGE='supply';render()")
    assert page.locator('.supply-v24-card').count() == 7
    page.locator('#supplier_steel').select_option(index=1)
    selected = page.locator('#supplier_steel').input_value()
    assert not page.locator('#aiSupply_steel').is_checked()
    page.locator('#buffer_steel').select_option('1.5')
    page.locator('[data-action="saveSupply"]').click()
    assert page.evaluate('current().supply.contracts.steel.buffer') == 1.5
    assert page.evaluate('current().supply.contracts.steel.supplierId') == selected
    assert page.evaluate('current().supply.contracts.steel.autoManage') is False
    before = page.evaluate('JSON.stringify(current().supply.contracts)')
    page.evaluate("document.querySelector('#supplier_rubber').value='BAD'")
    page.locator('[data-action="saveSupply"]').click()
    assert page.evaluate('JSON.stringify(current().supply.contracts)') == before
    page.evaluate("window.backup=savePayload(S);S=parsePayload(window.backup);saveAuto=async()=>true;render()")
    for month in range(12):
        page.evaluate('async()=>await runMonth()')
        result = page.evaluate("""()=>({d:LAST_MONTH_DIAGNOSTIC,e:check(S),c:consolidate(S).errors,cf:consolidate(S).cf.reconciled})""")
        assert result['d'] is None and not result['e'] and not result['c'] and result['cf'], (month, result)
    assert not errors, errors
    browser.close()
print('PASS v0.24 center / contracts / save / month accounting')
