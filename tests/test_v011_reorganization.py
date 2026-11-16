"""CONGLOMERATE v0.11: wholly-owned sibling business transfer/integration."""
from pathlib import Path
from playwright.sync_api import sync_playwright
source=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
    page=browser.new_page()
    failures=[]
    page.on("pageerror",lambda e:failures.append(str(e)))
    page.set_content(source,wait_until="load")
    page.evaluate("""()=>{
      window.__db={meta:{},snapshots:{}};
      idbRead=async(k,id)=>structuredClone(window.__db[k][id]??null);
      idbWrite=async(k,o)=>{window.__db[k][o.key]=structuredClone(o)};
      IDB={};SAVE_INDEX.backend='IndexedDB';
      S=newGame({...setup,era:1900,country:'JP',difficulty:'easy'});
      VIEW_FIRM=S.playerId;PAGE='group';render();}""")
    for name in ("製造子会社A","製造子会社B"):
        page.fill("#subName",name)
        page.select_option("#subIndustry","manufacturing")
        page.fill("#subCapital","1200000")
        page.click("[data-action=createSub]")
        page.evaluate("()=>{VIEW_FIRM=S.playerId;PAGE='group';render()}")
    ids=page.evaluate("()=>S.firms.filter(f=>f.name.startsWith('製造子会社')).map(f=>f.id)")
    page.evaluate("(id)=>{VIEW_FIRM=id;PAGE='group';render()}",ids[0])
    page.select_option("#reorgTarget",ids[1])
    page.select_option("#reorgModel",index=1)
    page.click("[data-action=reorgTransfer]")
    a=page.evaluate("""()=>({checks:check(S),group:consolidate(S).errors,
       cash:consolidate(S).cf.reconciled,history:S.reorgHistory.length})""")
    assert not a["checks"] and not a["group"] and a["cash"] and a["history"]==1,a
    page.evaluate("(id)=>{VIEW_FIRM=id;PAGE='group';render()}",ids[0])
    page.select_option("#reorgMergeTarget",ids[1])
    page.click("[data-action=reorgIntegrate]")
    b=page.evaluate("""()=>({checks:check(S),group:consolidate(S).errors,
       cash:consolidate(S).cf.reconciled,history:S.reorgHistory.length,
       status:S.reorgHistory.at(-1)?.kind,record:S.firms.some(f=>f.reorgStatus==='integrated')})""")
    assert not b["checks"] and not b["group"] and b["cash"]
    assert b["history"]==2 and b["status"]=="business-integration" and b["record"],b
    assert not failures
    print("PASS v0.11 subsidiary reorganization, transfer and consolidated CF")
    browser.close()
