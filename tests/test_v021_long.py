"""60-month detailed-manufacturing stability test. Requires Playwright + Chromium."""
from pathlib import Path
import os,shutil
from playwright.sync_api import sync_playwright

html=(Path(__file__).resolve().parents[1]/'index.html').read_text(encoding='utf-8')
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None,args=['--no-sandbox'])
    page=browser.new_page()
    page.set_content(html,wait_until='domcontentloaded')
    for _ in range(4):
        page.locator('[data-action="wizardNext"]').click()
    page.evaluate("""()=>{
      const f=current(),siteId=f.plants[0].siteId;
      for(const kind of ['engine','body','components'])
        f.plants.push({id:'LP'+S.seq++,name:kind+' test',kind,scale:'small',capacity:25,condition:100,siteId,siteCountry:'JP',focus:'all',construction:null,lastProduced:0,lastUtilization:0});
      for(const kind of ['steel','rubber']){
        const money=kind==='steel'?100000:30000;
        f.stock[kind].q+=1200;f.stock[kind].v+=money;
        post(f,{materials:money},{cash:money},'test stock','operating');
      }
      ensureFactoryV21(f);f.factoryOps.mode='detailed';
      for(const factory of f.plants.filter(x=>v21ModuleType(x))){
        f.factoryOps.plans[factory.id]=8;
        f.factoryOps.routes[factory.id]={enabled:true,to:f.plants[0].id,target:12,limit:12};
      }
      f.staff.production=400;saveAuto=async()=>true;syncPlant(f);render();
    }""")
    for month in range(60):
        page.evaluate('async()=>await runMonth()')
        d=page.evaluate("""()=>({diag:LAST_MONTH_DIAGNOSTIC,errors:check(S),conso:consolidate(S).errors,cf:consolidate(S).cf.reconciled})""")
        assert d['diag'] is None and not d['errors'] and not d['conso'] and d['cf'],(month,d)
    browser.close()
print('PASS v0.21 60-month manufacturing, supply and consolidation')
