"""v0.14: effects must change actual raw materials, costs, demand and accounting."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import os, shutil

html=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,args=["--no-sandbox"])
    page=browser.new_page()
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.set_content(html,wait_until="load")
    page.evaluate("""()=>{window.__db={meta:{},snapshots:{}};idbRead=async(k,id)=>structuredClone(window.__db[k][id]??null);idbWrite=async(k,o)=>{window.__db[k][o.key]=structuredClone(o)};IDB={};SAVE_INDEX.backend='IndexedDB';S=newGame({...setup,era:2020,country:'JP',difficulty:'easy'});VIEW_FIRM=S.playerId;PAGE='people';render()}""")
    result=page.evaluate("""()=>{
       const f=company(S.playerId),design={...DESIGN_DEFAULT,size:'large',audience:'premium',interior:'luxury',body:'sedan'};
       const before=materialRequirement(design,f),cost=productCostQuote(f,design,S).unitCost,fit=designAnalysis(design,f.tech,f.research.levels,techBenefits(f)).desirability;
       f.research.tree.done.push(...['materials-1','materials-4','materials-7','materials-10','materials-31','materials-34','chassis-31','comfort-1','comfort-31','comfort-34','comfort-37','electronics-31','software-31','production-31','production-33','production-35','energy-31']);
       const after=materialRequirement(design,f),newCost=productCostQuote(f,design,S).unitCost,newFit=designAnalysis(design,f.tech,f.research.levels,techBenefits(f)).desirability;
       return {before,after,cost,newCost,fit,newFit,bonus:techBenefits(f),checks:check(S),group:consolidate(S).errors};
    }""")
    assert result['after']['steel']<result['before']['steel']
    assert result['newCost']<result['cost'] and result['newFit']>result['fit']
    assert result['bonus']['manufacturing']>0
    assert not result['checks'] and not result['group']
    for month in range(8):
        result=page.evaluate("""async()=>{const old=S.monthCommitted;await runMonth();const g=consolidate(S);return {step:S.monthCommitted-old,books:check(S),group:g.errors,cf:g.cf.reconciled}}""")
        assert result['step']==1 and not result['books'] and not result['group'] and result['cf'],result
    assert not errors,errors
    print("PASS v0.14 eight-month materials/cost/market and consolidated cashflow regression")
    browser.close()
