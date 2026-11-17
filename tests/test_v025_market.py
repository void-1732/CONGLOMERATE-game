"""CONGLOMERATE Ver.0.25 market workspace smoke test."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import os, shutil

html=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,args=["--no-sandbox"])
    page=browser.new_page(viewport={"width":1440,"height":900})
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.set_content(html,wait_until="domcontentloaded")
    for _ in range(4): page.locator('[data-action="wizardNext"]').click()
    assert page.evaluate('TECH_NODES.length')==800
    page.locator('[data-section="markets"]').click()
    assert page.evaluate('PAGE')=='marketOverview'
    page.locator('[data-page="marketRegion"]').first.click()
    page.locator('[data-mk-region="US"]').first.click()
    assert page.evaluate('VIEW_COUNTRY')=='US'
    page.locator('[data-page="marketRivals"]').first.click()
    page.locator('#mkRivalsCountry').select_option('UK')
    assert page.locator('[data-mk-select]').count()>0
    page.locator('#mkRivalsCountry').select_option('all')
    page.locator('[data-mk-select]').first.check()
    page.locator('[data-mk-action="compare"]').click()
    assert page.locator('#mkRivalsComparison thead th').count()==2
    page.locator('[data-page="distribution"]').first.click()
    assert page.locator('.mk-contract').count()==5
    page.locator('#mkSimPrice').fill('20000')
    assert page.locator('#mkSimUnit').inner_text()!='—'
    page.locator('#capacity_JP').fill('510')
    assert '未保存' in page.locator('#mkContractState').inner_text()
    page.locator('[data-action="saveDistribution"]').click()
    assert page.evaluate('exportChannel(current(),"JP").capacity')==510
    page.locator('[data-page="marketOwn"]').first.click()
    assert page.locator('#mkOwnLedger').count()==1
    page.locator('[data-section="vehicles"]').click()
    assert page.locator('[data-product-view]').count()==3
    assert page.locator('.mk-v25-projects').count()==1
    assert page.locator('[data-product-view="projects"]').count()==0
    page.evaluate('saveAuto=async()=>true')
    for i in range(12):
        page.evaluate('async()=>await runMonth()')
        state=page.evaluate('({bad:LAST_MONTH_DIAGNOSTIC,err:check(S),group:consolidate(S).errors,cf:consolidate(S).cf.reconciled})')
        assert not state['bad'] and not state['err'] and not state['group'] and state['cf'],(i,state)
    assert not errors,errors
    browser.close()
print("PASS v0.25: market navigation, search, comparison, contracts, product tabs, 12 monthly checks")
