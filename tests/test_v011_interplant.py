"""CONGLOMERATE v0.11: Chromium smoke test for manufacturing and reorganization."""
from pathlib import Path
from playwright.sync_api import sync_playwright

source=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
    page=browser.new_page()
    failures=[]
    page.on("pageerror",lambda err:failures.append(str(err)))
    page.set_content(source,wait_until="load")
    page.evaluate("""()=>{window.__db={meta:{},snapshots:{}};
        idbRead=async(k,id)=>structuredClone(window.__db[k][id]??null);
        idbWrite=async(k,o)=>{window.__db[k][o.key]=structuredClone(o)};
        IDB={};SAVE_INDEX.backend='IndexedDB';
        S=newGame({...setup,era:1900,country:'JP',difficulty:'easy'});
        VIEW_FIRM=S.playerId;PAGE='factory';render();}""")
    page.fill("#factoryName","検証用部品工場")
    page.select_option("#factoryKind","components")
    page.click("[data-action=factoryBuild]")
    for i in range(2):page.evaluate("async()=>await runMonth()")
    page.evaluate("()=>{PAGE='factory';render()}")
    page.fill('[id^="partsPlan_"]',"6")
    page.click("[data-action=partsPlan]")
    page.evaluate("async()=>await runMonth()")
    page.evaluate("()=>{PAGE='factory';render()}")
    page.fill("#partsQty","2")
    page.click("[data-action=shipParts]")
    outgoing=page.evaluate("""()=>({checks:check(S),
         transit:acc(company(S.playerId),'materialsTransit'),
         record:company(S.playerId).interplant.shipments.reduce((v,x)=>v+x.bookCost,0)})""")
    assert not outgoing["checks"] and outgoing["transit"]>0
    assert outgoing["transit"]==outgoing["record"]
    for i in range(2):page.evaluate("async()=>await runMonth()")
    incoming=page.evaluate("""()=>({checks:check(S),cf:consolidate(S).cf.reconciled,
         transit:acc(company(S.playerId),'materialsTransit'),
         pending:company(S.playerId).interplant.shipments.length})""")
    assert not incoming["checks"] and incoming["cf"]
    assert incoming["transit"]==0 and incoming["pending"]==0
    assert not failures
    print("PASS v0.11 interplant materials and consolidated cashflow")
    browser.close()
