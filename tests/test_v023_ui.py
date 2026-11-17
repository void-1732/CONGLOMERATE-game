"""Current release v0.23 UI and monthly accounting smoke test (Playwright)."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import os, shutil

html=(Path(__file__).resolve().parents[1]/'index.html').read_text(encoding='utf-8')
with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True,
        executable_path=os.getenv('CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None,
        args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':900})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content(html,wait_until='domcontentloaded')
    for _ in range(4):
        page.locator('[data-action="wizardNext"]').click()
    assert page.evaluate('TECH_NODES.length')==800
    assert page.evaluate('check(S)')==[]
    page.locator('[data-section="vehicles"]').click()
    page.locator('[data-page="product"]').click()
    assert page.locator('[data-design-field]').count()==10
    page.locator('#design_exterior').select_option('sporty')
    assert 'スポーティ' in page.locator('.appearance-summary').inner_text()
    for tab in ['design','production','projects','sales']:
        page.locator(f'[data-product-view="{tab}"]').click()
        assert page.locator('[data-product-pane].current:visible').count()>0
    page.locator('[data-page="people"]').click()
    page.locator('[data-people-view="hr"]').click()
    assert page.locator('#staffingOverview .staff-dept').count()==3
    page.locator('[data-section="operations"]').click()
    page.locator('[data-page="factory"]').click()
    assert page.locator('.factory-insight').count()>=2
    page.evaluate("()=>{current().factoryOps.mode='detailed';current().plants[0].kind='assembly';render()}")
    assert page.locator('#assemblySupplyV023 tbody tr').count()==3
    page.evaluate("()=>{current().plants[0].kind='integrated';current().plants[0].lastInternalModules=3;render()}")
    assert '3個' in page.locator('#assemblySupplyV023').inner_text()
    page.locator('[data-action="staffToHrV023"]').click()
    assert page.locator('#staffingOverview').count()==1
    page.evaluate('saveAuto=async()=>true')
    for m in range(12):
        page.evaluate('async()=>await runMonth()')
        state=page.evaluate("""()=>({
            bad:LAST_MONTH_DIAGNOSTIC,errors:check(S),
            group:consolidate(S).errors,cf:consolidate(S).cf.reconciled})""")
        assert state['bad'] is None and not state['errors'] and not state['group'] and state['cf'],(m,state)
    assert not errors,errors
    browser.close()
print('PASS v0.23 800-techs, UI, factory/H.R., exterior, 12 months accounting')
