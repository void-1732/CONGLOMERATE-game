"""Current Ver.0.21 smoke test (Playwright + Chromium required)."""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright

html=(Path(__file__).resolve().parents[1]/'index.html').read_text(encoding='utf-8')
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':900})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content(html,wait_until='domcontentloaded')
    for _ in range(4):
        page.locator('[data-action="wizardNext"]').click()
    assert page.evaluate('TECH_NODES.length')==800
    assert page.evaluate('check(S)')==[]
    tariffs=page.evaluate("""() => [
      v21Freight(findSite('JP-TOK'),findSite('JP-TOK'),10),
      v21Freight(findSite('JP-TOK'),findSite('JP-NGO'),10),
      v21Freight(findSite('JP-TOK'),findSite('US-DET'),10)]""")
    assert [x['lead'] for x in tariffs]==[1,2,3]
    assert tariffs[0]['base']<tariffs[1]['base']<tariffs[2]['base']
    page.evaluate("""() => {
      window.oldProcure=procureNetwork;
      procureNetwork=()=>{throw Error('diagnostic smoke test')};
      saveAuto=async()=>true;
    }""")
    old_date=page.evaluate('S.month')
    page.evaluate('async()=>await runMonth()')
    assert page.evaluate('LAST_MONTH_DIAGNOSTIC.stage')=='PROCUREMENT'
    assert not page.evaluate('LAST_MONTH_DIAGNOSTIC.committed')
    assert page.evaluate('S.month')==old_date
    assert page.locator('[data-action="monthDiagnosticDownload"]').count()==1
    page.evaluate("""() => {
      procureNetwork=window.oldProcure;
      MONTH_DIAGNOSTIC_OPEN=false;
      LAST_MONTH_DIAGNOSTIC=null;
      const f=current(),siteId=f.plants[0].siteId;
      for(const kind of ['engine','body','components'])
       f.plants.push({id:'TEST'+S.seq++,name:kind+' factory',kind,scale:'small',capacity:25,condition:100,siteId,siteCountry:'JP',focus:'all',construction:null,lastProduced:0,lastUtilization:0});
      for(const kind of ['steel','rubber']){
        const cost=kind==='steel'?50000:20000;
        f.stock[kind].q+=500;f.stock[kind].v+=cost;
        post(f,{materials:cost},{cash:cost},'test materials','operating');
      }
      ensureFactoryV21(f);
      f.factoryOps.mode='detailed';
      for(const plant of f.plants.filter(x=>v21ModuleType(x))){
        f.factoryOps.plans[plant.id]=8;
        f.factoryOps.routes[plant.id]={enabled:true,to:f.plants[0].id,target:8,limit:8};
      }
      f.staff.production=300;syncPlant(f);render();
    }""")
    for _ in range(8):
        page.evaluate('async()=>await runMonth()')
        assert page.evaluate('LAST_MONTH_DIAGNOSTIC') is None
        assert page.evaluate('check(S)')==[]
        assert page.evaluate('consolidate(S).errors')==[]
        assert page.evaluate('consolidate(S).cf.reconciled')
    assert page.evaluate('current().factoryOps.history.length')>0
    assert not errors,errors
    browser.close()
print('PASS v0.21 smoke: 800 technologies, freight tiers, error rollback, auto module supply and accounting')
