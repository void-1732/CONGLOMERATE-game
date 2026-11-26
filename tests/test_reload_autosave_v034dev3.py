"""Real HTTP-origin Playwright reload test: IndexedDB + local safety snapshot.
No stubbing out saveAuto or browser persistence.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import os
import shutil
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
server=ThreadingHTTPServer(('127.0.0.1',0), partial(Quiet,directory=str(ROOT)))
thread=Thread(target=server.serve_forever,daemon=True);thread.start()
URL=f'http://127.0.0.1:{server.server_port}/index.html'
with sync_playwright() as p:
    browser=p.chromium.launch(
        executable_path=os.getenv('CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None,
        args=['--no-sandbox'])
    page=browser.new_page()
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(URL);page.wait_for_function('STORAGE_READY')
    assert page.title().startswith('CONGLOMERATE v0.34-dev.3')
    assert page.locator('.prototype').inner_text()=='機能検証用・開発版 v0.34-dev.3'
    assert page.evaluate('S===null') and page.locator('[data-action="wizardNext"]').count()==1
    for _ in range(4):
        page.locator('[data-action="wizardNext"]').click()
    page.wait_for_function("S?.playerId && S.autosaveState==='保存成功'")
    initial=page.evaluate("""()=>{
      const f=current();return {id:S.playerId,month:S.month,year:S.year,name:f.name,workers:f.staff.production,
        backend:SAVE_INDEX.backend};
    }""")
    assert initial['backend']=='IndexedDB',initial
    page.reload();page.wait_for_function('STORAGE_READY')
    assert page.evaluate('S!==null'),page.locator('#modalHost').inner_text()
    assert page.evaluate('S.playerId')==initial['id']
    assert page.evaluate('current().name')==initial['name']
    # Change headcount via the actual user-facing HR action; do not month-close.
    page.evaluate("PEOPLE_VIEW='hr';PAGE='people';render()")
    page.locator('#hireArea').select_option('production')
    page.locator('#hireCount').fill('11')
    page.locator('[data-action="hireStaff"]').click()
    changed=page.evaluate('current().staff.production')
    assert changed==initial['workers']+11
    # Refresh immediately: pending IndexedDB debounced commit has not necessarily fired.
    page.reload();page.wait_for_function('STORAGE_READY')
    assert page.evaluate('current().staff.production')==changed,('lost hired workers on refresh',initial,changed)
    # Create plant through user UI, then refresh before next month.
    page.evaluate("PAGE='facilityExpansion';render()")
    page.locator('#factoryName').fill('再読込試験工場')
    page.locator('#factoryKind').select_option('engine')
    page.locator('#factoryScale').select_option('small')
    page.locator('[data-action="factoryBuild"]').click()
    assert page.evaluate("current().plants.some(x=>x.name==='再読込試験工場')")
    page.reload();page.wait_for_function('STORAGE_READY')
    assert page.evaluate("current().plants.some(x=>x.name==='再読込試験工場')"), 'factory disappeared'
    # Month close must advance the saved year/month and preserve live factories.
    previous=page.evaluate('S.monthCommitted')
    page.evaluate('async()=>await runMonth()')
    assert page.evaluate('S.monthCommitted')==previous+1
    after_month=page.evaluate("""()=>({
       committed:S.monthCommitted,year:S.year,month:S.month,
       workers:current().staff.production,
       plant:current().plants.some(x=>x.name==='再読込試験工場')
    })""")
    page.reload();page.wait_for_function('STORAGE_READY')
    recovered_month=page.evaluate("""()=>({
       committed:S.monthCommitted,year:S.year,month:S.month,
       workers:current().staff.production,
       plant:current().plants.some(x=>x.name==='再読込試験工場')
    })""")
    assert recovered_month==after_month,(after_month,recovered_month)
    # Pagehide snapshots must protect data if the IDB connection is unavailable.
    page.evaluate("()=>{if(IDB){IDB.close();IDB=null}}")
    page.evaluate("PEOPLE_VIEW='hr';PAGE='people';render()")
    page.locator('#hireCount').fill('3')
    page.locator('[data-action="hireStaff"]').click()
    expected=page.evaluate('current().staff.production')
    page.add_init_script("""Object.defineProperty(window,'indexedDB',{get(){return undefined}, configurable:true})""")
    page.reload();page.wait_for_function('STORAGE_READY')
    assert page.evaluate('S!==null'), 'IndexedDB failure sent user to new game wizard'
    assert page.evaluate('current().staff.production')==expected,'emergency snapshot not restored'
    assert page.evaluate("SAVE_INDEX.backend")=='IndexedDB利用不可'
    assert page.evaluate("current().plants.some(x=>x.name==='再読込試験工場')")
    assert not errors,errors
    browser.close()
server.shutdown()
print('PASS: version label, new-game IndexedDB save, HR action, factory build immediate reload, IndexedDB failure recovery')
