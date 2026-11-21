"""CONGLOMERATE v0.26 current release smoke: factory labor + procurement."""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from playwright.sync_api import sync_playwright
import os, shutil

ROOT=Path(__file__).resolve().parents[1]
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT)))
Thread(target=server.serve_forever,daemon=True).start()
URL=f'http://127.0.0.1:{server.server_port}/index.html'
with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':900})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('dialog',lambda d:d.accept())
    page.goto(URL)
    page.wait_for_function('STORAGE_READY')
    for _ in range(4):page.locator('[data-action="wizardNext"]').click()
    assert page.evaluate('TECH_NODES.length')==800
    page.locator('[data-section="operations"]').click()
    assert page.locator('[data-factory-pane-v026]').count()==3
    page.evaluate("""()=>{
      const f=current(),base=f.plants[0];
      for(const kind of ['engine','body','components'])
        f.plants.push({...structuredClone(base),id:'SMK-'+kind,name:'Test '+kind,kind,capacity:25,construction:null,paused:false,renovation:null});
      ensureFactoryV21(f);f.staff.production=80;syncPlant(f);render();
    }""")
    page.locator('[data-action="activateSupportV026"]').click()
    assert page.evaluate('current().factoryOps.mode')=='detailed'
    assert page.evaluate('current().plants.filter(p=>v21ModuleType(p)).every(p=>current().factoryOps.plans[p.id]>0)')
    page.locator('[data-factory-select="SMK-engine"]').click()
    page.locator('[data-factory-view-v026="control"]').click()
    page.locator('#factoryStaffModeV026').select_option('fixed')
    page.locator('#factoryStaffAmountV026').fill('5')
    page.locator('[data-action="saveFactoryStaffV026"]').click()
    assert page.evaluate('factoryLaborPlanV026(current()).byId["SMK-engine"].assigned')==5
    assert page.evaluate('factoryResourceTargetV026(current(),"steel").demand')>0
    page.locator('[data-page="supply"]').first.click()
    assert page.locator('.resource-v026-dashboard .resource-v026-table tbody tr').count()==7
    page.locator('#spotResourceV026').select_option('steel')
    page.locator('#spotQtyV026').fill('2')
    cash_before=page.evaluate('acc(current(),"cash")')
    steel_before=page.evaluate('current().stock.steel.q')
    page.locator('[data-action="buySpotV026"]').click()
    assert page.evaluate('current().stock.steel.q')==steel_before+2
    assert page.evaluate('acc(current(),"cash")')<cash_before
    page.locator('[data-action="buySpotV026"]').click()
    assert page.evaluate('current().stock.steel.q')==steel_before+2
    page.evaluate('saveAuto=async()=>true')
    for month in range(24):
        page.evaluate('async()=>await runMonth()')
        check=page.evaluate('''()=>({diag:LAST_MONTH_DIAGNOSTIC?.stage||null,errors:check(S),group:consolidate(S).errors,cf:consolidate(S).cf.reconciled})''')
        assert not check['diag'] and not check['errors'] and not check['group'] and check['cf'],(month,check)
    assert not errors,errors
    browser.close()
server.shutdown()
print('PASS: 800 research nodes, staffing, procurement, 24 months and accounting')
