from pathlib import Path
from playwright.sync_api import sync_playwright
import os

html=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path=os.getenv("CHROMIUM_EXECUTABLE") or None)
    page=browser.new_page(viewport={"width":1366,"height":768})
    page.set_content(html,wait_until="load")
    page.evaluate("""()=>{window.__db={meta:{},snapshots:{}};
      idbRead=async(k,id)=>structuredClone(window.__db[k][id]??null);
      idbWrite=async(k,o)=>{window.__db[k][o.key]=structuredClone(o)};
      IDB={};SAVE_INDEX.backend='IndexedDB';
      S=newGame({...setup,era:1900,country:'JP',difficulty:'easy'});
      VIEW_FIRM=S.playerId;PAGE='group';render();}""")
    page.select_option("#negTarget",index=0)
    page.fill("#negPercent","55");page.fill("#negPremium","110")
    page.click("[data-action=buyStake]")
    assert page.evaluate("()=>controlled().length")==2
    page.evaluate("()=>{PAGE='group';render()}")
    page.select_option("#delegateMode","delegated")
    page.fill("#delegateTarget","32");page.fill("#delegateRndCap","5000")
    page.click("[data-action=saveDelegate]")
    result=page.evaluate("""async()=>{
      const failures=[];for(let i=0;i<120;i++){
        const previous=S.monthCommitted;await runMonth();
        const checks=check(S),group=consolidate(S);
        if(S.monthCommitted!==previous+1||checks.length||group.errors.length||!group.cf.reconciled){
          failures.push({month:i,advanced:S.monthCommitted-previous,checks,conso:group.errors,cf:group.cf.unreconciled});break;
        }
      }
      const before=JSON.stringify({group:consolidate(S).bs,cf:consolidate(S).cf,
        policies:company(S.playerId).delegate,plants:company(S.playerId).plants});
      const loaded=parsePayload(savePayload(S)),old=S;S=loaded;
      const after=JSON.stringify({group:consolidate(S).bs,cf:consolidate(S).cf,
        policies:company(S.playerId).delegate,plants:company(S.playerId).plants});
      return {failures,month:S.monthCommitted,same:before===after,checks:check(S),
        conso:consolidate(S).errors,reportCount:company(S.playerId).delegate.reports.length};
    }""")
    assert not result["failures"] and result["same"]
    assert not result["checks"] and not result["conso"] and result["reportCount"]>0
    assert result["month"]==1900*12+120-1
    migration=page.evaluate("""()=>{
      const older=structuredClone(S);
      for(const f of older.firms){delete f.delegate;delete f.modelRenewals;delete f.shareBlocks;
        for(const m of f.models){delete m.lineageId;delete m.generation;}}
      const loaded=parsePayload(savePayload(older));
      return {checks:check(loaded),delegated:!!loaded.firms[0].delegate,
        blocks:!!loaded.firms[1].shareBlocks,models:loaded.firms.every(f=>f.models.every(m=>Number.isInteger(m.generation)))};
    }""")
    assert not migration["checks"] and migration["delegated"] and migration["blocks"] and migration["models"]
    print("PASS v0.7 120-month accounting/CF, JSON, v0.6 migration",result)
    browser.close()
